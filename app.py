from flask import Flask, abort, redirect, render_template, request, url_for

from database import get_report, init_db, list_reports, save_report
from diagnostics.runner import run_diagnostics
from diagnostics.target import TargetError


app = Flask(__name__)
app.config["DATABASE"] = f"{app.instance_path}/servicepath.db"
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

    if mode == "remote":
        return (
            render_template(
                "index.html",
                error="Remote Test is not configured yet. Please use Local Test.",
                domain=domain,
                mode=mode,
            ),
            503,
        )

    try:
        report = run_diagnostics(domain, mode=mode)
    except TargetError as error:
        return (
            render_template(
                "index.html",
                error=str(error),
                domain=domain,
                mode=mode,
            ),
            400,
        )

    report_id = save_report(app.config["DATABASE"], report)
    return redirect(url_for("view_report", report_id=report_id))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
