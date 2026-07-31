import hmac

from flask import Blueprint, Response, current_app, jsonify, request

from diagnostics.agent import run_agent_diagnostics
from diagnostics.remote import run_remote_diagnostics
from servicepath.model_config import (
    public_presets,
    public_servers,
    resolve_provider,
    resolve_server,
)
from servicepath.settings import SettingsError
from servicepath.streaming import NDJSON_MIMETYPE, stream_operation


bp = Blueprint("main", __name__)


def _server_config():
    return current_app.config["SERVER_CONFIG"]


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


def _stream_response(operation):
    return Response(
        stream_operation(operation),
        content_type=NDJSON_MIMETYPE,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


def _server_authorized():
    expected = _server_config()["server_token"]
    scheme, separator, supplied = request.headers.get("Authorization", "").partition(" ")
    return bool(
        expected
        and separator == " "
        and scheme.casefold() == "bearer"
        and hmac.compare_digest(supplied.encode(), expected.encode())
    )


@bp.get("/")
@bp.get("/history")
@bp.get("/settings")
@bp.get("/reports/<int:report_id>")
def frontend_app(report_id=None):
    return current_app.send_static_file("frontend/index.html")


@bp.get("/api/app-settings")
def api_app_settings():
    config = _server_config()
    return jsonify({
        "presets": public_presets(config),
        "server_presets": public_servers(config),
    })


@bp.post("/diagnose")
def diagnose():
    data, error_response = _json_object()
    if error_response:
        return error_response

    target = str(data.get("domain", "")).strip()
    location = str(data.get("location", "local")).strip()
    if location not in {"local", "custom", "preset"}:
        return jsonify({"error": "Invalid run location."}), 400

    try:
        provider = resolve_provider(_server_config(), data.get("provider"))
        server = (
            resolve_server(_server_config(), data.get("server_id"))
            if location == "preset"
            else data.get("custom_server")
        )
    except SettingsError as error:
        return jsonify({"error": str(error)}), 400

    def run(emit):
        if location == "local":
            return run_agent_diagnostics(target, provider, event_handler=emit)
        return run_remote_diagnostics(
            target,
            server,
            data.get("provider"),
            event_handler=emit,
        )

    return _stream_response(run)


@bp.post("/api/diagnose")
def api_diagnose():
    if not _server_authorized():
        return jsonify({"error": "A valid Custom Server token is required."}), 401

    data, error_response = _json_object()
    if error_response:
        return error_response
    try:
        provider = resolve_provider(_server_config(), data.get("provider"))
    except SettingsError as error:
        return jsonify({"error": str(error)}), 400

    target = str(data.get("target", "")).strip()
    return _stream_response(
        lambda emit: run_agent_diagnostics(
            target,
            provider,
            event_handler=emit,
        )
    )
