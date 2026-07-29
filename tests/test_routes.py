import tempfile
import unittest
import os
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
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post(
                "/diagnose",
                data={"domain": "example.com", "mode": "remote"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"REMOTE_SERVICE_URL", response.data)

    @patch("app.analyze_report")
    @patch("app.run_remote_diagnostics")
    def test_remote_diagnosis_displays_report(self, run_remote, analyze_report):
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_remote.return_value = remote_report
        analyze_report.return_value = {
            "source": "rules",
            "title": "No failure was detected",
            "explanation": "All checks passed.",
            "causes": [],
            "actions": [],
        }

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "remote"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Remote Test", response.data)
        run_remote.assert_called_once_with("example.com")

    @patch("app.run_diagnostics")
    def test_api_returns_remote_report(self, run_diagnostics):
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_diagnostics.return_value = remote_report

        response = self.client.post("/api/diagnose", json={"target": "example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "remote")
        run_diagnostics.assert_called_once_with("example.com", mode="remote")

    @patch.dict(os.environ, {"SERVICEPATH_API_TOKEN": "secret-token"}, clear=True)
    def test_api_rejects_wrong_token(self):
        response = self.client.post("/api/diagnose", json={"target": "example.com"})

        self.assertEqual(response.status_code, 401)

    def test_api_rejects_non_object_json(self):
        response = self.client.post("/api/diagnose", json=["example.com"])

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
