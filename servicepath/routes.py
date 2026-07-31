import hmac
import os
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, jsonify, request, url_for

from diagnostics.agent import (
    AgentConfigurationError,
    AgentRunError,
    run_agent_diagnostics,
)
from diagnostics.execution import ExecutionError, run_selected_diagnostics
from diagnostics.remote import RemoteError
from diagnostics.target import TargetError
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
    return os.getenv(name, "").strip() or default


def _validated_environment_value(name, default, validator):
    value = _environment_value(name, default)
    try:
        return validator(value)
    except SettingsError:
        # Keep invalid values visible so the user can replace them.
        return value


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
        "openai_base_url": _validated_environment_value(
            "OPENAI_BASE_URL",
            "",
            validate_openai_base_url,
        ),
        "openai_api_mode": _validated_environment_value(
            "OPENAI_API_MODE",
            "auto",
            validate_openai_api_mode,
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


def _diagnostic_error(error):
    if isinstance(error, (RemoteError, AgentConfigurationError, AgentRunError)):
        status_code = 503
    elif isinstance(error, ExecutionError):
        status_code = 409
    else:
        status_code = 400
    return jsonify({"error": str(error)}), status_code


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
        values = validate_settings(
            str(data.get("instance_role", "")),
            str(data.get("remote_service_url", "")),
        )
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

    target = str(data.get("target", data.get("domain", ""))).strip()
    mode = str(data.get("mode", "local"))
    if mode not in {"local", "remote", "compare"}:
        return jsonify({"error": "Invalid test mode."}), 400

    try:
        report = run_selected_diagnostics(
            target,
            mode,
            get_settings(_database_path()),
        )
    except (
        AgentConfigurationError,
        AgentRunError,
        ExecutionError,
        TargetError,
        RemoteError,
    ) as error:
        return _diagnostic_error(error)

    report_id = save_report(_database_path(), report)
    report_url = url_for("main.view_report", report_id=report_id)
    return jsonify({"report_url": report_url}), 201


@bp.post("/api/diagnose")
def api_diagnose():
    expected_token = os.getenv("SERVICEPATH_API_TOKEN", "").strip()
    if expected_token and not _valid_bearer_token(expected_token):
        return jsonify({"error": "Unauthorized"}), 401

    data, error_response = _json_object()
    if error_response:
        return error_response

    try:
        report = run_agent_diagnostics(data.get("target", ""), mode="remote")
    except TargetError as error:
        return jsonify({"error": str(error)}), 400
    except (AgentConfigurationError, AgentRunError) as error:
        return jsonify({"error": str(error)}), 503

    return jsonify(report)
