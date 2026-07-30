import asyncio
from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable

from agents import RunContextWrapper, function_tool

from diagnostics.dns import check_dns
from diagnostics.http import check_http
from diagnostics.network import check_client_network
from diagnostics.result import make_result, skipped_result
from diagnostics.tcp import check_tcp
from diagnostics.tls import check_tls
from diagnostics.traceroute import check_traceroute, skipped_traceroute


CHECK_NAMES = {
    "client": "Client Network",
    "dns": "DNS",
    "tcp": "TCP",
    "tls": "TLS",
    "http": "HTTP",
    "traceroute": "Traceroute",
}
CHECK_ORDER = ("client", "dns", "traceroute", "tcp", "tls", "http")
MAX_CONNECTION_ADDRESSES = 4


def _connection_addresses(dns_result):
    """Choose a small IPv4/IPv6 sample while retaining complete DNS evidence."""
    details = dns_result.get("details", {})
    ipv4 = details.get("A records", [])
    ipv6 = details.get("AAAA records", [])

    if ipv4 or ipv6:
        return [*ipv4[:2], *ipv6[:2]][:MAX_CONNECTION_ADDRESSES]

    return details.get("addresses", [])[:MAX_CONNECTION_ADDRESSES]


@dataclass
class DiagnosticContext:
    """Server-owned state for one agent run.

    The target is normalized and locked before the model runs. Tool schemas do
    not accept a hostname or URL, so the model cannot redirect a check toward a
    different host.
    """

    target: dict
    mode: str
    max_checks: int = 6
    results: dict[str, dict] = field(default_factory=dict)
    tool_log: list[dict] = field(default_factory=list)
    requested_tools: list[dict] = field(default_factory=list)
    checks_used: int = 0

    def _budget_result(self, key):
        name = CHECK_NAMES[key]
        return skipped_result(
            key,
            name,
            f"Skipped because the {self.max_checks}-check agent budget was exhausted.",
        )

    def _run_check(self, key, operation: Callable[[], dict]):
        cached = self.results.get(key)
        if cached is not None:
            return cached

        if self.checks_used >= self.max_checks:
            result = self._budget_result(key)
            self.tool_log.append(
                {
                    "tool": key,
                    "cached": False,
                    "denied": True,
                    "status": result["status"],
                    "summary": result["summary"],
                    "duration_ms": 0,
                }
            )
            return result

        self.checks_used += 1
        started = perf_counter()

        try:
            result = operation()
        except Exception as error:
            result = make_result(
                key,
                CHECK_NAMES[key],
                "error",
                f"{CHECK_NAMES[key]} check failed unexpectedly.",
                details={
                    "Error type": type(error).__name__,
                    "Error": str(error)[:500],
                },
            )

        elapsed_ms = round((perf_counter() - started) * 1000)
        self.results[key] = result
        self.tool_log.append(
            {
                "tool": key,
                "cached": False,
                "status": result["status"],
                "summary": result["summary"],
                "duration_ms": result.get("duration_ms", elapsed_ms),
            }
        )
        return result

    def inspect_client(self):
        return self._run_check("client", check_client_network)

    def inspect_dns(self):
        network_result = self.inspect_client()
        allow_proxy_fake_ip = network_result.get("proxy_detected", False)
        return self._run_check(
            "dns",
            lambda: check_dns(
                self.target,
                allow_proxy_fake_ip=allow_proxy_fake_ip,
            ),
        )

    def inspect_tcp(self):
        dns_result = self.inspect_dns()

        if dns_result["status"] == "error":
            operation = lambda: skipped_result(
                "tcp",
                "TCP",
                "Skipped because DNS failed.",
            )
        elif dns_result.get("proxy_fake_ip"):
            operation = lambda: skipped_result(
                "tcp",
                "TCP",
                "Skipped because proxy DNS returned a synthetic IP address.",
            )
        else:
            addresses = _connection_addresses(dns_result)
            operation = lambda: check_tcp(self.target, addresses)

        return self._run_check("tcp", operation)

    def inspect_tls(self):
        dns_result = self.inspect_dns()
        tcp_result = self.inspect_tcp()

        if dns_result["status"] == "error":
            operation = lambda: skipped_result(
                "tls",
                "TLS",
                "Skipped because DNS failed.",
            )
        elif dns_result.get("proxy_fake_ip"):
            operation = lambda: skipped_result(
                "tls",
                "TLS",
                "Skipped because proxy DNS returned a synthetic IP address.",
            )
        elif tcp_result["status"] == "error":
            operation = lambda: skipped_result(
                "tls",
                "TLS",
                "Skipped because TCP failed.",
            )
        else:
            addresses = _connection_addresses(dns_result)
            operation = lambda: check_tls(self.target, addresses, tcp_result)

        return self._run_check("tls", operation)

    def inspect_http(self):
        network_result = self.inspect_client()
        dns_result = self.inspect_dns()

        if dns_result["status"] == "error":
            operation = lambda: skipped_result(
                "http",
                "HTTP",
                "Skipped because DNS failed.",
            )
        elif dns_result.get("proxy_fake_ip"):
            operation = lambda: check_http(
                self.target,
                use_proxy=True,
                allow_proxy_fake_ip=True,
            )
        else:
            use_proxy = network_result.get("proxy_detected", False)
            operation = lambda: check_http(
                self.target,
                use_proxy=use_proxy,
            )

        return self._run_check("http", operation)

    def inspect_traceroute(self):
        dns_result = self.inspect_dns()

        if dns_result["status"] == "error":
            operation = lambda: skipped_traceroute(
                "Skipped because DNS failed.",
            )
        elif dns_result.get("proxy_fake_ip"):
            operation = lambda: skipped_traceroute(
                "Skipped because proxy DNS returned a synthetic IP address.",
            )
        else:
            addresses = _connection_addresses(dns_result)
            operation = lambda: check_traceroute(addresses)

        return self._run_check("traceroute", operation)

    def tool_payload(self, requested_tool, result):
        self.requested_tools.append(
            {
                "tool": requested_tool,
                "status": result["status"],
                "summary": result["summary"],
            }
        )
        return {
            "requested_tool": requested_tool,
            "locked_target": self.target["url"],
            "result": result,
            "available_evidence": [
                self.results[key]
                for key in CHECK_ORDER
                if key in self.results
            ],
            "budget": {
                "checks_used": self.checks_used,
                "checks_remaining": max(0, self.max_checks - self.checks_used),
            },
        }


