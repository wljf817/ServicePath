import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from database import init_db
from diagnostics.result import make_result


def sample_report():
    return {
        "target": {"url": "https://example.com/"},
        "mode": "local",
        "created_at": "2026-07-29T12:00:00+00:00",
        "duration_ms": 120,
        "status": "passed",
        "first_problem": None,
        "layers": [
            make_result("dns", "DNS", "passed", "DNS passed", 10, {"A records": ["93.184.216.34"]})
        ],
    }


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        app.config["TESTING"] = True
        app.config["DATABASE"] = str(Path(self.temporary_directory.name) / "test.db")
        init_db(app.config["DATABASE"])
        self.client = app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_home_page_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Start diagnosis", response.data)

    @patch("app.run_diagnostics")
    @patch("app.analyze_report")
    def test_local_diagnosis_displays_report(self, analyze_report, run_diagnostics):
        run_diagnostics.return_value = sample_report()
        analyze_report.return_value = {
            "source": "rules",
            "title": "No failure was detected",
            "explanation": "All checks passed.",
            "causes": [],
            "actions": ["No action needed."],
        }

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DNS passed", response.data)
        self.assertIn(b"No failure was detected", response.data)
        run_diagnostics.assert_called_once_with("example.com", mode="local")

    @patch("app.run_diagnostics")
    @patch("app.analyze_report")
    def test_saved_report_appears_in_history(self, analyze_report, run_diagnostics):
        run_diagnostics.return_value = sample_report()
        analyze_report.return_value = {"source": "rules", "title": "Test", "actions": []}
        self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
        )

        response = self.client.get("/history")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"https://example.com/", response.data)

    def test_remote_mode_is_not_configured_yet(self):
        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "remote"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Remote Test is not configured", response.data)


if __name__ == "__main__":
    unittest.main()
