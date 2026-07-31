import os
import re
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from diagnostics.agent import AgentConfigurationError
from diagnostics.execution import ExecutionError
from diagnostics.remote import RemoteError
from diagnostics.result import make_result
from diagnostics.target import TargetError
from servicepath import create_app
from servicepath.database import get_settings, update_settings


def sample_report(mode="local"):
    """Build a complete report for route tests."""
    layer_names = {
        "client": "Client Network",
        "dns": "DNS",
        "tcp": "TCP",
        "tls": "TLS",
        "http": "HTTP",
    }
    return {
        "target": {"url": "https://example.com/"},
        "mode": mode,
        "created_at": "2026-07-29T12:00:00+00:00",
        "duration_ms": 120,
        "status": "passed",
        "first_problem": None,
        "layers": [
            make_result(key, name, "passed", f"{name} passed", 10)
            for key, name in layer_names.items()
        ],
        "analysis": {
            "source": "agent",
            "headline": "The target is reachable",
            "text": "HTTP returned 200.",
        },
    }


class ApplicationFactoryTests(unittest.TestCase):
    def test_uses_configured_data_directory(self):
        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            patch.dict(
                os.environ,
                {"SERVICEPATH_DATA_DIR": temporary_directory},
                clear=True,
            ),
        ):
            app = create_app({"LOAD_DOTENV": False, "TESTING": True})
            data_directory = Path(temporary_directory).resolve()

            self.assertEqual(Path(app.instance_path), data_directory)
            self.assertEqual(
                Path(app.config["DATABASE"]),
                data_directory / "servicepath.db",
            )
            self.assertEqual(
                Path(app.config["ENV_FILE"]),
                data_directory / ".env",
            )


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.app = create_app(
            {
                "DATABASE": str(root / "instance" / "test.db"),
                "ENV_FILE": str(root / ".env"),
                "LOAD_DOTENV": False,
                "TESTING": True,
            }
        )
        update_settings(
            self.app.config["DATABASE"],
            {"instance_role": "local_device", "remote_service_url": ""},
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()
        self.environment.stop()

    def settings_payload(self, **overrides):
        payload = {
            "instance_role": "local_device",
            "remote_service_url": "",
            "settings_password": "",
        }
        payload.update(overrides)
        return payload

    def assert_frontend_response(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<div id="root"></div>', response.data)
        assets = re.findall(
            rb'(?:href|src)="(/static/frontend/[^"?#]+)',
            response.data,
        )
        self.assertTrue(assets)
        for asset in assets:
            asset_response = self.client.get(asset.decode())
            self.assertEqual(asset_response.status_code, 200, asset.decode())
            asset_response.close()
        response.close()

    def test_frontend_routes_and_assets_load(self):
        for path in ("/", "/history", "/settings"):
            with self.subTest(path=path):
                self.assert_frontend_response(self.client.get(path))

    def test_health_check_reads_the_database(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_legacy_settings_post_is_not_available(self):
        response = self.client.post(
            "/settings",
            data={"instance_role": "local_device"},
        )

        self.assertEqual(response.status_code, 405)

    def test_app_settings_returns_safe_configuration(self):
        response = self.client.get("/api/app-settings")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["settings"]["instance_role"], "local_device")
        self.assertFalse(data["agent_configured"])
        self.assertNotIn("ai_configured", data)
        self.assertNotIn("openai_api_key", data)

    def test_app_settings_treats_blank_environment_as_unconfigured(self):
        os.environ.update(
            {
                "OPENAI_API_KEY": "  ",
                "OPENAI_MODEL": "\t",
                "OPENAI_BASE_URL": " \n ",
                "OPENAI_API_MODE": " ",
                "SERVICEPATH_API_TOKEN": "\t",
                "SETTINGS_PASSWORD": " ",
            }
        )

        response = self.client.get("/api/app-settings")

        data = response.get_json()
        self.assertFalse(data["agent_configured"])
        self.assertFalse(data["api_token_configured"])
        self.assertFalse(data["password_required"])
        self.assertEqual(data["openai_model"], "gpt-5.6")
        self.assertEqual(data["openai_base_url"], "")
        self.assertEqual(data["openai_api_mode"], "auto")

    def test_app_settings_normalizes_runtime_environment(self):
        os.environ.update(
            {
                "OPENAI_API_KEY": " test-key ",
                "OPENAI_MODEL": " gpt-test ",
                "OPENAI_BASE_URL": " https://BÜCHER.example/v1/ ",
                "OPENAI_API_MODE": " RESPONSES ",
                "SERVICEPATH_API_TOKEN": " remote-token ",
            }
        )

        data = self.client.get("/api/app-settings").get_json()

        self.assertTrue(data["agent_configured"])
        self.assertTrue(data["api_token_configured"])
        self.assertEqual(data["openai_model"], "gpt-test")
        self.assertEqual(
            data["openai_base_url"],
            "https://xn--bcher-kva.example/v1",
        )
        self.assertEqual(data["openai_api_mode"], "responses")

    def test_local_cli_request_can_update_settings_without_password(self):
        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(
                remote_service_url="https://servicepath.example/"
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["settings"]["remote_service_url"],
            "https://servicepath.example",
        )

    def test_local_vite_origin_can_update_settings(self):
        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(),
            headers={"Origin": "http://localhost:5173"},
        )

        self.assertEqual(response.status_code, 200)

    def test_local_bypass_requires_exact_loopback_address_and_host(self):
        cases = (
            ({"Host": "localhost"}, {"REMOTE_ADDR": "127.0.0.2"}),
            ({"Host": "localhost.example"}, {"REMOTE_ADDR": "127.0.0.1"}),
            ({"Host": "servicepath.example"}, {"REMOTE_ADDR": "127.0.0.1"}),
        )

        for headers, environment in cases:
            with self.subTest(headers=headers, environment=environment):
                response = self.client.post(
                    "/api/app-settings",
                    json=self.settings_payload(),
                    headers=headers,
                    environ_base=environment,
                )
                self.assertEqual(response.status_code, 403)

    def test_local_bypass_rejects_forwarded_requests(self):
        for header in (
            "Forwarded",
            "X-Forwarded-For",
            "X-Forwarded-Host",
            "X-Forwarded-Port",
            "X-Forwarded-Prefix",
            "X-Forwarded-Proto",
            "X-Forwarded-Custom",
            "X-Real-IP",
        ):
            with self.subTest(header=header):
                response = self.client.post(
                    "/api/app-settings",
                    json=self.settings_payload(),
                    headers={header: "proxy.example"},
                )
                self.assertEqual(response.status_code, 403)

    def test_local_bypass_rejects_nonlocal_origin(self):
        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(),
            headers={"Origin": "https://servicepath.example"},
        )

        self.assertEqual(response.status_code, 403)

    def test_configured_password_allows_remote_settings_update(self):
        os.environ["SETTINGS_PASSWORD"] = "admin-secret"

        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(settings_password="admin-secret"),
            headers={"Host": "servicepath.example"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )

        self.assertEqual(response.status_code, 200)

    def test_configured_password_rejects_wrong_password(self):
        os.environ["SETTINGS_PASSWORD"] = "admin-secret"

        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(settings_password="wrong"),
        )

        self.assertEqual(response.status_code, 403)

    def test_settings_api_requires_json_object(self):
        form_response = self.client.post(
            "/api/app-settings",
            data={"instance_role": "local_device"},
        )
        list_response = self.client.post("/api/app-settings", json=[])

        self.assertEqual(form_response.status_code, 415)
        self.assertEqual(list_response.status_code, 400)

    def test_settings_api_persists_secrets_without_returning_them(self):
        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(
                servicepath_api_token="remote-token",
                openai_api_key="openai-key",
                openai_base_url="https://models.example/v1/",
                openai_api_mode="chat_completions",
                openai_model="gpt-test",
                new_settings_password="new-password",
            ),
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["api_token_configured"])
        self.assertTrue(data["agent_configured"])
        self.assertTrue(data["password_required"])
        self.assertEqual(data["openai_model"], "gpt-test")
        self.assertEqual(data["openai_base_url"], "https://models.example/v1")
        self.assertEqual(data["openai_api_mode"], "chat_completions")
        self.assertNotIn("openai_api_key", data)

        env_text = Path(self.app.config["ENV_FILE"]).read_text()
        self.assertIn("OPENAI_API_KEY='openai-key'", env_text)
        self.assertIn("SETTINGS_PASSWORD='new-password'", env_text)

    def test_settings_api_rejects_an_invalid_remote_token(self):
        response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(servicepath_api_token="secret:token"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("token", response.get_json()["error"].lower())

    def test_settings_api_can_clear_optional_base_url(self):
        first_response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(
                openai_base_url="http://127.0.0.1:8000/v1"
            ),
        )
        second_response = self.client.post(
            "/api/app-settings",
            json=self.settings_payload(openai_base_url=""),
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.get_json()["openai_base_url"], "")
        self.assertNotIn("OPENAI_BASE_URL", os.environ)

    @patch("servicepath.routes.run_selected_diagnostics")
    def test_diagnosis_saves_report_and_returns_url(self, run_selected):
        report = sample_report()
        report["layers"][1]["details"] = {
            "A records": ["93.184.216.34"],
        }
        run_selected.return_value = report

        response = self.client.post(
            "/diagnose",
            json={"domain": "example.com", "mode": "local"},
        )

        self.assertEqual(response.status_code, 201)
        report_url = response.get_json()["report_url"]
        self.assertRegex(report_url, r"^/reports/\d+$")
        saved = self.client.get(
            report_url.replace("/reports/", "/api/reports/")
        ).get_json()
        self.assertEqual(
            saved["layers"][1]["details"]["A records"],
            ["93.184.216.34"],
        )
        run_selected.assert_called_once_with(
            "example.com",
            "local",
            {"instance_role": "local_device", "remote_service_url": ""},
        )

    def test_diagnosis_is_json_only(self):
        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
        )

        self.assertEqual(response.status_code, 415)
        self.assertIn("application/json", response.get_json()["error"])

    def test_diagnosis_rejects_malformed_or_nonobject_json(self):
        malformed = self.client.post(
            "/diagnose",
            data="{",
            content_type="application/json",
        )
        nonobject = self.client.post("/diagnose", json=["example.com"])

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(nonobject.status_code, 400)

    def test_diagnosis_rejects_invalid_mode(self):
        response = self.client.post(
            "/diagnose",
            json={"domain": "example.com", "mode": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Invalid test mode.")

    @patch("servicepath.routes.run_selected_diagnostics")
    def test_diagnostic_errors_use_stable_status_codes(self, run_selected):
        cases = (
            (TargetError("bad target"), 400),
            (ExecutionError("wrong role"), 409),
            (RemoteError("remote failed"), 503),
            (AgentConfigurationError("missing key"), 503),
        )

        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__):
                run_selected.side_effect = error
                response = self.client.post(
                    "/diagnose",
                    json={"domain": "example.com", "mode": "local"},
                )
                self.assertEqual(response.status_code, expected_status)

    @patch("servicepath.routes.run_selected_diagnostics")
    def test_saved_report_appears_in_history(self, run_selected):
        run_selected.return_value = sample_report()
        self.client.post(
            "/diagnose",
            json={"domain": "example.com", "mode": "local"},
        )

        response = self.client.get("/api/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["reports"]), 1)

    def test_missing_report_returns_not_found(self):
        self.assertEqual(self.client.get("/api/reports/999").status_code, 404)
        self.assertEqual(self.client.get("/reports/999").status_code, 404)

    @patch("servicepath.routes.run_agent_diagnostics")
    def test_remote_api_returns_report(self, run_agent):
        run_agent.return_value = sample_report(mode="remote")

        response = self.client.post(
            "/api/diagnose",
            json={"target": "example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "remote")
        run_agent.assert_called_once_with("example.com", mode="remote")

    @patch("servicepath.routes.run_agent_diagnostics")
    def test_remote_api_returns_service_unavailable_for_agent_error(
        self,
        run_agent,
    ):
        run_agent.side_effect = AgentConfigurationError("missing API key")

        response = self.client.post(
            "/api/diagnose",
            json={"target": "example.com"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "missing API key")

    @patch("servicepath.routes.run_agent_diagnostics")
    def test_remote_api_accepts_valid_case_insensitive_bearer_scheme(
        self,
        run_agent,
    ):
        os.environ["SERVICEPATH_API_TOKEN"] = "secret-token"
        run_agent.return_value = sample_report(mode="remote")

        response = self.client.post(
            "/api/diagnose",
            json={"target": "example.com"},
            headers={"Authorization": "bearer secret-token"},
        )

        self.assertEqual(response.status_code, 200)

    @patch("servicepath.routes.run_agent_diagnostics")
    def test_remote_api_rejects_malformed_bearer_headers(self, run_agent):
        os.environ["SERVICEPATH_API_TOKEN"] = "secret-token"
        headers = (
            "",
            "Basic secret-token",
            "Bearer",
            "Bearer  secret-token",
            "Bearer secret-token ",
            "Bearer secret-token,other",
            "Token Bearer secret-token",
        )

        for authorization in headers:
            with self.subTest(authorization=authorization):
                response = self.client.post(
                    "/api/diagnose",
                    json={"target": "example.com"},
                    headers={"Authorization": authorization},
                )
                self.assertEqual(response.status_code, 401)
        run_agent.assert_not_called()

    def test_remote_api_requires_json_object(self):
        form_response = self.client.post(
            "/api/diagnose",
            data={"target": "example.com"},
        )
        list_response = self.client.post("/api/diagnose", json=[])

        self.assertEqual(form_response.status_code, 415)
        self.assertEqual(list_response.status_code, 400)

class EntryPointTests(unittest.TestCase):
    def test_entry_point_disables_flasks_second_dotenv_load(self):
        fake_app = MagicMock()
        app_path = Path(__file__).resolve().parent.parent / "app.py"

        with (
            patch("servicepath.create_app", return_value=fake_app),
            patch.dict(os.environ, {"SERVICEPATH_DEBUG": "true"}, clear=True),
        ):
            runpy.run_path(str(app_path), run_name="__main__")

        fake_app.run.assert_called_once_with(
            debug=True,
            port=5050,
            load_dotenv=False,
        )


if __name__ == "__main__":
    unittest.main()
