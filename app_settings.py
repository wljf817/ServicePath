from urllib.parse import urlsplit


class SettingsError(ValueError):
    """Raised when application settings are invalid."""


def validate_openai_api_mode(value):
    """Normalize the API surface used by the diagnostic Agent."""
    value = str(value or "auto").strip().lower()

    if value not in {"auto", "responses", "chat_completions"}:
        raise SettingsError(
            "Agent API protocol must be Auto, Responses, or Chat Completions."
        )

    return value


def validate_openai_base_url(value):
    """Normalize an optional OpenAI-compatible API base URL."""
    value = str(value).strip().rstrip("/")

    if not value:
        return ""
    if len(value) > 2048 or any(character.isspace() for character in value):
        raise SettingsError("Agent API Base URL is invalid.")

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SettingsError("Agent API Base URL must use http:// or https://.")
    if parsed.username or parsed.password:
        raise SettingsError("Agent API Base URL cannot contain login details.")
    if parsed.query or parsed.fragment:
        raise SettingsError("Agent API Base URL cannot contain a query or fragment.")

    try:
        parsed.port
    except ValueError as error:
        raise SettingsError("Agent API Base URL contains an invalid port.") from error

    return value


def validate_settings(instance_role, remote_service_url):
    if instance_role not in {"remote_server", "local_device"}:
        raise SettingsError("Please select a valid instance role.")

    remote_service_url = remote_service_url.strip().rstrip("/")

    if remote_service_url:
        parsed = urlsplit(remote_service_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SettingsError("Remote Service URL must use http:// or https://.")
        if parsed.username or parsed.password:
            raise SettingsError("Remote Service URL cannot contain login details.")

    return {
        "instance_role": instance_role,
        "remote_service_url": remote_service_url,
    }
