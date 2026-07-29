import json
import os


def collect_issues(report):
    """Return every warning and error without trying to explain it."""
    if report.get("mode") == "compare":
        reports = [
            ("Local Test", report["local_report"]),
            ("Remote Test", report["remote_report"]),
        ]
    else:
        reports = [(None, report)]

    issues = []
    for location, test_report in reports:
        for layer in test_report.get("layers", []):
            if layer["status"] not in {"warning", "error"}:
                continue
            issues.append(
                {
                    "location": location,
                    "layer": layer["name"],
                    "status": layer["status"],
                    "summary": layer["summary"],
                }
            )
    return issues


def request_openai_analysis(report):
    from openai import OpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-5.6")
    prompt = (
        "You are a website reliability assistant. Analyze the JSON diagnostic report below. "
        "Use only the supplied evidence. State the most likely fault layer and uncertainty. "
        "Then give short, prioritized actions for a normal visitor and for a website owner. "
        "Do not claim that a guess is proven. Keep the answer under 250 words.\n\n"
        + json.dumps(report, indent=2)
    )
    client = OpenAI()
    response = client.responses.create(model=model, input=prompt)

    return {
        "source": "openai",
        "model": model,
        "text": response.output_text,
    }


def analyze_report(report):
    issues = collect_issues(report)

    if not os.getenv("OPENAI_API_KEY"):
        return {
            "source": "not_configured",
            "message": "AI analysis is not configured.",
            "issues": issues,
        }

    try:
        return request_openai_analysis(report)
    except Exception:
        return {
            "source": "unavailable",
            "message": "AI analysis could not be generated.",
            "issues": issues,
        }
