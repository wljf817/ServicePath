import json
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from servicepath.settings import (
    SettingsError,
    validate_servicepath_server_token,
    validate_servicepath_server_url,
)
from servicepath.streaming import NDJSON_MIMETYPE


MAX_EVENT_BYTES = 1024 * 1024
REMOTE_TIMEOUT_SECONDS = 300
STREAM_EVENTS = frozenset({
    "run_started",
    "tool_started",
    "tool_completed",
    "tool_failed",
})


class RemoteError(RuntimeError):
    """Raised when a custom ServicePath server rejects or breaks a run."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, url):
        return None


def _configuration(server):
    if not isinstance(server, dict):
        raise RemoteError("Custom Server configuration must be an object.")
    try:
        server_url = validate_servicepath_server_url(server.get("url", ""))
        token = validate_servicepath_server_token(server.get("token", ""))
    except SettingsError as error:
        raise RemoteError(str(error)) from error
    if not server_url or not token:
        raise RemoteError("Custom Server URL and token must be configured.")
    return server_url, token


def _event(line):
    if len(line) > MAX_EVENT_BYTES:
        raise RemoteError("Custom Server returned an oversized event.")
    try:
        event = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RemoteError("Custom Server returned an invalid event.") from error
    if not isinstance(event, dict) or not isinstance(event.get("type"), str):
        raise RemoteError("Custom Server returned an invalid event.")
    return event


def run_remote_diagnostics(target, server, provider, event_handler=None):
    """Run one diagnosis on the configured ServicePath server."""
    server_url, token = _configuration(server)
    request = Request(
        f"{server_url}/api/diagnose",
        data=json.dumps({"target": target, "provider": provider}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        response = build_opener(_NoRedirects).open(
            request,
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
    except HTTPError as error:
        message = error.read(4096).decode(errors="replace")
        try:
            payload = json.loads(message)
            if isinstance(payload, dict):
                message = payload.get("error", message)
        except json.JSONDecodeError:
            pass
        raise RemoteError(f"Custom Server rejected the request: {message}") from error
    except URLError as error:
        raise RemoteError(f"Custom Server connection failed: {error.reason}") from error

    with response:
        content_type = response.headers.get_content_type()
        if content_type != NDJSON_MIMETYPE:
            raise RemoteError("Custom Server returned an invalid content type.")

        report = None
        deadline = monotonic() + REMOTE_TIMEOUT_SECONDS
        for line in response:
            if monotonic() > deadline:
                raise RemoteError("Custom Server exceeded its time limit.")
            event = _event(line)
            event_type = event["type"]
            if event_type in STREAM_EVENTS:
                if event_type != "run_started" and event_handler:
                    event_handler(event)
            elif event_type == "error":
                raise RemoteError(str(event.get("error", "Custom Server failed.")))
            elif event_type == "complete" and report is None:
                report = event.get("result")
            else:
                raise RemoteError("Custom Server returned an unexpected event.")

    if not isinstance(report, dict):
        raise RemoteError("Custom Server did not return a report.")
    return report
