import socket
import ssl
from datetime import datetime, timezone
from time import perf_counter

import certifi

from diagnostics.result import make_result
from diagnostics.target import effective_port


def _handshake(target, address, port, timeout):
    context = ssl.create_default_context(cafile=certifi.where())
    raw_socket = None
    secure_socket = None
    started = perf_counter()

    try:
        raw_socket = socket.create_connection((address, port), timeout=timeout)
        secure_socket = context.wrap_socket(
            raw_socket,
            server_hostname=target["hostname"],
        )
        certificate = secure_socket.getpeercert()
        expires_at = datetime.fromtimestamp(
            ssl.cert_time_to_seconds(certificate.get("notAfter")),
            timezone.utc,
        )
        days_left = (expires_at - datetime.now(timezone.utc)).days
        cipher = secure_socket.cipher()
        return {
            "status": "warning" if days_left < 14 else "passed",
            "address": address,
            "time_ms": round((perf_counter() - started) * 1000),
            "error": None,
            "TLS version": secure_socket.version(),
            "Cipher": cipher[0] if cipher else "Unknown",
            "Certificate expires": expires_at.isoformat(),
            "Days remaining": days_left,
        }
    except (OSError, ssl.SSLError, ValueError) as error:
        return {
            "status": "error",
            "address": address,
            "time_ms": round((perf_counter() - started) * 1000),
            "error": str(error),
        }
    finally:
        if secure_socket:
            secure_socket.close()
        elif raw_socket:
            raw_socket.close()


def check_tls(target, tcp_result, timeout=4):
    if target["scheme"] != "https":
        return make_result(
            "tls",
            "TLS",
            "skipped",
            "TLS does not apply to an HTTP target.",
        )

    started = perf_counter()
    port = effective_port(target)
    families = {}

    for family, tcp_family in tcp_result["details"]["Address families"].items():
        if tcp_family["status"] == "passed":
            families[family] = _handshake(
                target,
                tcp_family["address"],
                port,
                timeout,
            )
        else:
            families[family] = {
                "status": "skipped",
                "address": tcp_family["address"],
                "time_ms": 0,
                "error": "TCP unavailable for this address family",
            }

    attempted = [
        result for result in families.values()
        if result["status"] != "skipped"
    ]
    passed = sum(result["status"] == "passed" for result in attempted)
    warned = sum(result["status"] == "warning" for result in attempted)

    if attempted and passed == len(attempted):
        status = "passed"
        summary = "TLS validation succeeded on every connected address family."
    elif passed or warned:
        status = "warning"
        summary = "TLS validation was incomplete on the available address families."
    else:
        status = "error"
        summary = "TLS validation failed on every connected address family."

    duration = round((perf_counter() - started) * 1000)
    return make_result(
        "tls",
        "TLS",
        status,
        summary,
        duration,
        {
            "Port": port,
            "SNI hostname": target["hostname"],
            "Address families": families,
        },
    )
