import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from database import get_settings, init_db, update_settings
from diagnostics.result import make_result


def sample_report():
    layer_names = {
        "client": "Client Network",
        "dns": "DNS",
        "tcp": "TCP",
        "tls": "TLS",
        "http": "HTTP",
    }
    return {
        "target": {"url": "https://example.com/"},
        "mode": "local",
        "created_at": "2026-07-29T12:00:00+00:00",
        "duration_ms": 120,
        "status": "passed",
        "first_problem": None,
        "layers": [
            make_result(key, name, "passed", f"{name} passed", 10)
            for key, name in layer_names.items()
        ],
    }


def unconfigured_analysis():
    return {
        "source": "not_configured",
        "message": "AI analysis is not configured.",
        "issues": [],
    }


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        app.config["TESTING"] = True
        app.config["DATABASE"] = str(Path(self.temporary_directory.name) / "test.db")
        init_db(app.config["DATABASE"])
        update_settings(
            app.config["DATABASE"],
            {"instance_role": "local_device", "remote_service_url": ""},
        )
        self.client = app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_home_page_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Start diagnosis", response.data)

    def test_settings_page_loads_default_role(self):
        response = self.client.get("/settings")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Deployed Remote Server", response.data)

    def test_local_request_can_update_settings(self):
        response = self.client.post(
            "/settings",
            data={
                "instance_role": "local_device",
                "remote_service_url": "https://servicepath.example/",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Settings saved successfully", response.data)
        settings = get_settings(app.config["DATABASE"])
        self.assertEqual(settings["instance_role"], "local_device")

    @patch.dict(os.environ, {"SETTINGS_PASSWORD": "admin-secret"}, clear=True)
    def test_settings_reject_wrong_password(self):
        response = self.client.post(
            "/settings",
            data={
                "instance_role": "remote_server",
                "remote_service_url": "",
                "settings_password": "wrong",
            },
        )

        self.assertEqual(response.status_code, 403)

    @patch.dict(os.environ, {}, clear=True)
    def test_public_host_requires_settings_password(self):
        response = self.client.post(
            "/settings",
            data={
                "instance_role": "remote_server",
                "remote_service_url": "",
            },
            headers={"Host": "servicepath.example"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )

        self.assertEqual(response.status_code, 403)

    @patch("app.run_selected_diagnostics")
    @patch("app.analyze_report")
    def test_local_diagnosis_displays_report(self, analyze_report, run_selected):
        run_selected.return_value = sample_report()
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DNS passed", response.data)
        self.assertIn(b"AI analysis is not configured", response.data)
        run_selected.assert_called_once_with(
            "example.com",
            "local",
            {"instance_role": "local_device", "remote_service_url": ""},
        )

    @patch("app.run_selected_diagnostics")
    @patch("app.analyze_report")
    def test_saved_report_appears_in_history(self, analyze_report, run_selected):
        run_selected.return_value = sample_report()
        analyze_report.return_value = unconfigured_analysis()
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
    @patch("app.run_selected_diagnostics")
    def test_remote_diagnosis_displays_report(self, run_selected, analyze_report):
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_selected.return_value = remote_report
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "remote"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Remote Test", response.data)
        run_selected.assert_called_once_with(
            "example.com",
            "remote",
            {"instance_role": "local_device", "remote_service_url": ""},
        )

    @patch("app.analyze_report")
    @patch("app.run_selected_diagnostics")
    def test_compare_both_displays_side_by_side_report(
        self,
        run_selected,
        analyze_report,
    ):
        from diagnostics.compare import compare_reports

        local_report = sample_report()
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_selected.return_value = compare_reports(local_report, remote_report)
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "compare"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Layer comparison", response.data)
        self.assertIn(b"AI analysis is not configured", response.data)
        run_selected.assert_called_once_with(
            "example.com",
            "compare",
            {"instance_role": "local_device", "remote_service_url": ""},
        )

    @patch("app.run_selected_diagnostics")
    @patch("app.analyze_report")
    def test_remote_server_runs_remote_mode(self, analyze_report, run_selected):
        update_settings(
            app.config["DATABASE"],
            {"instance_role": "remote_server", "remote_service_url": ""},
        )
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_selected.return_value = remote_report
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "remote"},
        )

        self.assertEqual(response.status_code, 302)
        run_selected.assert_called_once_with(
            "example.com",
            "remote",
            {"instance_role": "remote_server", "remote_service_url": ""},
        )

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
