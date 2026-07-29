import socket
from time import perf_counter

from diagnostics.result import make_result


def _connect(address, port, timeout):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    connection = socket.socket(family, socket.SOCK_STREAM)
    connection.settimeout(timeout)

    try:
        destination = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
        connection.connect(destination)
        return True, None
    except OSError as error:
        return False, str(error)
    finally:
        connection.close()


def check_tcp(target, addresses, timeout=3):
    started = perf_counter()
    ports = [target["port"]] if target["port"] else [80, 443]
    port_results = {}

    for port in ports:
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

    passed_ports = [port for port, result in port_results.items() if result["status"] == "passed"]

    if len(passed_ports) == len(port_results):
        status = "passed"
        summary = "TCP connection succeeded on " + ", ".join(passed_ports) + "."
    elif passed_ports:
        status = "warning"
        summary = "Only TCP port(s) " + ", ".join(passed_ports) + " accepted a connection."
    else:
        status = "error"
        summary = "No tested TCP port accepted a connection."

    duration = round((perf_counter() - started) * 1000)
    return make_result(
        "tcp",
        "TCP",
        status,
        summary,
        duration,
        {"ports": port_results},
    )
