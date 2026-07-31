import os

from servicepath import create_app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("SERVICEPATH_DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # The app factory already loads the configured environment file.
    app.run(
        debug=debug,
        host=os.getenv("SERVICEPATH_HOST", "127.0.0.1"),
        port=5050,
        load_dotenv=False,
    )
