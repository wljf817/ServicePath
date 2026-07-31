import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from servicepath.container import main, seed_configuration


class ContainerConfigurationTests(unittest.TestCase):
    def test_seeds_a_private_environment_file_once(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment_file = Path(temporary_directory) / ".env"
            initial_environment = {
                "OPENAI_API_KEY": "initial-key",
                "OPENAI_MODEL": "initial-model",
                "SERVICEPATH_API_TOKEN": "initial-token",
                "SETTINGS_PASSWORD": "initial-password",
            }

            self.assertTrue(
                seed_configuration(environment_file, initial_environment)
            )
            self.assertEqual(
                dotenv_values(environment_file)["OPENAI_API_KEY"],
                "initial-key",
            )
            self.assertEqual(
                stat.S_IMODE(environment_file.stat().st_mode),
                0o600,
            )

            self.assertFalse(
                seed_configuration(
                    environment_file,
                    {"OPENAI_API_KEY": "replacement-key"},
                )
            )
            self.assertEqual(
                dotenv_values(environment_file)["OPENAI_API_KEY"],
                "initial-key",
            )

    def test_entrypoint_executes_with_persistent_configuration(self):
        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "container-key",
                    "SERVICEPATH_DATA_DIR": temporary_directory,
                    "SETTINGS_PASSWORD": "container-password",
                },
                clear=True,
            ),
            patch("servicepath.container.os.execvp") as execute,
        ):
            main(["gunicorn", "app:app"])

            execute.assert_called_once_with(
                "gunicorn",
                ["gunicorn", "app:app"],
            )
            self.assertNotIn("OPENAI_API_KEY", os.environ)
            self.assertNotIn("SETTINGS_PASSWORD", os.environ)
            self.assertEqual(
                dotenv_values(Path(temporary_directory) / ".env")[
                    "OPENAI_API_KEY"
                ],
                "container-key",
            )


if __name__ == "__main__":
    unittest.main()
