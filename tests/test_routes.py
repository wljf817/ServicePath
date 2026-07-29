import unittest
from unittest.mock import patch

from app import app
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
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_home_page_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Start diagnosis", response.data)

    @patch("app.run_diagnostics")
    def test_local_diagnosis_displays_report(self, run_diagnostics):
        run_diagnostics.return_value = sample_report()

        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "local"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DNS passed", response.data)
        run_diagnostics.assert_called_once_with("example.com", mode="local")

    def test_remote_mode_is_not_configured_yet(self):
        response = self.client.post(
            "/diagnose",
            data={"domain": "example.com", "mode": "remote"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Remote Test is not configured", response.data)


if __name__ == "__main__":
    unittest.main()
