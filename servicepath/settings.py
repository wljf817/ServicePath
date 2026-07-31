import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


class SettingsError(ValueError):
    """Raised when provider or server settings are invalid."""


HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.ASCII)
TOKEN68 = re.compile(r"[A-Za-z0-9\-._~+/]+=*\Z", re.ASCII)


def _normalize_url_host(hostname, label):
    if "%" in hostname:
        raise SettingsError(f"{label} contains an invalid hostname.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if hostname.endswith("."):
            hostname = hostname[:-1]
        try:
            hostname = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as error:
            raise SettingsError(f"{label} contains an invalid hostname.") from error
        labels = hostname.split(".")
        if (
            not hostname
            or len(hostname) > 253
            or any(not HOST_LABEL.fullmatch(item) for item in labels)
        ):
            raise SettingsError(f"{label} contains an invalid hostname.")
        return hostname
    return f"[{address.compressed}]" if address.version == 6 else address.compressed


def _normalize_http_url(value, label):
    value = str(value).strip().rstrip("/")
    if not value:
        return ""
    if len(value) > 2048 or "\\" in value or any(
        character.isspace() or not character.isprintable()
        for character in value
    ):
        raise SettingsError(f"{label} is invalid.")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise SettingsError(f"{label} is invalid.") from error
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise SettingsError(f"{label} must use http:// or https://.")
    if parsed.username is not None or parsed.password is not None:
        raise SettingsError(f"{label} cannot contain login details.")
    if parsed.query or parsed.fragment:
        raise SettingsError(f"{label} cannot contain a query or fragment.")
    if port is None and parsed.netloc.endswith(":"):
        raise SettingsError(f"{label} contains an invalid port.")
    hostname = _normalize_url_host(hostname, label)
    netloc = f"{hostname}:{port}" if port is not None else hostname
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def validate_openai_api_mode(value):
    value = str(value).strip().lower()
    if value not in {"responses", "chat_completions"}:
        raise SettingsError("API protocol must be Responses or Chat Completions.")
    return value


def validate_openai_base_url(value):
    return _normalize_http_url(value, "API Base URL")


def validate_servicepath_server_url(value):
    return _normalize_http_url(value, "Custom Server URL")


def validate_servicepath_server_token(value):
    value = str(value).strip()
    if value and (len(value) > 4096 or not TOKEN68.fullmatch(value)):
        raise SettingsError("Custom Server token contains unsupported characters.")
    return value
