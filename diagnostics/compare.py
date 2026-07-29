from datetime import datetime, timezone


def _problem_layer(report):
    if report.get("status") == "passed":
        return None
    return report.get("first_problem") or "unknown"


def _layer_rows(local_report, remote_report):
    local_layers = {layer["key"]: layer for layer in local_report["layers"]}
    remote_layers = {layer["key"]: layer for layer in remote_report["layers"]}
    rows = []

    for key in ("client", "dns", "tcp", "tls", "http"):
        local_layer = local_layers[key]
        remote_layer = remote_layers[key]
        rows.append(
            {
                "key": key,
                "name": local_layer["name"],
                "local": local_layer,
                "remote": remote_layer,
                "matches": local_layer["status"] == remote_layer["status"],
            }
        )

    return rows


def compare_reports(local_report, remote_report):
    """Combine local and remote reports and explain their relationship."""
    local_problem = _problem_layer(local_report)
    remote_problem = _problem_layer(remote_report)

    if not local_problem and not remote_problem:
        classification = "no_issue"
        status = "passed"
        title = "No problem detected from either location"
        summary = "Both Local Test and Remote Test passed all five layers."
    elif local_problem and not remote_problem:
        classification = "local_only"
        status = "warning"
        title = "The problem is likely local to this device or network"
        summary = (
            f"Local Test first reported {local_problem.upper()}, while Remote Test passed."
        )
    elif not local_problem and remote_problem:
        classification = "remote_only"
        status = "warning"
        title = "The problem appears specific to the remote server path"
        summary = (
            f"Remote Test first reported {remote_problem.upper()}, while Local Test passed."
        )
    elif local_problem == remote_problem:
        classification = "shared_problem"
        status = "error" if "error" in {
            local_report["status"],
            remote_report["status"],
        } else "warning"
        title = "The problem affects both test locations"
        summary = f"Both tests first reported a problem in the {local_problem.upper()} layer."
    else:
        classification = "different_results"
        status = "warning"
        title = "Local and remote results differ"
        summary = (
            f"Local Test first reported {local_problem.upper()}, while Remote Test "
            f"first reported {remote_problem.upper()}."
        )

    first_problem = local_problem or remote_problem

    return {
        "target": local_report["target"],
        "mode": "compare",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": local_report["duration_ms"] + remote_report["duration_ms"],
        "status": status,
        "first_problem": first_problem,
        "comparison": {
            "classification": classification,
            "title": title,
            "summary": summary,
            "local_problem": local_problem,
            "remote_problem": remote_problem,
            "layers": _layer_rows(local_report, remote_report),
        },
        "local_report": local_report,
        "remote_report": remote_report,
    }
