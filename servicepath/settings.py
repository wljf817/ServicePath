import ipaddress
import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values, set_key, unset_key


class SettingsError(ValueError):
    """Raised when application settings are invalid."""


HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.ASCII)
TOKEN68 = re.compile(r"[A-Za-z0-9\-._~+/]+=*\Z", re.ASCII)


def _normalize_url_host(hostname, label):
    """Return a canonical IP address or DNS hostname."""
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
            raise SettingsError(
                f"{label} contains an invalid hostname."
            ) from error

        labels = hostname.split(".")
        if (
            not hostname
            or len(hostname) > 253
            or any(not HOST_LABEL.fullmatch(item) for item in labels)
        ):
            raise SettingsError(f"{label} contains an invalid hostname.")
        return hostname

    if address.version == 6:
        return f"[{address.compressed}]"
    return address.compressed


def _normalize_http_url(value, label):
    """Validate and normalize an optional HTTP endpoint."""
    value = str(value).strip().rstrip("/")

    if not value:
        return ""
    if (
        len(value) > 2048
        or "\\" in value
        or any(
            character.isspace() or not character.isprintable()
            for character in value
        )
    ):
        raise SettingsError(f"{label} is invalid.")

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError as error:
        raise SettingsError(f"{label} is invalid.") from error

    if parsed.scheme not in {"http", "https"} or not hostname:
        raise SettingsError(f"{label} must use http:// or https://.")
    if parsed.username is not None or parsed.password is not None:
        raise SettingsError(f"{label} cannot contain login details.")
    if parsed.query or parsed.fragment:
        raise SettingsError(f"{label} cannot contain a query or fragment.")

    try:
        port = parsed.port
    except ValueError as error:
        raise SettingsError(f"{label} contains an invalid port.") from error

    if port is None and parsed.netloc.endswith(":"):
        raise SettingsError(f"{label} contains an invalid port.")

    hostname = _normalize_url_host(hostname, label)
    netloc = f"{hostname}:{port}" if port is not None else hostname
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def validate_openai_api_mode(value):
    """Normalize the API surface used by the diagnostic agent."""
    value = str(value or "auto").strip().lower()

    if value not in {"auto", "responses", "chat_completions"}:
        raise SettingsError(
            "Agent API protocol must be Auto, Responses, or Chat Completions."
        )

    return value


def validate_openai_base_url(value):
    """Normalize an optional OpenAI-compatible API base URL."""
    return _normalize_http_url(value, "Agent API Base URL")


def validate_servicepath_api_token(value):
    """Normalize a Bearer token accepted by the remote API."""
    value = str(value).strip()
    if value and (len(value) > 4096 or not TOKEN68.fullmatch(value)):
        raise SettingsError("Remote API token contains unsupported characters.")
    return value


def validate_settings(instance_role, remote_service_url):
    instance_role = str(instance_role).strip()
    if instance_role not in {"remote_server", "local_device"}:
        raise SettingsError("Please select a valid instance role.")

    remote_service_url = _normalize_http_url(
        remote_service_url,
        "Remote Service URL",
    )

    return {
        "instance_role": instance_role,
        "remote_service_url": remote_service_url,
    }


def _secure_env_file(env_path):
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.touch(mode=0o600, exist_ok=True)
    env_path.chmod(0o600)


def _write_environment_value(env_path, name, value):
    _secure_env_file(env_path)
    set_key(str(env_path), name, value)
    os.environ[name] = value


def _remove_environment_value(env_path, name):
    if env_path.exists() and name in dotenv_values(env_path):
        unset_key(str(env_path), name)
    os.environ.pop(name, None)


def update_environment_settings(env_file, data):
    """Persist supplied runtime settings without exposing existing secrets."""
    base_url_supplied = "openai_base_url" in data
    base_url = validate_openai_base_url(data.get("openai_base_url", ""))
    api_mode_supplied = "openai_api_mode" in data
    api_mode = validate_openai_api_mode(data.get("openai_api_mode", "auto"))
    api_token = validate_servicepath_api_token(
        data.get("servicepath_api_token", "")
    )
    values = {
        "SERVICEPATH_API_TOKEN": api_token,
        "OPENAI_API_KEY": data.get("openai_api_key", ""),
        "OPENAI_MODEL": data.get("openai_model", ""),
        "SETTINGS_PASSWORD": data.get("new_settings_password", ""),
    }
    env_path = Path(env_file)

    for name, value in values.items():
        value = str(value).strip()
        if value:
            _write_environment_value(env_path, name, value)

    if base_url_supplied:
        if base_url:
            _write_environment_value(env_path, "OPENAI_BASE_URL", base_url)
        else:
            _remove_environment_value(env_path, "OPENAI_BASE_URL")

    if api_mode_supplied:
        _write_environment_value(env_path, "OPENAI_API_MODE", api_mode)
