import hmac
import os
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from dotenv import load_dotenv, set_key

from app_settings import SettingsError, validate_settings
from database import (
    get_report,
    get_settings,
    init_db,
    list_reports,
    save_report,
    update_settings,
)
from diagnostics.analysis import analyze_report
from diagnostics.execution import ExecutionError, run_selected_diagnostics
from diagnostics.remote import RemoteError
from diagnostics.runner import run_diagnostics
from diagnostics.target import TargetError


load_dotenv()

app = Flask(__name__)
app.config["DATABASE"] = f"{app.instance_path}/servicepath.db"
app.config["ENV_FILE"] = str(Path(app.root_path) / ".env")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
init_db(app.config["DATABASE"])


def frontend_app():
    return app.send_static_file("frontend/index.html")


@app.template_filter("format_detail")
def format_detail(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "None"
    if isinstance(value, dict):
        return " | ".join(
            f"{key}: {format_detail(item)}" for key, item in value.items()
        )
    return str(value)


@app.template_filter("console_details")
def console_details(details):
    """Flatten nested diagnostic details into readable console lines."""
    lines = []

    def add_value(label, value):
        if isinstance(value, dict):
            if not value:
                lines.append({"label": label, "value": "None"})
            for child_label, child_value in value.items():
                add_value(f"{label} > {child_label}", child_value)
        else:
            lines.append({"label": label, "value": format_detail(value)})

    for label, value in details.items():
        add_value(label, value)

    return lines


@app.route("/")
def index():
    return frontend_app()


@app.route("/history")
def history():
    return frontend_app()


def settings_authorized(supplied_password):
    expected_password = os.getenv("SETTINGS_PASSWORD", "")
    is_loopback_address = request.remote_addr in {"127.0.0.1", "::1"}
    is_local_host = request.host.startswith(("127.0.0.1", "localhost", "[::1]"))
    is_local_request = is_loopback_address and is_local_host

    if expected_password:
        return hmac.compare_digest(supplied_password, expected_password)
    return is_local_request


def app_settings_payload():
    return {
        "settings": get_settings(app.config["DATABASE"]),
        "password_required": bool(os.getenv("SETTINGS_PASSWORD")),
        "api_token_configured": bool(os.getenv("SERVICEPATH_API_TOKEN")),
        "ai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-5.6"),
    }


def update_environment_settings(data):
    values = {
        "SERVICEPATH_API_TOKEN": data.get("servicepath_api_token", ""),
        "OPENAI_API_KEY": data.get("openai_api_key", ""),
        "OPENAI_MODEL": data.get("openai_model", ""),
        "SETTINGS_PASSWORD": data.get("new_settings_password", ""),
    }
    env_path = Path(app.config["ENV_FILE"])

    for name, value in values.items():
        value = str(value).strip()
        if not value:
            continue
        env_path.touch(mode=0o600, exist_ok=True)
        env_path.chmod(0o600)
        set_key(str(env_path), name, value)
        os.environ[name] = value


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "GET":
        return frontend_app()

    current_settings = get_settings(app.config["DATABASE"])
    error = None

    if request.method == "POST":
        supplied_password = request.form.get("settings_password", "")

        if not settings_authorized(supplied_password):
            error = "A valid settings password is required."
        else:
            try:
                values = validate_settings(
                    request.form.get("instance_role", ""),
                    request.form.get("remote_service_url", ""),
                )
                update_settings(app.config["DATABASE"], values)
                return redirect(url_for("settings_page", saved="1"))
            except SettingsError as settings_error:
                error = str(settings_error)
                current_settings = {
                    "instance_role": request.form.get("instance_role", ""),
                    "remote_service_url": request.form.get("remote_service_url", ""),
                }

    return (
        render_template(
            "settings.html",
            settings=current_settings,
            error=error,
            saved=request.args.get("saved") == "1",
            password_required=bool(os.getenv("SETTINGS_PASSWORD")),
            api_token_configured=bool(os.getenv("SERVICEPATH_API_TOKEN")),
            ai_configured=bool(os.getenv("OPENAI_API_KEY")),
        ),
        403 if error == "A valid settings password is required." else 200,
    )


@app.route("/api/app-settings", methods=["GET", "POST"])
def api_app_settings():
    if request.method == "GET":
        return jsonify(app_settings_payload())

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "The request body must be a JSON object."}), 400

    if not settings_authorized(str(data.get("settings_password", ""))):
        return jsonify({"error": "A valid settings password is required."}), 403

    try:
        values = validate_settings(
            str(data.get("instance_role", "")),
            str(data.get("remote_service_url", "")),
        )
    except SettingsError as error:
        return jsonify({"error": str(error)}), 400

    update_environment_settings(data)
    update_settings(app.config["DATABASE"], values)
    return jsonify(app_settings_payload())


@app.route("/api/history")
def api_history():
    return jsonify({"reports": list_reports(app.config["DATABASE"])})


@app.route("/api/reports/<int:report_id>")
def api_report(report_id):
    report = get_report(app.config["DATABASE"], report_id)
    if not report:
        return jsonify({"error": "Report not found."}), 404
    return jsonify(report)


@app.route("/reports/<int:report_id>")
def view_report(report_id):
    report = get_report(app.config["DATABASE"], report_id)
    if not report:
        abort(404)
    return frontend_app()


def diagnosis_error(message, status_code, domain, mode):
    if request.headers.get("Accept") == "application/json":
        return jsonify({"error": message}), status_code

    return (
        render_template(
            "index.html",
            error=message,
            domain=domain,
            mode=mode,
            app_settings=get_settings(app.config["DATABASE"]),
        ),
        status_code,
    )


@app.route("/diagnose", methods=["POST"])
def diagnose():
    domain = request.form.get("domain", "").strip()
    mode = request.form.get("mode", "local")

    if mode not in {"local", "remote", "compare"}:
        return diagnosis_error("Invalid test mode.", 400, domain, mode)

    try:
        current_settings = get_settings(app.config["DATABASE"])
        report = run_selected_diagnostics(domain, mode, current_settings)
    except (ExecutionError, TargetError, RemoteError) as error:
        if isinstance(error, RemoteError):
            status_code = 503
        elif isinstance(error, ExecutionError):
            status_code = 409
        else:
            status_code = 400
        return diagnosis_error(str(error), status_code, domain, mode)

    report["analysis"] = analyze_report(report)
    report_id = save_report(app.config["DATABASE"], report)
    report_url = url_for("view_report", report_id=report_id)

    if request.headers.get("Accept") == "application/json":
        return jsonify({"report_url": report_url}), 201

    return redirect(report_url)


@app.route("/api/diagnose", methods=["POST"])
def api_diagnose():
    expected_token = os.getenv("SERVICEPATH_API_TOKEN", "").strip()

    if expected_token:
        supplied_token = request.headers.get("Authorization", "").removeprefix(
            "Bearer "
        )
        if not hmac.compare_digest(supplied_token, expected_token):
            return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "The request body must be a JSON object."}), 400

    try:
        report = run_diagnostics(data.get("target", ""), mode="remote")
    except TargetError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
