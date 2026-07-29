import hmac
import os

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from dotenv import load_dotenv

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
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
init_db(app.config["DATABASE"])


@app.template_filter("format_detail")
def format_detail(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "None"
    if isinstance(value, dict):
        return " | ".join(
            f"{key}: {format_detail(item)}" for key, item in value.items()
        )
    return str(value)


@app.route("/")
def index():
    current_settings = get_settings(app.config["DATABASE"])
    default_mode = (
        "remote" if current_settings["instance_role"] == "remote_server" else "local"
    )
    return render_template(
        "index.html",
        mode=default_mode,
        app_settings=current_settings,
    )


@app.route("/history")
def history():
    reports = list_reports(app.config["DATABASE"])
    return render_template("history.html", reports=reports)


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    current_settings = get_settings(app.config["DATABASE"])
    error = None

    if request.method == "POST":
        expected_password = os.getenv("SETTINGS_PASSWORD", "")
        supplied_password = request.form.get("settings_password", "")
        is_loopback_address = request.remote_addr in {"127.0.0.1", "::1"}
        is_local_host = request.host.startswith(("127.0.0.1", "localhost", "[::1]"))
        is_local_request = is_loopback_address and is_local_host

        if expected_password:
            authorized = hmac.compare_digest(supplied_password, expected_password)
        else:
            authorized = is_local_request

        if not authorized:
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


@app.route("/reports/<int:report_id>")
def view_report(report_id):
    report = get_report(app.config["DATABASE"], report_id)
    if not report:
        abort(404)
    template = "compare.html" if report["mode"] == "compare" else "index.html"
    return render_template(
        template,
        report=report,
        domain=report["target"]["url"],
        mode=report["mode"],
        app_settings=get_settings(app.config["DATABASE"]),
    )


@app.route("/diagnose", methods=["POST"])
def diagnose():
    domain = request.form.get("domain", "").strip()
    mode = request.form.get("mode", "local")

    if mode not in {"local", "remote", "compare"}:
        return render_template("index.html", error="Invalid test mode.", domain=domain), 400

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
        return (
            render_template(
                "index.html",
                error=str(error),
                domain=domain,
                mode=mode,
                app_settings=get_settings(app.config["DATABASE"]),
            ),
            status_code,
        )

    report["analysis"] = analyze_report(report)
    report_id = save_report(app.config["DATABASE"], report)
    return redirect(url_for("view_report", report_id=report_id))


@app.route("/api/diagnose", methods=["POST"])
def api_diagnose():
    expected_token = os.getenv("SERVICEPATH_API_TOKEN", "").strip()

    if expected_token:
        supplied_token = request.headers.get("Authorization", "").removeprefix("Bearer ")
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
