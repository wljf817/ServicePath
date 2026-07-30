from diagnostics.agent import run_agent_diagnostics
from diagnostics.compare import compare_reports
from diagnostics.remote import run_remote_diagnostics


class ExecutionError(RuntimeError):
    """Raised when a test mode cannot run from this instance role."""


def run_selected_diagnostics(target, mode, settings):
    role = settings["instance_role"]

    if role == "remote_server":
        if mode == "remote":
            return run_agent_diagnostics(target, mode="remote")

        raise ExecutionError(
            "Local Test and Compare Both require ServicePath to be running on the "
            "user's device. A deployed webpage cannot perform raw DNS, TCP, and TLS "
            "checks from the visitor's computer."
        )

    if mode == "local":
        return run_agent_diagnostics(target, mode="local")

    remote_url = settings.get("remote_service_url") or None
    remote_report = run_remote_diagnostics(target, service_url=remote_url)

    if mode == "remote":
        return remote_report

    local_report = run_agent_diagnostics(target, mode="local")
    return compare_reports(local_report, remote_report)
