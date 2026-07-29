import socket
from time import perf_counter
from urllib.request import getproxies

from diagnostics.result import make_result


def _outbound_address(family, destination):
    connection = socket.socket(family, socket.SOCK_DGRAM)
    connection.settimeout(2)

    try:
        connection.connect(destination)
        return connection.getsockname()[0]
    except OSError:
        return None
    finally:
        connection.close()


def check_client_network():
    """Inspect local routes and proxy settings without sending test data."""
    started = perf_counter()
    ipv4 = _outbound_address(socket.AF_INET, ("1.1.1.1", 53))
    ipv6 = _outbound_address(
        socket.AF_INET6,
        ("2606:4700:4700::1111", 53, 0, 0),
    )
    proxies = {
        name: value
        for name, value in getproxies().items()
        if name.lower() in {"http", "https", "all", "socks"} and value
    }

    details = {
        "IPv4 route": ipv4 or "Unavailable",
        "IPv6 route": ipv6 or "Unavailable",
        "Proxy": ", ".join(sorted(proxies)) if proxies else "Not detected",
    }

    if not ipv4 and not ipv6:
        status = "error"
        summary = "No outbound IPv4 or IPv6 route was detected."
    elif proxies:
        status = "warning"
        summary = "A network route is available, but proxy settings were detected."
    elif not ipv6:
        status = "warning"
        summary = "IPv4 is available; IPv6 was not detected."
    else:
        status = "passed"
        summary = "IPv4 and IPv6 routes are available."

    duration = round((perf_counter() - started) * 1000)
    result = make_result(
        "client",
        "Client Network",
        status,
        summary,
        duration,
        details,
    )
    result["proxy_detected"] = bool(proxies)
    return result
