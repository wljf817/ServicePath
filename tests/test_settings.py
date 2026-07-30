import unittest

from app_settings import (
    SettingsError,
    validate_openai_api_mode,
    validate_openai_base_url,
    validate_settings,
)


class SettingsValidationTests(unittest.TestCase):
    def test_accepts_remote_server_role(self):
        settings = validate_settings("remote_server", "")

        self.assertEqual(settings["instance_role"], "remote_server")

    def test_normalizes_remote_url(self):
        settings = validate_settings(
            "local_device",
            "https://servicepath.example/",
        )

        self.assertEqual(
            settings["remote_service_url"],
            "https://servicepath.example",
        )

    def test_rejects_invalid_role(self):
        with self.assertRaises(SettingsError):
            validate_settings("browser", "")

    def test_rejects_invalid_remote_url(self):
        with self.assertRaises(SettingsError):
            validate_settings("local_device", "ftp://servicepath.example")

    def test_normalizes_optional_agent_api_base_url(self):
        self.assertEqual(validate_openai_base_url(""), "")
        self.assertEqual(
            validate_openai_base_url("http://127.0.0.1:8000/v1/"),
            "http://127.0.0.1:8000/v1",
        )

    def test_rejects_unsafe_agent_api_base_url(self):
        invalid_urls = [
            "ftp://models.example/v1",
            "https://user:password@models.example/v1",
            "https://models.example/v1?token=secret",
            "https://models.example/v1#fragment",
        ]

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


if __name__ == "__main__":
    unittest.main()
