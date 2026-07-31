import asyncio
from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable

from agents import RunContextWrapper, function_tool

from diagnostics.dns import check_dns
from diagnostics.http import check_http
from diagnostics.network import check_client_network
from diagnostics.result import skipped_result
from diagnostics.tcp import check_tcp
from diagnostics.tls import check_tls
from diagnostics.traceroute import check_traceroute, skipped_traceroute


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
    event_handler: Callable[[dict], None] | None = None
    results: dict[str, dict] = field(default_factory=dict)
    tool_log: list[dict] = field(default_factory=list)
    checks_used: int = 0

    def emit(self, event):
        if self.event_handler:
            self.event_handler(event)

    def _run_check(self, key, operation: Callable[[], dict]):
        cached = self.results.get(key)
        if cached is not None:
            return cached

        self.checks_used += 1
        started = perf_counter()
        result = operation()
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
        if self.target["scheme"] != "https":
            return self._run_check(
                "tls",
                lambda: skipped_result(
                    "tls",
                    "TLS",
                    "TLS does not apply to an HTTP target.",
                ),
            )

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
            operation = lambda: check_tls(self.target, tcp_result)

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
        return {
            "requested_tool": requested_tool,
            "locked_target": self.target["url"],
            "result": result,
            "available_evidence": [
                self.results[key]
                for key in CHECK_ORDER
                if key in self.results
            ],
        }

    async def invoke_tool(self, key, operation):
        self.emit({"type": "tool_started", "tool": key})
        try:
            result = await asyncio.to_thread(operation)
        except Exception as error:
            self.emit(
                {
                    "type": "tool_failed",
                    "tool": key,
                    "error": str(error),
                }
            )
            raise

        payload = self.tool_payload(key, result)
        self.emit(
            {
                "type": "tool_completed",
                "tool": key,
                "result": result,
            }
        )
        return payload


@function_tool(
    name_override="inspect_client_network",
    failure_error_function=None,
    timeout=6,
    timeout_behavior="raise_exception",
)
async def inspect_client_network_tool(
    context: RunContextWrapper[DiagnosticContext],
) -> dict:
    """Inspect routes and system proxy settings for the locked target's runtime."""
    return await context.context.invoke_tool(
        "client",
        context.context.inspect_client,
    )


@function_tool(
    name_override="inspect_dns",
    failure_error_function=None,
    timeout=10,
    timeout_behavior="raise_exception",
)
async def inspect_dns_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Resolve and validate DNS addresses for the locked target."""
    return await context.context.invoke_tool("dns", context.context.inspect_dns)


@function_tool(
    name_override="inspect_tcp",
    failure_error_function=None,
    timeout=30,
    timeout_behavior="raise_exception",
)
async def inspect_tcp_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Test TCP connectivity for the locked target after validated DNS."""
    return await context.context.invoke_tool("tcp", context.context.inspect_tcp)


@function_tool(
    name_override="inspect_tls",
    failure_error_function=None,
    timeout=60,
    timeout_behavior="raise_exception",
)
async def inspect_tls_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Test TLS handshake and certificate validity for the locked target."""
    return await context.context.invoke_tool("tls", context.context.inspect_tls)


@function_tool(
    name_override="inspect_http",
    failure_error_function=None,
    timeout=50,
    timeout_behavior="raise_exception",
)
async def inspect_http_tool(context: RunContextWrapper[DiagnosticContext]) -> dict:
    """Request the locked URL, validate redirects, and inspect its HTTP response."""
    return await context.context.invoke_tool("http", context.context.inspect_http)


@function_tool(
    name_override="inspect_traceroute",
    failure_error_function=None,
    timeout=15,
    timeout_behavior="raise_exception",
)
async def inspect_traceroute_tool(
    context: RunContextWrapper[DiagnosticContext],
) -> dict:
    """Run a short route trace to a validated address for the locked target."""
    return await context.context.invoke_tool(
        "traceroute",
        context.context.inspect_traceroute,
    )


AGENT_TOOLS = [
    inspect_client_network_tool,
    inspect_dns_tool,
    inspect_tcp_tool,
    inspect_tls_tool,
    inspect_http_tool,
    inspect_traceroute_tool,
]
