import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from servicepath import database


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _runtime_paths():
    """Return persistent paths for local or container deployments."""
    configured_directory = os.getenv("SERVICEPATH_DATA_DIR", "").strip()
    if configured_directory:
        data_directory = Path(configured_directory).expanduser().resolve()
        return data_directory, data_directory / ".env"

    return PROJECT_ROOT / "instance", PROJECT_ROOT / ".env"


def create_app(test_config=None):
    """Create and configure a ServicePath application."""
    data_directory, environment_file = _runtime_paths()
    app = Flask(
        __name__,
        instance_path=str(data_directory),
        static_folder=str(PROJECT_ROOT / "static"),
        static_url_path="/static",
    )
    app.config.from_mapping(
        DATABASE=str(data_directory / "servicepath.db"),
        ENV_FILE=str(environment_file),
        HISTORY_LIMIT=50,
        LOAD_DOTENV=True,
        MAX_CONTENT_LENGTH=16 * 1024,
    )

    if test_config is not None:
        app.config.update(test_config)

    if app.config["LOAD_DOTENV"]:
        load_dotenv(app.config["ENV_FILE"])

    database.init_app(app)

    from servicepath.routes import bp

    app.register_blueprint(bp)
    return app
