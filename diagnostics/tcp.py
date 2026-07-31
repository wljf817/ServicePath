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


def check_tcp(target, addresses, timeout=3):
    started = perf_counter()
    port = effective_port(target)
    port_results = {}

    port_started = perf_counter()
    connected_address = None
    last_error = "Connection failed"

    for address in addresses:
        connected, error = _connect(address, port, timeout)
        if connected:
            connected_address = address
            break
        if error:
            last_error = error

    port_results[str(port)] = {
        "status": "passed" if connected_address else "error",
        "address": connected_address,
        "time_ms": round((perf_counter() - port_started) * 1000),
        "error": None if connected_address else last_error,
    }

    if connected_address:
        status = "passed"
        summary = f"TCP connection succeeded on port {port}."
    else:
        status = "error"
        summary = f"TCP port {port} did not accept a connection."

    duration = round((perf_counter() - started) * 1000)
    return make_result(
        "tcp",
        "TCP",
        status,
        summary,
        duration,
        {"ports": port_results},
    )
