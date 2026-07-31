import json
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from servicepath.database import (
    MAX_HISTORY_LIMIT,
    SCHEMA_VERSION,
    DatabaseVersionError,
    ReportDataError,
    _connection,
    get_report,
    get_settings,
    init_db,
    list_reports,
    save_report,
    update_settings,
)


def sample_report(number=0):
    """Build a stored report with a unique timestamp."""
    return {
        "target": {"url": f"https://example{number}.com/"},
        "mode": "local",
        "status": "passed",
        "first_problem": None,
        "created_at": f"2026-07-29T12:00:{number % 60:02d}+00:00",
        "duration_ms": 100,
        "layers": [],
    }


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temporary_directory.name) / "data" / "test.db"
        )
        init_db(self.database_path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def execute(self, statement, parameters=()):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(statement, parameters)
            connection.commit()
        finally:
            connection.close()

    def test_initializes_private_database_with_schema_version(self):
        self.assertEqual(
            stat.S_IMODE(self.database_path.parent.stat().st_mode),
            0o700,
        )
        self.assertEqual(stat.S_IMODE(self.database_path.stat().st_mode), 0o600)

        connection = sqlite3.connect(self.database_path)
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(version, SCHEMA_VERSION)

    def test_rejects_newer_database_schema(self):
        self.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")

        with self.assertRaises(DatabaseVersionError):
            init_db(self.database_path)

    def test_connection_context_commits_and_closes(self):
        connection = MagicMock()

        with patch("servicepath.database.connect", return_value=connection):
            with _connection(self.database_path):
                pass

        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once_with()

    def test_connection_context_rolls_back_and_closes_on_error(self):
        connection = MagicMock()

        with self.assertRaises(RuntimeError):
            with patch("servicepath.database.connect", return_value=connection):
                with _connection(self.database_path):
                    raise RuntimeError("failed")

        connection.rollback.assert_called_once_with()
        connection.commit.assert_not_called()
        connection.close.assert_called_once_with()

    def test_saves_and_loads_report(self):
        report_id = save_report(self.database_path, sample_report())
        report = get_report(self.database_path, report_id)

        self.assertEqual(report["id"], report_id)
        self.assertEqual(report["target"]["url"], "https://example0.com/")

    def test_missing_report_returns_none(self):
        self.assertIsNone(get_report(self.database_path, 999))

    def test_rejects_corrupt_report_json(self):
        report = sample_report()
        report_id = save_report(self.database_path, report)
        invalid_values = ("{", json.dumps(["not", "an", "object"]), b"\xff")

        for value in invalid_values:
            with self.subTest(value=value):
                self.execute(
                    "UPDATE reports SET report_json = ? WHERE id = ?",
                    (value, report_id),
                )
                with self.assertRaises(ReportDataError):
                    get_report(self.database_path, report_id)

    def test_lists_newest_reports_first(self):
        first_id = save_report(self.database_path, sample_report(1))
        second_id = save_report(self.database_path, sample_report(2))

        reports = list_reports(self.database_path)

        self.assertEqual([row["id"] for row in reports], [second_id, first_id])

    def test_history_limit_is_bounded(self):
        for number in range(MAX_HISTORY_LIMIT + 5):
            save_report(self.database_path, sample_report(number))

        self.assertEqual(
            len(list_reports(self.database_path, MAX_HISTORY_LIMIT + 500)),
            MAX_HISTORY_LIMIT,
        )
        self.assertEqual(len(list_reports(self.database_path, 0)), 1)

    def test_history_limit_requires_an_integer(self):
        for value in (True, None, "10", 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                list_reports(self.database_path, value)

    def test_uses_remote_server_as_default_role(self):
        settings = get_settings(self.database_path)

        self.assertEqual(
            settings,
            {"instance_role": "remote_server", "remote_service_url": ""},
        )

    def test_updates_settings(self):
        update_settings(
            self.database_path,
            {
                "instance_role": "local_device",
                "remote_service_url": "https://servicepath.example",
            },
        )

        settings = get_settings(self.database_path)

        self.assertEqual(settings["instance_role"], "local_device")
        self.assertEqual(
            settings["remote_service_url"],
            "https://servicepath.example",
        )

    def test_rejects_unknown_setting(self):
        with self.assertRaises(ValueError):
            update_settings(self.database_path, {"api_key": "secret"})


if __name__ == "__main__":
    unittest.main()
