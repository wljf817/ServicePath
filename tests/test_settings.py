import unittest

from app_settings import SettingsError, validate_settings


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


if __name__ == "__main__":
    unittest.main()
