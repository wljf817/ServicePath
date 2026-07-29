import socket
from time import perf_counter

from diagnostics.result import make_result
from diagnostics.target import TargetError, validate_public_addresses


def resolve_addresses(hostname):
    records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    ipv4 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET})
    ipv6 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET6})
    return ipv4, ipv6


def check_dns(target):
    started = perf_counter()

    try:
        ipv4, ipv6 = resolve_addresses(target["hostname"])
        addresses = ipv4 + ipv6
        validate_public_addresses(addresses)
        status = "passed"
        summary = f"Resolved {len(addresses)} public IP address(es)."
        details = {
            "A records": ipv4,
            "AAAA records": ipv6,
            "addresses": addresses,
        }
    except (socket.gaierror, TargetError) as error:
        status = "error"
        summary = f"DNS lookup failed: {error}"
        details = {"A records": [], "AAAA records": [], "addresses": []}

    duration = round((perf_counter() - started) * 1000)
    return make_result("dns", "DNS", status, summary, duration, details)
