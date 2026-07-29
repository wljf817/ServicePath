import tempfile
import unittest
from pathlib import Path

from database import (
    get_report,
    get_settings,
    init_db,
    list_reports,
    save_report,
    update_settings,
)


def sample_report():
    return {
        "target": {"url": "https://example.com/"},
        "mode": "local",
        "status": "passed",
        "first_problem": None,
        "created_at": "2026-07-29T12:00:00+00:00",
        "duration_ms": 100,
        "layers": [],
    }


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temporary_directory.name) / "test.db")
        init_db(self.database_path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_saves_and_loads_report(self):
        report_id = save_report(self.database_path, sample_report())
        report = get_report(self.database_path, report_id)

        self.assertEqual(report["id"], report_id)
        self.assertEqual(report["target"]["url"], "https://example.com/")

    def test_lists_newest_report_first(self):
        first_id = save_report(self.database_path, sample_report())
        second_id = save_report(self.database_path, sample_report())
        reports = list_reports(self.database_path)

        self.assertEqual([report["id"] for report in reports], [second_id, first_id])

    def test_uses_remote_server_as_default_role(self):
        settings = get_settings(self.database_path)

        self.assertEqual(settings["instance_role"], "remote_server")
        self.assertEqual(settings["remote_service_url"], "")

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
