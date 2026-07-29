import hmac
import os

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from dotenv import load_dotenv

from database import get_report, init_db, list_reports, save_report
from diagnostics.analysis import analyze_report
from diagnostics.remote import RemoteError, run_remote_diagnostics
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
    return render_template("index.html")


@app.route("/history")
def history():
    reports = list_reports(app.config["DATABASE"])
    return render_template("history.html", reports=reports)


@app.route("/reports/<int:report_id>")
def view_report(report_id):
    report = get_report(app.config["DATABASE"], report_id)
    if not report:
        abort(404)
    return render_template(
        "index.html",
        report=report,
        domain=report["target"]["url"],
        mode=report["mode"],
    )


@app.route("/diagnose", methods=["POST"])
def diagnose():
    domain = request.form.get("domain", "").strip()
    mode = request.form.get("mode", "local")

    if mode not in {"local", "remote"}:
        return render_template("index.html", error="Invalid test mode.", domain=domain), 400

    try:
        if mode == "remote":
            report = run_remote_diagnostics(domain)
        else:
            report = run_diagnostics(domain, mode="local")
    except (TargetError, RemoteError) as error:
        status_code = 503 if isinstance(error, RemoteError) else 400
        return (
            render_template(
                "index.html",
                error=str(error),
                domain=domain,
                mode=mode,
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
