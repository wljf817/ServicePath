from datetime import datetime, timezone

from diagnostics.result import skipped_result


def _problem_layer(report):
    if report.get("status") == "passed":
        return None
    return report.get("first_problem") or "unknown"


def _report_results(report):
    results = {
        layer["key"]: layer
        for layer in report.get("layers", [])
        if isinstance(layer, dict) and layer.get("key")
    }
    traceroute = report.get("traceroute")
    if isinstance(traceroute, dict):
        results["traceroute"] = traceroute
    return results


def _missing_result(key, name):
    return skipped_result(
        key,
        name,
        "The agent did not select this check at this location.",
    )


def _layer_rows(local_report, remote_report):
    local_layers = _report_results(local_report)
    remote_layers = _report_results(remote_report)
    rows = []

    preferred_order = ("client", "dns", "traceroute", "tcp", "tls", "http")
    extra_keys = sorted((set(local_layers) | set(remote_layers)) - set(preferred_order))

    for key in [*preferred_order, *extra_keys]:
        if key not in local_layers and key not in remote_layers:
            continue

        available_layer = local_layers.get(key) or remote_layers[key]
        name = available_layer.get("name", key.replace("_", " ").title())
        local_layer = local_layers.get(key) or _missing_result(key, name)
        remote_layer = remote_layers.get(key) or _missing_result(key, name)
        rows.append(
            {
                "key": key,
                "name": name,
                "local": local_layer,
                "remote": remote_layer,
                "matches": (
                    key in local_layers
                    and key in remote_layers
                    and local_layer["status"] == remote_layer["status"]
                ),
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
        summary = "Both adaptive investigations found the target reachable."
    elif local_problem and not remote_problem:
        classification = "local_only"
        status = "warning"
        title = "The problem is likely local to this device or network"
        summary = (
            f"Local Test first reported {local_problem.upper()}, while Remote "
            "Test passed."
        )
    elif not local_problem and remote_problem:
        classification = "remote_only"
        status = "warning"
        title = "The problem appears specific to the remote server path"
        summary = (
            f"Remote Test first reported {remote_problem.upper()}, while Local "
            "Test passed."
        )
    elif local_problem == remote_problem:
        classification = "shared_problem"
        status = "error" if "error" in {
            local_report["status"],
            remote_report["status"],
        } else "warning"
        title = "The problem affects both test locations"
        summary = (
            "Both tests first reported a problem in the "
            f"{local_problem.upper()} layer."
        )
    else:
        classification = "different_results"
        status = "warning"
        title = "Local and remote results differ"
        summary = (
            f"Local Test first reported {local_problem.upper()}, while Remote Test "
            f"first reported {remote_problem.upper()}."
        )

    first_problem = local_problem or remote_problem
    actions = []
    if classification == "local_only":
        actions = [
            "Compare direct and proxy access on the local device.",
            "Retry from another local network, such as a mobile hotspot.",
        ]
    elif classification == "remote_only":
        actions = [
            "Review the remote server's DNS, proxy, and outbound network policy.",
        ]
    elif classification == "shared_problem":
        actions = [
            "Review the matching local and remote evidence for the target service.",
        ]

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
        "analysis": {
            "source": "comparison",
            "verdict": classification,
            "headline": title,
            "text": summary,
            "failure_stage": first_problem,
            "confidence": "medium",
            "evidence": [summary],
            "causes": [],
            "actions": actions,
        },
        "local_report": local_report,
        "remote_report": remote_report,
    }
