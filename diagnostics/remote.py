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
LAYER_STATUSES = {"passed", "warning", "error", "skipped"}
LAYER_KEYS = {"client", "dns", "tcp", "tls", "http"}
FAILURE_STAGES = {"client", "dns", "route", "tcp", "tls", "http", "application"}


class RemoteError(RuntimeError):
    """Raised when the configured remote diagnostic service cannot be used."""


def _remote_endpoint(service_url=None):
    if service_url is None:
        service_url = os.getenv("REMOTE_SERVICE_URL", "")
    if not isinstance(service_url, str):
        raise RemoteError("REMOTE_SERVICE_URL is invalid.")
    service_url = service_url.strip()

    if not service_url:
        raise RemoteError("Remote Test requires REMOTE_SERVICE_URL in your .env file.")

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
        raise RemoteError("Remote Test exceeded its time limit.")


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
        and analysis.get("source") == "agent"
        and _is_text(analysis.get("model"), 200)
        and _is_choice(analysis.get("completion"), {"complete", "fallback"})
        and _is_choice(
            analysis.get("verdict"),
            {"reachable", "degraded", "unreachable", "inconclusive"},
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


def _is_tool_entry(entry, include_timing=False):
    if not (
        isinstance(entry, dict)
        and _is_choice(entry.get("tool"), {*LAYER_KEYS, "traceroute"})
        and _is_choice(entry.get("status"), LAYER_STATUSES)
        and _is_text(entry.get("summary"), 1200)
    ):
        return False
    if include_timing:
        return (
            isinstance(entry.get("cached"), bool)
            and _is_number(entry.get("duration_ms"))
            and (
                "denied" not in entry
                or isinstance(entry.get("denied"), bool)
            )
        )
    return True


def _is_agent_trace(agent):
    if not isinstance(agent, dict):
        return False

    checks_used = agent.get("checks_used")
    max_checks = agent.get("max_checks")
    requested_tools = agent.get("requested_tools")
    tool_log = agent.get("tool_log")
    token_usage = agent.get("token_usage")
    return (
        _is_text(agent.get("model"), 200)
        and _is_choice(agent.get("api_mode"), {"responses", "chat_completions"})
        and _is_choice(agent.get("completion"), {"complete", "fallback"})
        and _is_count(checks_used)
        and _is_count(max_checks)
        and checks_used <= max_checks
        and isinstance(requested_tools, list)
        and len(requested_tools) <= 64
        and all(_is_tool_entry(entry) for entry in requested_tools)
        and isinstance(tool_log, list)
        and len(tool_log) <= 64
        and all(_is_tool_entry(entry, include_timing=True) for entry in tool_log)
        and _is_count(agent.get("model_calls"))
        and isinstance(token_usage, dict)
        and all(
            _is_count(token_usage.get(key))
            for key in ("input", "output", "total")
        )
    )


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
    if report.get("mode") != "remote":
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
    if report.get("comparison") is not None:
        raise RemoteError("The remote report contains invalid comparison data.")

    analysis = report["analysis"]
    expected_status = {
        "reachable": "passed",
        "degraded": "warning",
        "unreachable": "error",
        "inconclusive": "warning",
    }[analysis["verdict"]]
    failure_stage = analysis["failure_stage"]
    expected_problem = "traceroute" if failure_stage == "route" else failure_stage
    if (
        report["status"] != expected_status
        or report.get("first_problem") != expected_problem
        or report["agent"]["model"] != analysis["model"]
        or report["agent"]["completion"] != analysis["completion"]
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


def run_remote_diagnostics(target, timeout=120, service_url=None):
    if not _is_number(timeout) or timeout <= 0:
        raise RemoteError("Remote Test requires a positive timeout.")

    normalized_target = normalize_target(target)
    endpoint = _remote_endpoint(service_url)
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
            raise RemoteError("Remote Test does not follow service redirects.")
        payload = _response_json(response, deadline)
        if not response.ok:
            remote_message = (
                payload.get("error", "") if isinstance(payload, dict) else ""
            )
            remote_message = (
                remote_message.strip() if isinstance(remote_message, str) else ""
            )
            if remote_message:
                raise RemoteError(f"Remote Test failed: {remote_message[:500]}")
            response.raise_for_status()
        report = payload
    except RemoteError:
        raise
    except requests.RequestException as error:
        raise RemoteError(f"Remote Test failed: {error}") from error
    finally:
        if response is not None:
            response.close()

    _validate_report(report, normalized_target)
    report["mode"] = "remote"
    return report
