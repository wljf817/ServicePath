import hmac
import os
from urllib.parse import urlsplit

from flask import Blueprint, Response, abort, current_app, jsonify, request

from diagnostics.agent import run_agent_diagnostics
from diagnostics.execution import run_selected_diagnostics
from servicepath.database import (
    ReportDataError,
    get_report,
    get_settings,
    list_reports,
    save_report,
    update_settings,
)
from servicepath.settings import (
    SettingsError,
    update_environment_settings,
    validate_openai_api_mode,
    validate_openai_base_url,
    validate_servicepath_api_token,
    validate_settings,
)
from servicepath.streaming import NDJSON_MIMETYPE, stream_operation


bp = Blueprint("main", __name__)
LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1"})
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _database_path():
    return current_app.config["DATABASE"]


def _parse_authority(value):
    try:
        parsed = urlsplit(f"//{value}")
        parsed.port
    except ValueError:
        return None
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return None
    return parsed


def _constant_time_equal(supplied, expected):
    """Compare user-provided secrets without leaking timing information."""
    return hmac.compare_digest(supplied.encode(), expected.encode())


def _has_forwarding_headers():
    for name in request.headers.keys():
        normalized = name.casefold()
        if (
            normalized == "forwarded"
            or normalized == "x-real-ip"
            or normalized.startswith("x-forwarded-")
        ):
            return True
    return False


def _local_settings_request():
    if request.remote_addr not in LOOPBACK_ADDRESSES:
        return False
    host = _parse_authority(request.host)
    if host is None or host.hostname not in LOCAL_HOSTS:
        return False
    if _has_forwarding_headers():
        return False

    origin = request.headers.get("Origin")
    if origin is None:
        return True

    try:
        parsed = urlsplit(origin)
        parsed.port
    except ValueError:
        return False

    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in LOCAL_HOSTS
        and not parsed.username
        and not parsed.password
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
    )


def _settings_authorized(supplied_password):
    expected_password = os.getenv("SETTINGS_PASSWORD", "").strip()
    if expected_password:
        return _constant_time_equal(supplied_password, expected_password)
    return _local_settings_request()


def _environment_value(name, default=""):
    value = os.getenv(name)
    return default if value is None else value.strip()


def _app_settings_payload():
    agent_configured = bool(_environment_value("OPENAI_API_KEY"))
    return {
        "settings": get_settings(_database_path()),
        "password_required": bool(_environment_value("SETTINGS_PASSWORD")),
        "api_token_configured": bool(
            _environment_value("SERVICEPATH_API_TOKEN")
        ),
        "agent_configured": agent_configured,
        "openai_model": _environment_value("OPENAI_MODEL", "gpt-5.6"),
        "openai_base_url": validate_openai_base_url(
            _environment_value("OPENAI_BASE_URL")
        ),
        "openai_api_mode": validate_openai_api_mode(
            _environment_value("OPENAI_API_MODE", "responses")
        ),
    }


def _json_object():
    if not request.is_json:
        return None, (
            jsonify({"error": "The request body must use application/json."}),
            415,
        )

    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data, None
    return None, (jsonify({"error": "The request body must be a JSON object."}), 400)


def _valid_bearer_token(expected_token):
    authorization = request.headers.get("Authorization", "")
    scheme, separator, supplied_token = authorization.partition(" ")
    if separator != " " or scheme.casefold() != "bearer":
        return False
    try:
        normalized_token = validate_servicepath_api_token(supplied_token)
    except SettingsError:
        return False
    return bool(
        supplied_token == normalized_token
        and normalized_token
        and _constant_time_equal(normalized_token, expected_token)
    )


def _stream_response(operation):
    return Response(
        stream_operation(operation),
        content_type=NDJSON_MIMETYPE,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@bp.get("/")
@bp.get("/history")
@bp.get("/settings")
def frontend_app():
    return current_app.send_static_file("frontend/index.html")


@bp.get("/healthz")
def health():
    """Confirm that the app and its persistent database are ready."""
    get_settings(_database_path())
    return jsonify({"status": "ok"})


@bp.route("/api/app-settings", methods=["GET", "POST"])
def api_app_settings():
    if request.method == "GET":
        return jsonify(_app_settings_payload())

    data, error_response = _json_object()
    if error_response:
        return error_response

    if not _settings_authorized(str(data.get("settings_password", ""))):
        return jsonify({"error": "A valid settings password is required."}), 403

    try:
        values = validate_settings(str(data.get("instance_role", "")))
        update_environment_settings(current_app.config["ENV_FILE"], data)
    except SettingsError as error:
        return jsonify({"error": str(error)}), 400

    update_settings(_database_path(), values)
    return jsonify(_app_settings_payload())


@bp.get("/api/history")
def api_history():
    reports = list_reports(
        _database_path(),
        limit=current_app.config["HISTORY_LIMIT"],
    )
    return jsonify({"reports": reports})


@bp.get("/api/reports/<int:report_id>")
def api_report(report_id):
    try:
        report = get_report(_database_path(), report_id)
    except ReportDataError:
        return jsonify({"error": "Report data is unavailable."}), 500
    if not report:
        return jsonify({"error": "Report not found."}), 404
    return jsonify(report)


@bp.get("/reports/<int:report_id>")
def view_report(report_id):
    try:
        report = get_report(_database_path(), report_id)
    except ReportDataError:
        abort(500)
    if not report:
        abort(404)
    return current_app.send_static_file("frontend/index.html")


@bp.post("/diagnose")
def diagnose():
    data, error_response = _json_object()
    if error_response:
        return error_response

    target = str(data.get("domain", "")).strip()
    mode = str(data.get("mode", "client"))
    if mode not in {"client", "server"}:
        return jsonify({"error": "Invalid test mode."}), 400

    database_path = _database_path()
    settings = get_settings(database_path)

    def run(emit):
        report = run_selected_diagnostics(
            target,
            mode,
            settings,
            event_handler=emit,
        )
        report_id = save_report(database_path, report)
        return {"report_url": f"/reports/{report_id}"}

    return _stream_response(run)


@bp.post("/api/diagnose")
def api_diagnose():
    expected_token = os.getenv("SERVICEPATH_API_TOKEN", "").strip()
    if expected_token and not _valid_bearer_token(expected_token):
        return jsonify({"error": "Unauthorized"}), 401

    data, error_response = _json_object()
    if error_response:
        return error_response

    target = data.get("target", "")

    def run(emit):
        return run_agent_diagnostics(
            target,
            mode="server",
            event_handler=emit,
        )

    return _stream_response(run)
