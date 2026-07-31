import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


PROXY_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")
HOST_LABEL_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z",
    re.IGNORECASE,
)


class TargetError(ValueError):
    """Raised when a target is invalid or unsafe to request."""


def normalize_target(value):
    """Return a safe, normalized HTTP target as a dictionary."""
    if not isinstance(value, str):
        raise TargetError("Please enter a website or domain.")

    value = value.strip()

    if not value:
        raise TargetError("Please enter a website or domain.")

    if len(value) > 2048:
        raise TargetError("The website address is too long.")
    if "\\" in value or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in value
    ):
        raise TargetError("The website address is invalid.")

    if "://" not in value:
        value = "https://" + value

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise TargetError("Please enter a valid website or domain.") from error

    if parsed.scheme.lower() not in {"http", "https"}:
        raise TargetError("Only http:// and https:// websites are supported.")

    if parsed.username is not None or parsed.password is not None:
        raise TargetError(
            "Website addresses with usernames or passwords are not allowed."
        )

    if not hostname:
        raise TargetError("Please enter a valid website or domain.")

    if parsed.netloc.endswith(":"):
        raise TargetError("The website port is invalid.")
    if port is not None and not 1 <= port <= 65535:
        raise TargetError("The website port is invalid.")

    hostname = normalize_hostname(hostname)
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


def normalize_hostname(hostname):
    """Return a canonical hostname after strict syntax validation."""
    hostname = hostname.lower()
    if hostname.endswith("."):
        hostname = hostname[:-1]
    if not hostname or "%" in hostname:
        raise TargetError("The domain name is invalid.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise TargetError("The domain name is invalid.") from error

        if len(hostname) > 253:
            raise TargetError("The domain name is invalid.")

        labels = hostname.split(".")
        if not labels or any(
            not HOST_LABEL_PATTERN.fullmatch(label) for label in labels
        ):
            raise TargetError("The domain name is invalid.")

        for label in labels:
            if not label.startswith("xn--"):
                continue
            try:
                label.encode("ascii").decode("idna")
            except UnicodeError as error:
                raise TargetError("The domain name is invalid.") from error
        return hostname

    return address.compressed


def validate_hostname(hostname):
    """Reject local names and literal addresses that are not public."""
    local_suffixes = (".local", ".localhost", ".internal", ".lan", ".home")

    if hostname == "localhost" or hostname.endswith(local_suffixes):
        raise TargetError("Local and private hostnames are not allowed.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return

    if not address.is_global:
        raise TargetError(
            "Private, loopback, and reserved IP addresses are not allowed."
        )


def effective_port(target):
    """Return the explicit port or the default for the target scheme."""
    return target["port"] or {"http": 80, "https": 443}[target["scheme"]]


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
            raise TargetError(
                "The domain resolves to a private or reserved IP address."
            )
