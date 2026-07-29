import platform
import shlex
import shutil
import subprocess
from time import perf_counter

from diagnostics.result import make_result


MAX_OUTPUT_LENGTH = 16 * 1024


def _command_for(destination, max_hops):
    system = platform.system().lower()

    if system == "windows":
        executable = shutil.which("tracert")
        if not executable:
            return None
        version_flag = ["-6"] if ":" in destination else []
        return [
            executable,
            *version_flag,
            "-d",
            "-h",
            str(max_hops),
            "-w",
            "1000",
            destination,
        ]

    if ":" in destination:
        executable = shutil.which("traceroute6")
        if executable:
            return [
                executable,
                "-n",
                "-m",
                str(max_hops),
                "-w",
                "1",
                "-q",
                "1",
                destination,
            ]

    executable = shutil.which("traceroute")
    if not executable:
        return None
    version_flag = ["-6"] if ":" in destination else []
    return [
        executable,
        *version_flag,
        "-n",
        "-m",
        str(max_hops),
        "-w",
        "1",
        "-q",
        "1",
        destination,
    ]


def _text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def skipped_traceroute(reason, destination=None):
    details = {}
    if destination:
        details["Destination address"] = destination
    return make_result(
        "traceroute",
        "Traceroute",
        "skipped",
        reason,
        details=details,
    )


def check_traceroute(addresses, max_hops=8, timeout=12):
    """Run a short traceroute without invoking a command shell."""
    if not addresses:
        return skipped_traceroute("Skipped because no destination IP is available.")

    destination = next(
        (address for address in addresses if ":" not in address),
        addresses[0],
    )
    command = _command_for(destination, max_hops)

    if not command:
        return skipped_traceroute(
            "Traceroute is not installed on this system.",
            destination,
        )

    started = perf_counter()

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
        stdout = completed.stdout.strip()[:MAX_OUTPUT_LENGTH]
        stderr = completed.stderr.strip()[:MAX_OUTPUT_LENGTH]
        raw_output = stdout or stderr or "No output returned"

        if completed.returncode != 0:
            status = "warning"
            summary = f"Traceroute exited with code {completed.returncode}."
        elif "*" in stdout:
            status = "warning"
            summary = "Traceroute completed with one or more unanswered hops."
        else:
            status = "passed"
            summary = "Traceroute command completed."

        duration = round((perf_counter() - started) * 1000)
        return make_result(
            "traceroute",
            "Traceroute",
            status,
            summary,
            duration,
            {
                "Command": shlex.join(command),
                "Destination address": destination,
                "Maximum hops": max_hops,
                "Return code": completed.returncode,
                "Raw output": raw_output,
                "Standard error": stderr or "None",
            },
        )
    except subprocess.TimeoutExpired as error:
        duration = round((perf_counter() - started) * 1000)
        partial_output = (_text(error.stdout) or _text(error.stderr)).strip()
        return make_result(
            "traceroute",
            "Traceroute",
            "warning",
            f"Traceroute stopped after the {timeout}-second limit.",
            duration,
            {
                "Command": shlex.join(command),
                "Destination address": destination,
                "Maximum hops": max_hops,
                "Raw output": partial_output[:MAX_OUTPUT_LENGTH] or "No partial output",
            },
        )
    except OSError as error:
        duration = round((perf_counter() - started) * 1000)
        return make_result(
            "traceroute",
            "Traceroute",
            "warning",
            "Traceroute could not be started.",
            duration,
            {
                "Command": shlex.join(command),
                "Destination address": destination,
                "Error": str(error),
            },
        )
