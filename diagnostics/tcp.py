import socket
from time import perf_counter

from diagnostics.result import make_result
from diagnostics.target import effective_port


def _connect(address, port, timeout):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    connection = socket.socket(family, socket.SOCK_STREAM)
    connection.settimeout(timeout)

    try:
        destination = (
            (address, port, 0, 0)
            if family == socket.AF_INET6
            else (address, port)
        )
        connection.connect(destination)
        return True, None
    except OSError as error:
        return False, str(error)
    finally:
        connection.close()


def _family_result(addresses, port, timeout):
    if not addresses:
        return {
            "status": "skipped",
            "address": None,
            "time_ms": 0,
            "error": "No DNS address for this family",
        }

    address = addresses[0]
    started = perf_counter()
    connected, error = _connect(address, port, timeout)
    return {
        "status": "passed" if connected else "error",
        "address": address,
        "time_ms": round((perf_counter() - started) * 1000),
        "error": error,
    }


def check_tcp(target, addresses, timeout=3):
    started = perf_counter()
    port = effective_port(target)
    families = {
        "IPv4": _family_result(
            [address for address in addresses if ":" not in address],
            port,
            timeout,
        ),
        "IPv6": _family_result(
            [address for address in addresses if ":" in address],
            port,
            timeout,
        ),
    }
    attempted = [
        result for result in families.values()
        if result["status"] != "skipped"
    ]
    passed = sum(result["status"] == "passed" for result in attempted)

    if attempted and passed == len(attempted):
        status = "passed"
        summary = f"TCP port {port} accepted every available address family."
    elif passed:
        status = "warning"
        summary = f"TCP port {port} worked on only one address family."
    else:
        status = "error"
        summary = f"TCP port {port} did not accept any connection."

    duration = round((perf_counter() - started) * 1000)
    return make_result(
        "tcp",
        "TCP",
        status,
        summary,
        duration,
        {"Port": port, "Address families": families},
    )
