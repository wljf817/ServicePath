import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from database import get_settings, init_db, update_settings
from diagnostics.agent import AgentConfigurationError
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
        self.original_env_file = app.config["ENV_FILE"]
        app.config["TESTING"] = True
        app.config["DATABASE"] = str(Path(self.temporary_directory.name) / "test.db")
        app.config["ENV_FILE"] = str(Path(self.temporary_directory.name) / ".env")
        init_db(app.config["DATABASE"])
        update_settings(
            app.config["DATABASE"],
            {"instance_role": "local_device", "remote_service_url": ""},
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config["ENV_FILE"] = self.original_env_file
        self.temporary_directory.cleanup()

    def assert_frontend_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<div id="root"></div>', response.data)
        self.assertIn(b"/static/frontend/assets/", response.data)
        response.close()

    def test_home_page_loads(self):
        response = self.client.get("/")

        self.assert_frontend_response(response)

    def test_settings_page_loads_frontend(self):
        response = self.client.get("/settings")

        self.assert_frontend_response(response)

    def test_frontend_settings_api_returns_configuration(self):
        response = self.client.get("/api/app-settings")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["settings"]["instance_role"], "local_device")
        self.assertIn("agent_configured", data)
        self.assertIn("ai_configured", data)
        self.assertIn("openai_base_url", data)
        self.assertIn("openai_api_mode", data)

    def test_local_request_can_update_settings(self):
        response = self.client.post(
            "/settings",
            data={
                "instance_role": "local_device",
                "remote_service_url": "https://servicepath.example/",
            },
        )

        self.assertEqual(response.status_code, 302)
        settings = get_settings(app.config["DATABASE"])
        self.assertEqual(settings["instance_role"], "local_device")

    def test_frontend_settings_api_updates_settings(self):
        response = self.client.post(
            "/api/app-settings",
            json={
                "instance_role": "local_device",
                "remote_service_url": "https://servicepath.example/",
                "settings_password": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        settings = response.get_json()["settings"]
        self.assertEqual(settings["remote_service_url"], "https://servicepath.example")

    @patch.dict(os.environ, {}, clear=True)
    def test_frontend_settings_api_saves_secrets_to_env_file(self):
        response = self.client.post(
            "/api/app-settings",
            json={
                "instance_role": "local_device",
                "remote_service_url": "",
                "settings_password": "",
                "servicepath_api_token": "remote-token",
                "openai_api_key": "openai-key",
                "openai_base_url": "https://models.example/v1/",
                "openai_api_mode": "chat_completions",
                "openai_model": "gpt-test",
                "new_settings_password": "new-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["api_token_configured"])
        self.assertTrue(data["agent_configured"])
        self.assertTrue(data["ai_configured"])
        self.assertTrue(data["password_required"])
        self.assertEqual(data["openai_model"], "gpt-test")
        self.assertEqual(data["openai_base_url"], "https://models.example/v1")
        self.assertEqual(data["openai_api_mode"], "chat_completions")
        self.assertNotIn("openai_api_key", data)

        env_text = Path(app.config["ENV_FILE"]).read_text()
        self.assertIn("SERVICEPATH_API_TOKEN='remote-token'", env_text)
        self.assertIn("OPENAI_API_KEY='openai-key'", env_text)
        self.assertIn("OPENAI_BASE_URL='https://models.example/v1'", env_text)
        self.assertIn("OPENAI_API_MODE='chat_completions'", env_text)
        self.assertIn("SETTINGS_PASSWORD='new-password'", env_text)

    @patch.dict(os.environ, {}, clear=True)
    def test_frontend_settings_api_can_clear_agent_api_base_url(self):
        common_data = {
            "instance_role": "local_device",
            "remote_service_url": "",
            "settings_password": "",
        }
        first_response = self.client.post(
            "/api/app-settings",
            json={
                **common_data,
                "openai_base_url": "http://127.0.0.1:8000/v1",
            },
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            "/api/app-settings",
            json={**common_data, "openai_base_url": ""},
        )

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.get_json()["openai_base_url"], "")
        self.assertNotIn("OPENAI_BASE_URL", os.environ)
        self.assertNotIn(
            "OPENAI_BASE_URL",
            Path(app.config["ENV_FILE"]).read_text(),
        )

    def test_frontend_settings_api_rejects_invalid_agent_api_base_url(self):
        response = self.client.post(
            "/api/app-settings",
            json={
                "instance_role": "local_device",
                "remote_service_url": "",
                "settings_password": "",
                "openai_base_url": "file:///tmp/model",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Base URL", response.get_json()["error"])

    def test_frontend_settings_api_rejects_invalid_agent_api_mode(self):
        response = self.client.post(
            "/api/app-settings",
            json={
                "instance_role": "local_device",
                "remote_service_url": "",
                "settings_password": "",
                "openai_api_mode": "legacy_completions",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("protocol", response.get_json()["error"])

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

    @patch.dict(os.environ, {"SETTINGS_PASSWORD": "admin-secret"}, clear=True)
    def test_frontend_settings_api_rejects_wrong_password(self):
        response = self.client.post(
            "/api/app-settings",
            json={
                "instance_role": "remote_server",
                "remote_service_url": "",
                "settings_password": "wrong",
            },
        )

        self.assertEqual(response.status_code, 403)

    @patch("app.run_selected_diagnostics")
    @patch("app.analyze_report")
    def test_local_diagnosis_saves_complete_report(self, analyze_report, run_selected):
        test_report = sample_report()
        test_report["layers"][1]["details"] = {
            "A records": ["93.184.216.34"],
            "Lookup": {"Resolver": "System resolver"},
        }
        run_selected.return_value = test_report
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
            headers={"Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 201)
        api_report_url = response.get_json()["report_url"].replace(
            "/reports/",
            "/api/reports/",
        )
        report_response = self.client.get(api_report_url)
        saved_report = report_response.get_json()
        self.assertEqual(saved_report["layers"][1]["key"], "dns")
        self.assertEqual(
            saved_report["layers"][1]["details"]["A records"],
            ["93.184.216.34"],
        )
        self.assertEqual(saved_report["analysis"]["source"], "not_configured")
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

        self.assert_frontend_response(response)

        api_response = self.client.get("/api/history")
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(len(api_response.get_json()["reports"]), 1)

        report_id = api_response.get_json()["reports"][0]["id"]
        report_response = self.client.get(f"/api/reports/{report_id}")
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(
            report_response.get_json()["target"]["url"],
            "https://example.com/",
        )

    def test_frontend_report_api_returns_not_found(self):
        response = self.client.get("/api/reports/999")

        self.assertEqual(response.status_code, 404)

    @patch("app.run_selected_diagnostics")
    @patch("app.analyze_report")
    def test_async_diagnosis_returns_report_url(self, analyze_report, run_selected):
        run_selected.return_value = sample_report()
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
            headers={"Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertRegex(response.get_json()["report_url"], r"^/reports/\d+$")

    @patch("app.run_selected_diagnostics")
    @patch("app.analyze_report")
    def test_agent_analysis_is_saved_without_legacy_reanalysis(
        self,
        analyze_report,
        run_selected,
    ):
        agent_report = sample_report()
        agent_report["analysis"] = {
            "source": "agent",
            "headline": "The target is reachable",
            "text": "HTTP returned 200.",
        }
        run_selected.return_value = agent_report

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
            headers={"Accept": "application/json"},
        )

        report_url = response.get_json()["report_url"].replace(
            "/reports/",
            "/api/reports/",
        )
        saved_report = self.client.get(report_url).get_json()
        self.assertEqual(saved_report["analysis"]["source"], "agent")
        analyze_report.assert_not_called()

    def test_async_diagnosis_returns_json_error(self):
        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "invalid"},
            headers={"Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid test mode.")

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
    def test_remote_diagnosis_saves_remote_report(self, run_selected, analyze_report):
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_selected.return_value = remote_report
        analyze_report.return_value = unconfigured_analysis()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "remote"},
            headers={"Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 201)
        report_url = response.get_json()["report_url"]
        api_report_url = report_url.replace("/reports/", "/api/reports/")
        report_response = self.client.get(api_report_url)
        self.assertEqual(report_response.get_json()["mode"], "remote")
        run_selected.assert_called_once_with(
            "example.com",
            "remote",
            {"instance_role": "local_device", "remote_service_url": ""},
        )

    @patch("app.analyze_report")
    @patch("app.run_selected_diagnostics")
    def test_compare_both_saves_side_by_side_report(
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
            headers={"Accept": "application/json"},
        )

        self.assertEqual(response.status_code, 201)
        report_url = response.get_json()["report_url"]
        api_report_url = report_url.replace("/reports/", "/api/reports/")
        report_response = self.client.get(api_report_url)
        saved_report = report_response.get_json()
        self.assertEqual(saved_report["mode"], "compare")
        self.assertIn("comparison", saved_report)
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

    @patch("app.run_agent_diagnostics")
    def test_api_returns_remote_report(self, run_agent):
        remote_report = sample_report()
        remote_report["mode"] = "remote"
        run_agent.return_value = remote_report

        response = self.client.post("/api/diagnose", json={"target": "example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "remote")
        run_agent.assert_called_once_with("example.com", mode="remote")

    @patch("app.run_agent_diagnostics")
    def test_api_returns_service_unavailable_when_agent_is_not_configured(
        self,
        run_agent,
    ):
        run_agent.side_effect = AgentConfigurationError(
            "Agent diagnostics require an OpenAI API key in Settings."
        )

        response = self.client.post("/api/diagnose", json={"target": "example.com"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("OpenAI API key", response.get_json()["error"])

    @patch.dict(os.environ, {"SERVICEPATH_API_TOKEN": "secret-token"}, clear=True)
    def test_api_rejects_wrong_token(self):
        response = self.client.post("/api/diagnose", json={"target": "example.com"})

        self.assertEqual(response.status_code, 401)

    def test_api_rejects_non_object_json(self):
        response = self.client.post("/api/diagnose", json=["example.com"])

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