@function_tool(name_override="inspect_client_network", timeout=6)
async def inspect_client_network_tool(
    context: RunContextWrapper[DiagnosticContext],
) -> dict:
    """Inspect routes and system proxy settings for the locked target's runtime."""
    result = await asyncio.to_thread(context.context.inspect_client)
    return context.context.tool_payload("client", result)


@function_tool(name_override="inspect_dns", timeout=10)
async def inspect_dns_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Resolve and validate DNS addresses for the locked target."""
    result = await asyncio.to_thread(context.context.inspect_dns)
    return context.context.tool_payload("dns", result)


@function_tool(name_override="inspect_tcp", timeout=30)
async def inspect_tcp_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Test TCP connectivity for the locked target after validated DNS."""
    result = await asyncio.to_thread(context.context.inspect_tcp)
    return context.context.tool_payload("tcp", result)


@function_tool(name_override="inspect_tls", timeout=60)
async def inspect_tls_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Test TLS handshake and certificate validity for the locked target."""
    result = await asyncio.to_thread(context.context.inspect_tls)
    return context.context.tool_payload("tls", result)


@function_tool(name_override="inspect_http", timeout=50)
async def inspect_http_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Request the locked URL, validate redirects, and inspect its HTTP response."""
    result = await asyncio.to_thread(context.context.inspect_http)
    return context.context.tool_payload("http", result)


@function_tool(name_override="inspect_traceroute", timeout=15)
async def inspect_traceroute_tool(
    context: RunContextWrapper[DiagnosticContext],
) -> dict:
    """Run a short route trace to a validated address for the locked target."""
    result = await asyncio.to_thread(context.context.inspect_traceroute)
    return context.context.tool_payload("traceroute", result)


AGENT_TOOLS = [
    inspect_client_network_tool,
    inspect_dns_tool,
    inspect_tcp_tool,
    inspect_tls_tool,
    inspect_http_tool,
    inspect_traceroute_tool,
]
