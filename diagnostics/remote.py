import json
import math
import os
from datetime import datetime
from time import monotonic
from urllib.parse import urlsplit, urlunsplit

import requests

from diagnostics.target import TargetError, normalize_hostname, normalize_target
from servicepath.settings import SettingsError, validate_servicepath_api_token


MAX_REMOTE_RESPONSE_BYTES = 1024 * 1024
NDJSON_MIMETYPE = "application/x-ndjson"
LAYER_STATUSES = {"passed", "warning", "error", "skipped"}
LAYER_KEYS = {"client", "dns", "tcp", "tls", "http"}
FAILURE_STAGES = {"client", "dns", "route", "tcp", "tls", "http", "application"}


class RemoteError(RuntimeError):
    """Raised when the configured remote diagnostic service cannot be used."""


def _remote_endpoint():
    service_url = os.getenv("REMOTE_SERVICE_URL", "")
    if not isinstance(service_url, str):
        raise RemoteError("REMOTE_SERVICE_URL is invalid.")
    service_url = service_url.strip()

    if not service_url:
        raise RemoteError("Server Test requires REMOTE_SERVICE_URL in your .env file.")

    if (
        len(service_url) > 2048
        or "\\" in service_url
        or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in service_url
        )
    ):
        raise RemoteError("REMOTE_SERVICE_URL is invalid.")

    try:
        parsed = urlsplit(service_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise RemoteError("REMOTE_SERVICE_URL is invalid.") from error

    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise RemoteError("REMOTE_SERVICE_URL must be a valid http:// or https:// URL.")
    if parsed.username is not None or parsed.password is not None:
        raise RemoteError("REMOTE_SERVICE_URL cannot contain a username or password.")
    if parsed.query or parsed.fragment:
        raise RemoteError("REMOTE_SERVICE_URL cannot contain a query or fragment.")
    if parsed.netloc.endswith(":") or (port is not None and not 1 <= port <= 65535):
        raise RemoteError("REMOTE_SERVICE_URL contains an invalid port.")

    try:
        hostname = normalize_hostname(hostname)
    except TargetError as error:
        raise RemoteError("REMOTE_SERVICE_URL contains an invalid hostname.") from error

    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc = f"{netloc}:{port}"

    path = parsed.path.rstrip("/") + "/api/diagnose"
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def _check_deadline(deadline):
    if monotonic() > deadline:
        raise RemoteError("Server Test exceeded its time limit.")


def _response_json(response, deadline):
    _check_deadline(deadline)
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            announced_size = int(content_length)
        except (TypeError, ValueError) as error:
            raise RemoteError(
                "The remote server returned an invalid response size."
            ) from error
        if announced_size < 0 or announced_size > MAX_REMOTE_RESPONSE_BYTES:
            raise RemoteError("The remote server response is too large.")

    body = bytearray()
    for chunk in response.iter_content(chunk_size=8192):
        _check_deadline(deadline)
        if not chunk:
            continue
        body.extend(chunk)
        if len(body) > MAX_REMOTE_RESPONSE_BYTES:
            raise RemoteError("The remote server response is too large.")
    _check_deadline(deadline)

    if not body:
        raise RemoteError("The remote server returned an empty response.")

    try:
        return json.loads(body.decode(response.encoding or "utf-8"))
    except (LookupError, UnicodeError, ValueError, RecursionError) as error:
        raise RemoteError("The remote server returned invalid JSON.") from error


def _response_events(response, deadline):
    body_size = 0
    buffer = bytearray()

    for chunk in response.iter_content(chunk_size=8192):
        _check_deadline(deadline)
        if not chunk:
            continue
        body_size += len(chunk)
        if body_size > MAX_REMOTE_RESPONSE_BYTES:
            raise RemoteError("The remote server response is too large.")
        buffer.extend(chunk)

        while b"\n" in buffer:
            line, _, remainder = buffer.partition(b"\n")
            buffer = bytearray(remainder)
            if line:
                yield _decode_event(line)

    _check_deadline(deadline)
    if buffer:
        yield _decode_event(buffer)


def _decode_event(line):
    try:
        event = json.loads(line.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise RemoteError("The remote server returned an invalid event.") from error
    if not isinstance(event, dict):
        raise RemoteError("The remote server returned an invalid event.")
    return event


def _is_text(value, max_length, allow_empty=False):
    return (
        isinstance(value, str)
        and len(value) <= max_length
        and (allow_empty or bool(value.strip()))
    )


def _is_choice(value, choices, allow_none=False):
    return (allow_none and value is None) or (
        isinstance(value, str) and value in choices
    )


def _is_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    return isinstance(value, float) and math.isfinite(value) and value >= 0


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_timestamp(value):
    if not _is_text(value, 128):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _is_text_list(value, max_items, max_length=500):
    return (
        isinstance(value, list)
        and len(value) <= max_items
        and all(_is_text(item, max_length) for item in value)
    )


def _is_safe_detail(value, depth=0):
    if value is None or isinstance(value, (str, bool)):
        return not isinstance(value, str) or len(value) <= 64 * 1024
    if _is_number(value):
        return True
    if depth >= 8:
        return False
    if isinstance(value, list):
        return len(value) <= 256 and all(
            _is_safe_detail(item, depth + 1) for item in value
        )
    if isinstance(value, dict):
        return len(value) <= 256 and all(
            _is_text(key, 200)
            and _is_safe_detail(item, depth + 1)
            for key, item in value.items()
        )
    return False


def _is_layer(layer, allowed_keys):
    return (
        isinstance(layer, dict)
        and _is_choice(layer.get("key"), allowed_keys)
        and _is_choice(layer.get("status"), LAYER_STATUSES)
        and _is_text(layer.get("name"), 100)
        and _is_text(layer.get("summary"), 1200)
        and _is_number(layer.get("duration_ms"))
        and isinstance(layer.get("details"), dict)
        and _is_safe_detail(layer["details"])
    )


def _is_analysis(analysis):
    return (
        isinstance(analysis, dict)
        and set(analysis) == {
            "source",
            "model",
            "verdict",
            "headline",
            "text",
            "failure_stage",
            "confidence",
            "evidence",
            "causes",
            "actions",
        }
        and analysis.get("source") == "agent"
        and _is_text(analysis.get("model"), 200)
        and _is_choice(
            analysis.get("verdict"),
            {"reachable", "degraded", "unreachable"},
        )
        and _is_text(analysis.get("headline"), 160)
        and _is_text(analysis.get("text"), 1200)
        and _is_choice(
            analysis.get("failure_stage"),
            FAILURE_STAGES,
            allow_none=True,
        )
        and _is_choice(analysis.get("confidence"), {"low", "medium", "high"})
        and _is_text_list(analysis.get("evidence"), 8)
        and _is_text_list(analysis.get("causes"), 5, 500)
        and _is_text_list(analysis.get("actions"), 5, 500)
    )


def _is_tool_entry(entry):
    return (
        isinstance(entry, dict)
        and set(entry) == {
            "tool",
            "cached",
            "status",
            "summary",
            "duration_ms",
        }
        and _is_choice(entry.get("tool"), {*LAYER_KEYS, "traceroute"})
        and _is_choice(entry.get("status"), LAYER_STATUSES)
        and _is_text(entry.get("summary"), 1200)
        and isinstance(entry.get("cached"), bool)
        and _is_number(entry.get("duration_ms"))
    )


def _is_agent_trace(agent):
    if not isinstance(agent, dict):
        return False

    checks_used = agent.get("checks_used")
    tool_log = agent.get("tool_log")
    return (
        set(agent) == {
            "model",
            "api_mode",
            "checks_used",
            "tool_log",
        }
        and _is_text(agent.get("model"), 200)
        and _is_choice(agent.get("api_mode"), {"responses", "chat_completions"})
        and _is_count(checks_used)
        and isinstance(tool_log, list)
        and len(tool_log) <= 64
        and all(_is_tool_entry(entry) for entry in tool_log)
    )


def _validate_stream_event(event):
    event_type = event.get("type")
    if event_type == "run_started":
        return set(event) == {"type"}
    if event_type == "tool_started":
        return (
            set(event) == {"type", "tool"}
            and _is_choice(event.get("tool"), {*LAYER_KEYS, "traceroute"})
        )
    if event_type == "tool_completed":
        result = event.get("result")
        return (
            set(event) == {"type", "tool", "result"}
            and _is_choice(event.get("tool"), {*LAYER_KEYS, "traceroute"})
            and _is_layer(result, {event.get("tool")})
        )
    if event_type == "tool_failed":
        return (
            set(event) == {"type", "tool", "error"}
            and _is_choice(event.get("tool"), {*LAYER_KEYS, "traceroute"})
            and _is_text(event.get("error"), 1200)
        )
    if event_type == "error":
        return (
            set(event) == {"type", "error"}
            and _is_text(event.get("error"), 1200)
        )
    if event_type == "complete":
        return set(event) == {"type", "result"}
    return False


def _validate_report(report, expected_target):
    if not isinstance(report, dict):
        raise RemoteError("The remote server returned an invalid report.")
    target = report.get("target")
    if not isinstance(target, dict):
        raise RemoteError("The remote report is missing its target.")
    if any(
        target.get(key) != expected_target[key]
        for key in ("url", "hostname", "scheme", "port")
    ):
        raise RemoteError("The remote report target does not match the request.")
    if not _is_text(target.get("original"), 2048):
        raise RemoteError("The remote report contains an invalid target.")
    if report.get("mode") != "server":
        raise RemoteError("The remote report has an invalid execution mode.")
    if not _is_choice(report.get("status"), {"passed", "warning", "error"}):
        raise RemoteError("The remote report has an invalid overall status.")
    if (
        not _is_timestamp(report.get("created_at"))
        or not _is_number(report.get("duration_ms"))
    ):
        raise RemoteError("The remote report is missing run metadata.")
    if not _is_choice(
        report.get("first_problem"),
        {*FAILURE_STAGES, "traceroute"},
        allow_none=True,
    ):
        raise RemoteError("The remote report has an invalid failure stage.")
    if not isinstance(report.get("layers"), list) or not report["layers"]:
        raise RemoteError("The remote report does not contain diagnostic evidence.")
    if not _is_analysis(report.get("analysis")):
        raise RemoteError("The remote report is missing its agent analysis.")
    if not _is_agent_trace(report.get("agent")):
        raise RemoteError("The remote report is missing its agent trace.")
    analysis = report["analysis"]
    expected_status = {
        "reachable": "passed",
        "degraded": "warning",
        "unreachable": "error",
    }[analysis["verdict"]]
    failure_stage = analysis["failure_stage"]
    expected_problem = "traceroute" if failure_stage == "route" else failure_stage
    if (
        report["status"] != expected_status
        or report.get("first_problem") != expected_problem
        or report["agent"]["model"] != analysis["model"]
    ):
        raise RemoteError("The remote report contains inconsistent conclusions.")

    seen_keys = set()
    for layer in report["layers"]:
        if (
            not _is_layer(layer, LAYER_KEYS)
            or layer["key"] in seen_keys
        ):
            raise RemoteError("The remote report contains an invalid layer result.")
        seen_keys.add(layer["key"])

    traceroute = report.get("traceroute")
    if traceroute is not None and not _is_layer(traceroute, {"traceroute"}):
        raise RemoteError("The remote report contains an invalid traceroute result.")


def run_remote_diagnostics(target, timeout=120, event_handler=None):
    if not _is_number(timeout) or timeout <= 0:
        raise RemoteError("Server Test requires a positive timeout.")

    normalized_target = normalize_target(target)
    endpoint = _remote_endpoint()
    try:
        token = validate_servicepath_api_token(
            os.getenv("SERVICEPATH_API_TOKEN", "")
        )
    except SettingsError as error:
        raise RemoteError("SERVICEPATH_API_TOKEN is invalid.") from error
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = None
    # Requests timeouts are per socket operation; also check elapsed stream time.
    deadline = monotonic() + timeout
    try:
        response = requests.post(
            endpoint,
            json={"target": normalized_target["url"]},
            headers=headers,
            timeout=timeout,
            stream=True,
            allow_redirects=False,
        )
        if response.is_redirect or 300 <= response.status_code <= 399:
            raise RemoteError("Server Test does not follow service redirects.")
        if not response.ok:
            payload = _response_json(response, deadline)
            remote_message = (
                payload.get("error", "") if isinstance(payload, dict) else ""
            )
            remote_message = (
                remote_message.strip() if isinstance(remote_message, str) else ""
            )
            if remote_message:
                raise RemoteError(f"Server Test failed: {remote_message[:500]}")
            response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if content_type.partition(";")[0].strip().lower() != NDJSON_MIMETYPE:
            raise RemoteError("The remote server did not return an event stream.")

        started = False
        for event in _response_events(response, deadline):
            if not _validate_stream_event(event):
                raise RemoteError("The remote server returned an invalid event.")

            event_type = event["type"]
            if event_type == "run_started":
                if started:
                    raise RemoteError("The remote server repeated its start event.")
                started = True
            elif not started:
                raise RemoteError("The remote server omitted its start event.")

            if event_type == "error":
                raise RemoteError(f"Server Test failed: {event['error']}")
            if event_type == "complete":
                report = event["result"]
                _validate_report(report, normalized_target)
                return report
            if event_handler and event_type != "run_started":
                event_handler(event)

        raise RemoteError("The remote server ended before completing the report.")
    except RemoteError:
        raise
    except requests.RequestException as error:
        raise RemoteError(f"Server Test failed: {error}") from error
    finally:
        if response is not None:
            response.close()
