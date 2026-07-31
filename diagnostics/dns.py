import ipaddress
from time import perf_counter

import dns.exception
import dns.flags
import dns.resolver

from diagnostics.result import make_result
from diagnostics.target import (
    TargetError,
    is_proxy_fake_address,
    validate_public_addresses,
)


DNS_TIMEOUT_SECONDS = 4


def _resolver():
    resolver = dns.resolver.Resolver()
    resolver.timeout = DNS_TIMEOUT_SECONDS
    resolver.lifetime = DNS_TIMEOUT_SECONDS
    resolver.retry_servfail = False
    resolver.use_edns(edns=0, ednsflags=dns.flags.DO, payload=1232)
    return resolver


def _records(resolver, hostname, record_type):
    answer = resolver.resolve(
        hostname,
        record_type,
        lifetime=DNS_TIMEOUT_SECONDS,
        raise_on_no_answer=False,
        search=False,
    )
    if answer.rrset is None:
        return [], None, answer
    return [record.to_text() for record in answer], answer.rrset.ttl, answer


def _address_records(resolver, hostname):
    ipv4, ipv4_ttl, ipv4_answer = _records(resolver, hostname, "A")
    ipv6, ipv6_ttl, ipv6_answer = _records(resolver, hostname, "AAAA")
    return ipv4, ipv6, ipv4_ttl, ipv6_ttl, (ipv4_answer, ipv6_answer)


def _literal_addresses(hostname):
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return None
    if address.version == 4:
        return [address.compressed], []
    return [], [address.compressed]


def resolve_addresses(hostname):
    literal = _literal_addresses(hostname)
    if literal is not None:
        return literal
    resolver = _resolver()
    ipv4, ipv6, _, _, _ = _address_records(resolver, hostname)
    return sorted(set(ipv4)), sorted(set(ipv6))


def _dns_metadata(resolver, hostname, ipv4_ttl, ipv6_ttl, address_answers):
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return {
            "Canonical name": "Not applicable to an IP address",
            "Authoritative zone": "Not applicable to an IP address",
            "NS records": [],
            "SOA record": "Not applicable to an IP address",
            "A TTL": ipv4_ttl,
            "AAAA TTL": ipv6_ttl,
            "DNSSEC": "Not applicable to an IP address",
        }

    cname_records, _, _ = _records(resolver, hostname, "CNAME")
    zone = dns.resolver.zone_for_name(hostname, resolver=resolver)
    ns_records, _, _ = _records(resolver, zone, "NS")
    soa_records, _, _ = _records(resolver, zone, "SOA")
    dnssec_validated = any(
        answer.response.flags & dns.flags.AD
        for answer in address_answers
        if answer.response is not None
    )

    return {
        "Canonical name": cname_records[0] if cname_records else "Direct record",
        "Authoritative zone": zone.to_text(),
        "NS records": ns_records,
        "SOA record": soa_records[0] if soa_records else "Not returned",
        "A TTL": ipv4_ttl,
        "AAAA TTL": ipv6_ttl,
        "DNSSEC": "Validated" if dnssec_validated else "Not confirmed",
    }


def check_dns(target, allow_proxy_fake_ip=False):
    started = perf_counter()
    proxy_fake_ips = []

    try:
        literal = _literal_addresses(target["hostname"])
        if literal is None:
            resolver = _resolver()
            (
                ipv4,
                ipv6,
                ipv4_ttl,
                ipv6_ttl,
                address_answers,
            ) = _address_records(resolver, target["hostname"])
            ipv4 = sorted(set(ipv4))
            ipv6 = sorted(set(ipv6))
        else:
            ipv4, ipv6 = literal
            ipv4_ttl = ipv6_ttl = None
            address_answers = ()
            resolver = None
        addresses = ipv4 + ipv6
        validate_public_addresses(addresses, allow_proxy_fake_ip)
        metadata = _dns_metadata(
            resolver,
            target["hostname"],
            ipv4_ttl,
            ipv6_ttl,
            address_answers,
        )
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
            **metadata,
        }
    except (dns.exception.DNSException, TargetError) as error:
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
