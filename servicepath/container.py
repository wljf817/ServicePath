import os
import sys
import tempfile
from pathlib import Path

from dotenv import set_key


CONFIGURATION_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_API_MODE",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "REMOTE_SERVICE_URL",
    "SERVICEPATH_API_TOKEN",
    "SETTINGS_PASSWORD",
)


def seed_configuration(environment_file, environment=None):
    """Seed a new persistent configuration from container variables."""
    environment_file = Path(environment_file)
    if environment_file.exists():
        return False

    values = os.environ if environment is None else environment
    environment_file.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    environment_file.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=environment_file.parent,
        prefix=".servicepath-env-",
    )
    os.close(descriptor)
    temporary_file = Path(temporary_name)

    try:
        for name in CONFIGURATION_NAMES:
            set_key(
                str(temporary_file),
                name,
                str(values.get(name, "")),
            )
        temporary_file.chmod(0o600)
        temporary_file.replace(environment_file)
    finally:
        temporary_file.unlink(missing_ok=True)

    return True


def main(arguments=None):
    """Prepare persistent settings, then replace this process with the app."""
    command = list(sys.argv[1:] if arguments is None else arguments)
    if not command:
        raise SystemExit("A container command is required.")

    data_directory = Path(
        os.getenv("SERVICEPATH_DATA_DIR", "/data").strip() or "/data"
    )
    seed_configuration(data_directory / ".env")

    # The persistent file is authoritative after the first container start.
    for name in CONFIGURATION_NAMES:
        os.environ.pop(name, None)

    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
