from datetime import datetime, timezone
from time import perf_counter

from diagnostics.dns import check_dns
from diagnostics.http import check_http
from diagnostics.network import check_client_network
from diagnostics.result import skipped_result
from diagnostics.target import normalize_target
from diagnostics.tcp import check_tcp
from diagnostics.tls import check_tls


def _overall_status(layers):
    statuses = {layer["status"] for layer in layers}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "passed"


def _first_problem(layers):
    for wanted_status in ("error", "warning"):
        for layer in layers:
            if layer["status"] == wanted_status:
                return layer["key"]
    return None


def run_diagnostics(value, mode="local"):
    """Run each diagnostic layer and return one structured report."""
    started = perf_counter()
    target = normalize_target(value)
    layers = []

    network_result = check_client_network()
    layers.append(network_result)

    proxy_detected = network_result.get("proxy_detected", False)
    allow_proxy_fake_ip = proxy_detected
    dns_result = check_dns(target, allow_proxy_fake_ip=allow_proxy_fake_ip)
    layers.append(dns_result)

    if dns_result["status"] == "error":
        layers.extend(
            [
                skipped_result("tcp", "TCP", "Skipped because DNS failed."),
                skipped_result("tls", "TLS", "Skipped because DNS failed."),
                skipped_result("http", "HTTP", "Skipped because DNS failed."),
            ]
        )
    elif dns_result.get("proxy_fake_ip"):
        layers.extend(
            [
                skipped_result(
                    "tcp",
                    "TCP",
                    "Skipped because proxy DNS returned a synthetic IP address.",
                ),
                skipped_result(
                    "tls",
                    "TLS",
                    "Skipped because proxy DNS returned a synthetic IP address.",
                ),
                check_http(
                    target,
                    use_proxy=True,
                    allow_proxy_fake_ip=True,
                ),
            ]
        )
    else:
        addresses = dns_result["details"]["addresses"]
        tcp_result = check_tcp(target, addresses)
        layers.append(tcp_result)

        if tcp_result["status"] == "error":
            layers.extend(
                [
                    skipped_result("tls", "TLS", "Skipped because TCP failed."),
                    skipped_result("http", "HTTP", "Skipped because TCP failed."),
                ]
            )
        else:
            tls_result = check_tls(target, addresses, tcp_result)
            layers.append(tls_result)

            if target["scheme"] == "https" and tls_result["status"] == "error":
                layers.append(
                    skipped_result("http", "HTTP", "Skipped because the TLS handshake failed.")
                )
            else:
                layers.append(check_http(target))

    return {
        "target": target,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": round((perf_counter() - started) * 1000),
        "status": _overall_status(layers),
        "first_problem": _first_problem(layers),
        "layers": layers,
    }
