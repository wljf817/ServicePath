import socket
from time import perf_counter

from diagnostics.result import make_result
from diagnostics.target import (
    TargetError,
    is_proxy_fake_address,
    validate_public_addresses,
)


def resolve_addresses(hostname):
    records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    ipv4 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET})
    ipv6 = sorted({record[4][0] for record in records if record[0] == socket.AF_INET6})
    return ipv4, ipv6


def check_dns(target, allow_proxy_fake_ip=False):
    started = perf_counter()
    proxy_fake_ips = []

    try:
        ipv4, ipv6 = resolve_addresses(target["hostname"])
        addresses = ipv4 + ipv6
        validate_public_addresses(addresses, allow_proxy_fake_ip)
        proxy_fake_ips = [
            address for address in addresses if is_proxy_fake_address(address)
        ]

        if proxy_fake_ips:
            status = "warning"
            summary = "DNS returned a proxy-managed Fake-IP address."
        else:
            status = "passed"
            summary = f"Resolved {len(addresses)} public IP address(es)."

        details = {
            "Hostname": target["hostname"],
            "A records": ipv4,
            "AAAA records": ipv6,
            "addresses": addresses,
            "Proxy Fake-IP": proxy_fake_ips or "Not detected",
        }
    except (socket.gaierror, TargetError) as error:
        status = "error"
        summary = f"DNS lookup failed: {error}"
        details = {
            "Hostname": target["hostname"],
            "A records": [],
            "AAAA records": [],
            "addresses": [],
            "Error": str(error),
        }

    duration = round((perf_counter() - started) * 1000)
    result = make_result("dns", "DNS", status, summary, duration, details)
    result["proxy_fake_ip"] = bool(proxy_fake_ips)
    return result
