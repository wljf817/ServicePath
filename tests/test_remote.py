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
        "analysis": {
            "source": "agent",
            "headline": "Target is reachable",
        },
        "agent": {
            "model": "gpt-test",
            "checks_used": 5,
            "max_checks": 6,
            "requested_tools": [],
            "tool_log": [],
        },
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
            json={"target": "https://example.com/"},
            headers={"Authorization": "Bearer secret-token"},
            timeout=120,
        )

    @patch("diagnostics.remote.requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_accepts_service_url_argument(self, post):
        response = Mock()
        response.json.return_value = remote_report()
        post.return_value = response

        run_remote_diagnostics(
            "example.com",
            service_url="https://configured.example",
        )

        self.assertEqual(
            post.call_args.args[0],
            "https://configured.example/api/diagnose",
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

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_malformed_adaptive_evidence(self, post):
        response = Mock()
        response.json.return_value = remote_report()
        response.json.return_value["layers"][0]["details"] = "not-an-object"
        post.return_value = response

        with self.assertRaisesRegex(RemoteError, "invalid layer"):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_report_for_a_different_target(self, post):
        response = Mock()
        response.json.return_value = remote_report()
        response.json.return_value["target"]["url"] = "https://other.example/"
        post.return_value = response

        with self.assertRaisesRegex(RemoteError, "does not match"):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_surfaces_safe_remote_agent_error(self, post):
        response = Mock()
        response.ok = False
        response.json.return_value = {
            "error": "Agent diagnostics require an OpenAI API key in Settings."
        }
        post.return_value = response

        with self.assertRaisesRegex(RemoteError, "OpenAI API key"):
            run_remote_diagnostics("example.com")


if __name__ == "__main__":
    unittest.main()
