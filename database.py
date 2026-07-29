import json
import sqlite3
from pathlib import Path


def connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    with connect(database_path) as connection:
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


def save_report(database_path, report):
    report_json = json.dumps(report)

    with connect(database_path) as connection:
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
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, report_json FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()

    if not row:
        return None

    report = json.loads(row["report_json"])
    report["id"] = row["id"]
    return report


def list_reports(database_path, limit=50):
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, target, mode, status, first_problem, created_at
            FROM reports
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
