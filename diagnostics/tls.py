import socket
import ssl
from datetime import datetime, timezone
from time import perf_counter

import certifi

from diagnostics.result import make_result
from diagnostics.target import effective_port


def check_tls(target, addresses, tcp_result, timeout=4):
    if target["scheme"] != "https":
        return make_result(
            "tls",
            "TLS",
            "skipped",
            "TLS does not apply to an HTTP target.",
        )

    started = perf_counter()
    port = effective_port(target)
    tcp_port = tcp_result["details"]["ports"].get(str(port), {})

    if tcp_port.get("status") != "passed":
        return make_result(
            "tls",
            "TLS",
            "skipped",
            f"TLS check skipped because TCP port {port} is unavailable.",
            details={
                "Port": port,
                "SNI hostname": target["hostname"],
                "TCP status": "Unavailable",
            },
        )

    context = ssl.create_default_context(cafile=certifi.where())
    last_error = "TLS handshake failed"

    for address in addresses:
        raw_socket = None
        secure_socket = None

        try:
            raw_socket = socket.create_connection((address, port), timeout=timeout)
            secure_socket = context.wrap_socket(
                raw_socket,
                server_hostname=target["hostname"],
            )
            certificate = secure_socket.getpeercert()
            expires_text = certificate.get("notAfter")
            expires_at = datetime.fromtimestamp(
                ssl.cert_time_to_seconds(expires_text),
                timezone.utc,
            )
            days_left = (expires_at - datetime.now(timezone.utc)).days
            cipher = secure_socket.cipher()
            duration = round((perf_counter() - started) * 1000)
            details = {
                "Port": port,
                "Connected address": address,
                "SNI hostname": target["hostname"],
                "Certificate trusted": "Yes",
                "Hostname matches": "Yes",
                "TLS version": secure_socket.version(),
                "Cipher": cipher[0] if cipher else "Unknown",
                "Certificate expires": expires_at.isoformat(),
                "Days remaining": days_left,
            }

            if days_left < 14:
                return make_result(
                    "tls",
                    "TLS",
                    "warning",
                    f"The certificate is valid but expires in {days_left} day(s).",
                    duration,
                    details,
                )

            return make_result(
                "tls",
                "TLS",
                "passed",
                "TLS handshake and certificate validation succeeded.",
                duration,
                details,
            )
        except (OSError, ssl.SSLError, ValueError) as error:
            last_error = str(error)
        finally:
            if secure_socket:
                secure_socket.close()
            elif raw_socket:
                raw_socket.close()

    duration = round((perf_counter() - started) * 1000)
    return make_result(
        "tls",
        "TLS",
        "error",
        f"TLS handshake failed: {last_error}",
        duration,
        {
            "Port": port,
            "SNI hostname": target["hostname"],
            "TLS handshake": "Failed",
            "Certificate trusted": "Not confirmed",
            "Hostname matches": "Not confirmed",
            "Error": last_error,
        },
    )
