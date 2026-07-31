import os
from pathlib import Path

from flask import Flask

from servicepath.model_config import load_server_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    """Create and configure a stateless ServicePath application."""
    app = Flask(
        __name__,
        static_folder=str(PROJECT_ROOT / "static"),
        static_url_path="/static",
    )
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=16 * 1024,
        SERVER_CONFIG_FILE=os.getenv(
            "SERVICEPATH_CONFIG",
            str(PROJECT_ROOT / "servicepath.config.json"),
        ),
    )
    if test_config is not None:
        app.config.update(test_config)
    if "SERVER_CONFIG" not in app.config:
        app.config["SERVER_CONFIG"] = load_server_config(
            app.config["SERVER_CONFIG_FILE"]
        )

    from servicepath.routes import bp

    app.register_blueprint(bp)
    return app
