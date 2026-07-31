from diagnostics.agent import run_agent_diagnostics
from diagnostics.remote import run_remote_diagnostics


class ExecutionError(RuntimeError):
    """Raised when a test mode cannot run from this instance role."""


def run_selected_diagnostics(target, mode, settings, event_handler=None):
    if not isinstance(mode, str) or mode not in {"client", "server"}:
        raise ExecutionError("Please select Client Test or Server Test.")

    role = settings["instance_role"]

    if role not in {"server", "client"}:
        raise ExecutionError("ServicePath has an invalid instance role.")

    if role == "server":
        if mode == "server":
            return run_agent_diagnostics(
                target,
                mode="server",
                event_handler=event_handler,
            )

        raise ExecutionError(
            "Client Test requires ServicePath to run on the user's device. A "
            "deployed webpage cannot inspect the visitor's network."
        )

    if mode == "client":
        return run_agent_diagnostics(
            target,
            mode="client",
            event_handler=event_handler,
        )

    return run_remote_diagnostics(target, event_handler=event_handler)
