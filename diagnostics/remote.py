import os
from urllib.parse import urlsplit

import requests

from diagnostics.target import normalize_target


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


def _validate_report(report, expected_target):
    if not isinstance(report, dict):
        raise RemoteError("The remote server returned an invalid report.")
    if not isinstance(report.get("target"), dict):
        raise RemoteError("The remote report is missing its target.")
    if report["target"].get("url") != expected_target["url"]:
        raise RemoteError("The remote report target does not match the request.")
    if report.get("mode") != "remote":
        raise RemoteError("The remote report has an invalid execution mode.")
    if report.get("status") not in {"passed", "warning", "error"}:
        raise RemoteError("The remote report has an invalid overall status.")
    if (
        not isinstance(report.get("created_at"), str)
        or not isinstance(report.get("duration_ms"), (int, float))
    ):
        raise RemoteError("The remote report is missing run metadata.")
    if not isinstance(report.get("layers"), list) or not report["layers"]:
        raise RemoteError("The remote report does not contain diagnostic evidence.")
    if (
        not isinstance(report.get("analysis"), dict)
        or report["analysis"].get("source") != "agent"
    ):
        raise RemoteError("The remote report is missing its agent analysis.")
    if not isinstance(report.get("agent"), dict):
        raise RemoteError("The remote report is missing its agent trace.")

    allowed_statuses = {"passed", "warning", "error", "skipped"}
    allowed_keys = {"client", "dns", "tcp", "tls", "http"}
    seen_keys = set()
    for layer in report["layers"]:
        if (
            not isinstance(layer, dict)
            or layer.get("status") not in allowed_statuses
            or layer.get("key") not in allowed_keys
            or layer["key"] in seen_keys
            or not isinstance(layer.get("name"), str)
            or not isinstance(layer.get("summary"), str)
            or not isinstance(layer.get("details"), dict)
            or not isinstance(layer.get("duration_ms"), (int, float))
        ):
            raise RemoteError("The remote report contains an invalid layer result.")
        seen_keys.add(layer["key"])

    traceroute = report.get("traceroute")
    if traceroute is not None and (
        not isinstance(traceroute, dict)
        or traceroute.get("key") != "traceroute"
        or traceroute.get("status") not in allowed_statuses
        or not isinstance(traceroute.get("details"), dict)
    ):
        raise RemoteError("The remote report contains an invalid traceroute result.")


def run_remote_diagnostics(target, timeout=120, service_url=None):
    normalized_target = normalize_target(target)
    endpoint = _remote_endpoint(service_url)
    token = os.getenv("SERVICEPATH_API_TOKEN", "").strip()
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.post(
            endpoint,
            json={"target": normalized_target["url"]},
            headers=headers,
            timeout=timeout,
        )
        if not response.ok:
            try:
                remote_message = response.json().get("error", "")
            except (AttributeError, ValueError):
                remote_message = ""
            if remote_message:
                raise RemoteError(f"Remote Test failed: {remote_message[:500]}")
            response.raise_for_status()
        report = response.json()
    except RemoteError:
        raise
    except (requests.RequestException, ValueError) as error:
        raise RemoteError(f"Remote Test failed: {error}") from error

    _validate_report(report, normalized_target)
    report["mode"] = "remote"
    return report
