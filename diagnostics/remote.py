import os
from urllib.parse import urlsplit

import requests


class RemoteError(RuntimeError):
    """Raised when the configured remote diagnostic service cannot be used."""


def _remote_endpoint(service_url=None):
    if service_url is None:
        service_url = os.getenv("REMOTE_SERVICE_URL", "")
    service_url = service_url.strip()

    if not service_url:
        raise RemoteError("Remote Test requires REMOTE_SERVICE_URL in your .env file.")

    parsed = urlsplit(service_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RemoteError("REMOTE_SERVICE_URL must be a valid http:// or https:// URL.")
    if parsed.username or parsed.password:
        raise RemoteError("REMOTE_SERVICE_URL cannot contain a username or password.")

    return service_url.rstrip("/") + "/api/diagnose"


def _validate_report(report):
    if not isinstance(report, dict):
        raise RemoteError("The remote server returned an invalid report.")
    if not isinstance(report.get("target"), dict):
        raise RemoteError("The remote report is missing its target.")
    if not isinstance(report.get("layers"), list) or len(report["layers"]) != 5:
        raise RemoteError("The remote report does not contain five diagnostic layers.")

    allowed_statuses = {"passed", "warning", "error", "skipped"}
    for layer in report["layers"]:
        if not isinstance(layer, dict) or layer.get("status") not in allowed_statuses:
            raise RemoteError("The remote report contains an invalid layer result.")


def run_remote_diagnostics(target, timeout=45, service_url=None):
    endpoint = _remote_endpoint(service_url)
    token = os.getenv("SERVICEPATH_API_TOKEN", "").strip()
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.post(
            endpoint,
            json={"target": target},
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        report = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RemoteError(f"Remote Test failed: {error}") from error

    _validate_report(report)
    report["mode"] = "remote"
    return report
