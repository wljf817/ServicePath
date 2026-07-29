from flask import Flask, render_template, request

from diagnostics.runner import run_diagnostics
from diagnostics.target import TargetError


app = Flask(__name__)


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

    return render_template(
        "index.html",
        domain=domain,
        mode=mode,
        report=report,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
