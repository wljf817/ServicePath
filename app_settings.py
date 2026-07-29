from urllib.parse import urlsplit


class SettingsError(ValueError):
    """Raised when application settings are invalid."""


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
