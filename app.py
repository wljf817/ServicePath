from flask import Flask, render_template, request


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/diagnose", methods=["POST"])
def diagnose():
    domain = request.form.get("domain", "").strip()
    mode = request.form.get("mode", "local")

    if not domain:
        return render_template(
            "index.html",
            error="Please enter a website or domain.",
            mode=mode,
        )

    return render_template(
        "index.html",
        domain=domain,
        mode=mode,
        submitted=True,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
