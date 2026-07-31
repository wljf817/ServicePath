import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULT_SETTINGS = {
    "instance_role": "remote_server",
    "remote_service_url": "",
}
SCHEMA_VERSION = 1
DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 100


class DatabaseVersionError(RuntimeError):
    """Raised when the database schema is newer than this application."""


class ReportDataError(RuntimeError):
    """Raised when a saved report cannot be decoded safely."""


def _prepare_database_path(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.parent.chmod(0o700)

    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags, 0o600)
    os.close(descriptor)
    path.chmod(0o600)
    return path


def connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def _connection(database_path):
    connection = connect(database_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(database_path):
    path = _prepare_database_path(database_path)

    with _connection(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise DatabaseVersionError(
                f"Database schema version {version} is not supported."
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                first_problem TEXT,
                created_at TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def init_app(app):
    """Create or upgrade the database during application startup."""
    init_db(app.config["DATABASE"])


def save_report(database_path, report):
    report_json = json.dumps(report)

    with _connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO reports (
                target, mode, status, first_problem, created_at, report_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report["target"]["url"],
                report["mode"],
                report["status"],
                report["first_problem"],
                report["created_at"],
                report_json,
            ),
        )
        return cursor.lastrowid


def get_report(database_path, report_id):
    with _connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, report_json FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()

    if not row:
        return None

    try:
        report = json.loads(row["report_json"])
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as error:
        raise ReportDataError("The saved report is corrupted.") from error

    if not isinstance(report, dict):
        raise ReportDataError("The saved report is corrupted.")

    report["id"] = row["id"]
    return report


def _bounded_history_limit(limit):
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("History limit must be an integer.")
    return max(1, min(limit, MAX_HISTORY_LIMIT))


def list_reports(database_path, limit=DEFAULT_HISTORY_LIMIT):
    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, target, mode, status, first_problem, created_at
            FROM reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (_bounded_history_limit(limit),),
        ).fetchall()

    return [dict(row) for row in rows]


def get_settings(database_path):
    settings = DEFAULT_SETTINGS.copy()

    with _connection(database_path) as connection:
        rows = connection.execute("SELECT key, value FROM settings").fetchall()

    for row in rows:
        if row["key"] in settings:
            settings[row["key"]] = row["value"]

    return settings


def update_settings(database_path, values):
    unknown_keys = set(values) - set(DEFAULT_SETTINGS)
    if unknown_keys:
        raise ValueError("Unknown setting: " + ", ".join(sorted(unknown_keys)))

    with _connection(database_path) as connection:
        for key, value in values.items():
            connection.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )
