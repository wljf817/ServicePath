import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from servicepath.settings import (
    SettingsError,
    update_environment_settings,
    validate_openai_api_mode,
    validate_openai_base_url,
    validate_servicepath_api_token,
    validate_settings,
)


class SettingsValidationTests(unittest.TestCase):
    def test_accepts_supported_roles(self):
        for role in ("remote_server", "local_device"):
            with self.subTest(role=role):
                settings = validate_settings(role, "")
                self.assertEqual(settings["instance_role"], role)

    def test_normalizes_values(self):
        settings = validate_settings(
            " local_device ",
            " https://servicepath.example/api/ ",
        )

        self.assertEqual(settings["instance_role"], "local_device")
        self.assertEqual(
            settings["remote_service_url"],
            "https://servicepath.example/api",
        )

    def test_rejects_invalid_role(self):
        with self.assertRaises(SettingsError):
            validate_settings("browser", "")

    def test_rejects_unsafe_remote_urls(self):
        invalid_urls = (
            "ftp://servicepath.example",
            "https://user:password@servicepath.example",
            "https://servicepath.example/path?token=secret",
            "https://servicepath.example/path#fragment",
            "https://service path.example",
            "https://servicepath.example:invalid",
        )

        for value in invalid_urls:
            with self.subTest(value=value), self.assertRaises(SettingsError):
                validate_settings("local_device", value)

    def test_normalizes_optional_agent_api_base_url(self):
        self.assertEqual(validate_openai_base_url(""), "")
        self.assertEqual(
            validate_openai_base_url("http://127.0.0.1:8000/v1/"),
            "http://127.0.0.1:8000/v1",
        )

    def test_normalizes_idn_and_ip_hosts(self):
        cases = {
            "HTTPS://BÜCHER.Example/api/": (
                "https://xn--bcher-kva.example/api"
            ),
            "http://[2001:0db8::1]:8000/v1/": (
                "http://[2001:db8::1]:8000/v1"
            ),
            "https://Example.COM./": "https://example.com",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(validate_openai_base_url(value), expected)

    def test_rejects_unsafe_agent_api_base_url(self):
        invalid_urls = (
            "ftp://models.example/v1",
            "https://user:password@models.example/v1",
            "https://models.example/v1?token=secret",
            "https://models.example/v1#fragment",
            "https://models.example:invalid/v1",
            "https://models.example:/v1",
            "https://@models.example/v1",
            "https://bad_host.example/v1",
            "https://-bad.example/v1",
            "https://bad-.example/v1",
            "https://bad..example/v1",
            "https://models%2eexample/v1",
            r"https://models.example\v1",
            "https://models.example/\x00v1",
        )

        for value in invalid_urls:
            with self.subTest(value=value), self.assertRaises(SettingsError):
                validate_openai_base_url(value)

    def test_validates_agent_api_mode(self):
        self.assertEqual(validate_openai_api_mode(""), "auto")
        self.assertEqual(
            validate_openai_api_mode(" CHAT_COMPLETIONS "),
            "chat_completions",
        )

        with self.assertRaises(SettingsError):
            validate_openai_api_mode("completions")

    def test_validates_remote_api_token(self):
        self.assertEqual(
            validate_servicepath_api_token(" token._~+/== "),
            "token._~+/==",
        )
        for value in ("secret:token", "two words", "token,other"):
            with self.subTest(value=value), self.assertRaises(SettingsError):
                validate_servicepath_api_token(value)


class EnvironmentSettingsTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temporary_directory.name) / "config" / ".env"

    def tearDown(self):
        self.temporary_directory.cleanup()
        self.environment.stop()

    def test_writes_supplied_values_to_private_file(self):
        update_environment_settings(
            self.env_path,
            {
                "servicepath_api_token": "remote-token",
                "openai_api_key": "openai-key",
                "openai_model": "gpt-test",
                "new_settings_password": "admin-secret",
                "openai_base_url": "https://models.example/v1/",
                "openai_api_mode": "responses",
            },
        )

        values = dotenv_values(self.env_path)
        self.assertEqual(values["SERVICEPATH_API_TOKEN"], "remote-token")
        self.assertEqual(values["OPENAI_BASE_URL"], "https://models.example/v1")
        self.assertEqual(os.environ["OPENAI_API_MODE"], "responses")
        self.assertEqual(stat.S_IMODE(self.env_path.stat().st_mode), 0o600)

    def test_omitted_secrets_keep_existing_values(self):
        update_environment_settings(
            self.env_path,
            {"openai_api_key": "existing-key"},
        )
        update_environment_settings(self.env_path, {})

        self.assertEqual(
            dotenv_values(self.env_path)["OPENAI_API_KEY"],
            "existing-key",
        )

    def test_explicit_empty_base_url_removes_existing_value(self):
        update_environment_settings(
            self.env_path,
            {"openai_base_url": "https://models.example/v1"},
        )
        update_environment_settings(self.env_path, {"openai_base_url": ""})

        self.assertNotIn("OPENAI_BASE_URL", dotenv_values(self.env_path))
        self.assertNotIn("OPENAI_BASE_URL", os.environ)


if __name__ == "__main__":
    unittest.main()
