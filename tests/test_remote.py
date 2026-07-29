import os
import unittest
from unittest.mock import Mock, patch

from diagnostics.remote import RemoteError, run_remote_diagnostics
from diagnostics.result import make_result


def remote_report():
    names = ["Client Network", "DNS", "TCP", "TLS", "HTTP"]
    keys = ["client", "dns", "tcp", "tls", "http"]
    return {
        "target": {"url": "https://example.com/"},
        "mode": "remote",
        "status": "passed",
        "first_problem": None,
        "created_at": "2026-07-29T12:00:00+00:00",
        "duration_ms": 100,
        "layers": [
            make_result(key, name, "passed", "Passed")
            for key, name in zip(keys, names)
        ],
    }


class RemoteDiagnosticTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_requires_remote_service_url(self):
        with self.assertRaises(RemoteError):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {
            "REMOTE_SERVICE_URL": "https://servicepath.example",
            "SERVICEPATH_API_TOKEN": "secret-token",
        },
        clear=True,
    )
    def test_calls_remote_api_with_token(self, post):
        response = Mock()
        response.json.return_value = remote_report()
        post.return_value = response

        report = run_remote_diagnostics("example.com")

        self.assertEqual(report["mode"], "remote")
        post.assert_called_once_with(
            "https://servicepath.example/api/diagnose",
            json={"target": "example.com"},
            headers={"Authorization": "Bearer secret-token"},
            timeout=45,
        )

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_incomplete_remote_report(self, post):
        response = Mock()
        response.json.return_value = {"target": {}, "layers": []}
        post.return_value = response

        with self.assertRaises(RemoteError):
            run_remote_diagnostics("example.com")


if __name__ == "__main__":
    unittest.main()
