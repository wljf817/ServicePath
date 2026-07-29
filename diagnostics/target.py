import ipaddress
from urllib.parse import urlsplit, urlunsplit


PROXY_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")


class TargetError(ValueError):
    """Raised when a target is invalid or unsafe to request."""


def normalize_target(value):
    """Return a safe, normalized HTTP target as a dictionary."""
    value = value.strip()

    if not value:
        raise TargetError("Please enter a website or domain.")

    if len(value) > 2048:
        raise TargetError("The website address is too long.")

    if "://" not in value:
        value = "https://" + value

    parsed = urlsplit(value)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise TargetError("Only http:// and https:// websites are supported.")

    if parsed.username or parsed.password:
        raise TargetError("Website addresses with usernames or passwords are not allowed.")

    if not parsed.hostname:
        raise TargetError("Please enter a valid website or domain.")

    try:
        port = parsed.port
    except ValueError as error:
        raise TargetError("The website port is invalid.") from error

    hostname = parsed.hostname.rstrip(".").lower()

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise TargetError("The domain name is invalid.") from error

    validate_hostname(hostname)

    netloc = hostname
    if ":" in hostname:
        netloc = f"[{hostname}]"
    if port:
        netloc = f"{netloc}:{port}"

    path = parsed.path or "/"
    url = urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))

    return {
        "original": value,
        "hostname": hostname,
        "scheme": parsed.scheme.lower(),
        "port": port,
        "url": url,
    }


def validate_hostname(hostname):
    """Reject local names and literal IP addresses that are not public."""
    local_suffixes = (".local", ".localhost", ".internal", ".lan", ".home")

    if hostname == "localhost" or hostname.endswith(local_suffixes):
        raise TargetError("Local and private hostnames are not allowed.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return

    if not address.is_global:
        raise TargetError("Private, loopback, and reserved IP addresses are not allowed.")


def is_proxy_fake_address(value):
    """Return whether an address is in the standard proxy Fake-IP range."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address in PROXY_FAKE_IP_NETWORK


def validate_public_addresses(addresses, allow_proxy_fake_ip=False):
    """Reject DNS results that point to a non-public network."""
    if not addresses:
        raise TargetError("The domain did not return an IP address.")

    for value in addresses:
        try:
            address = ipaddress.ip_address(value)
        except ValueError as error:
            raise TargetError("The domain returned an invalid IP address.") from error

        proxy_fake_ip = allow_proxy_fake_ip and is_proxy_fake_address(value)
        if not address.is_global and not proxy_fake_ip:
            raise TargetError("The domain resolves to a private or reserved IP address.")
