import json
import os
import unittest
from unittest.mock import Mock, patch

from diagnostics.remote import (
    MAX_REMOTE_RESPONSE_BYTES,
    RemoteError,
    run_remote_diagnostics,
)
from diagnostics.result import make_result


def remote_report():
    names = ["Client Network", "DNS", "TCP", "TLS", "HTTP"]
    keys = ["client", "dns", "tcp", "tls", "http"]
    return {
        "target": {
            "original": "https://example.com/",
            "hostname": "example.com",
            "scheme": "https",
            "port": None,
            "url": "https://example.com/",
        },
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
            "model": "gpt-test",
            "completion": "complete",
            "verdict": "reachable",
            "headline": "Target is reachable",
            "text": "HTTP returned 200.",
            "failure_stage": None,
            "confidence": "high",
            "evidence": ["HTTP: HTTP returned 200."],
            "causes": [],
            "actions": [],
        },
        "agent": {
            "model": "gpt-test",
            "api_mode": "responses",
            "completion": "complete",
            "checks_used": 5,
            "max_checks": 6,
            "requested_tools": [],
            "tool_log": [],
            "model_calls": 1,
            "token_usage": {"input": 10, "output": 5, "total": 15},
        },
    }


def remote_response(payload, ok=True):
    body = json.dumps(payload).encode("utf-8")
    response = Mock()
    response.ok = ok
    response.status_code = 200 if ok else 500
    response.is_redirect = False
    response.headers = {"Content-Length": str(len(body))}
    response.encoding = "utf-8"
    response.iter_content.return_value = [body]
    return response


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
            "SERVICEPATH_API_TOKEN": "two tokens",
        },
        clear=True,
    )
    def test_rejects_invalid_api_token_before_request(self, post):
        with self.assertRaisesRegex(RemoteError, "API_TOKEN"):
            run_remote_diagnostics("example.com")

        post.assert_not_called()

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
        post.return_value = remote_response(remote_report())

        report = run_remote_diagnostics("example.com")

        self.assertEqual(report["mode"], "remote")
        post.assert_called_once_with(
            "https://servicepath.example/api/diagnose",
            json={"target": "https://example.com/"},
            headers={"Authorization": "Bearer secret-token"},
            timeout=120,
            stream=True,
            allow_redirects=False,
        )
        post.return_value.close.assert_called_once_with()

    @patch("diagnostics.remote.requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_accepts_service_url_argument(self, post):
        post.return_value = remote_response(remote_report())

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
        post.return_value = remote_response({"target": {}, "layers": []})

        with self.assertRaises(RemoteError):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_malformed_adaptive_evidence(self, post):
        report = remote_report()
        report["layers"][0]["details"] = "not-an-object"
        post.return_value = remote_response(report)

        with self.assertRaisesRegex(RemoteError, "invalid layer"):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_report_for_a_different_target(self, post):
        report = remote_report()
        report["target"]["url"] = "https://other.example/"
        post.return_value = remote_response(report)

        with self.assertRaisesRegex(RemoteError, "does not match"):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_surfaces_safe_remote_agent_error(self, post):
        post.return_value = remote_response(
            {"error": "Agent diagnostics require an OpenAI API key in Settings."},
            ok=False,
        )

        with self.assertRaisesRegex(RemoteError, "OpenAI API key"):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_rejects_invalid_remote_service_urls(self, post):
        invalid_urls = [
            "https://bad_name.example",
            "https://servicepath.example?token=secret",
            "https://servicepath.example#fragment",
            "https://servicepath.example:",
        ]

        for value in invalid_urls:
            with self.subTest(value=value):
                with self.assertRaises(RemoteError):
                    run_remote_diagnostics("example.com", service_url=value)

        post.assert_not_called()

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_oversized_remote_response(self, post):
        response = remote_response(remote_report())
        response.headers["Content-Length"] = str(MAX_REMOTE_RESPONSE_BYTES + 1)
        post.return_value = response

        with self.assertRaisesRegex(RemoteError, "too large"):
            run_remote_diagnostics("example.com")

        response.close.assert_called_once_with()

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_oversized_stream_without_content_length(self, post):
        response = remote_response(remote_report())
        response.headers = {}
        response.iter_content.return_value = [
            b"x" * (MAX_REMOTE_RESPONSE_BYTES + 1)
        ]
        post.return_value = response

        with self.assertRaisesRegex(RemoteError, "too large"):
            run_remote_diagnostics("example.com")

    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_rejects_unsafe_nested_report_fields(self, post):
        cases = {
            "target hostname": lambda report: report["target"].update(
                hostname={"unsafe": True}
            ),
            "analysis headline": lambda report: report["analysis"].update(
                headline={"unsafe": True}
            ),
            "analysis evidence": lambda report: report["analysis"].update(
                evidence=[{"unsafe": True}]
            ),
            "agent model": lambda report: report["agent"].update(
                model={"unsafe": True}
            ),
            "agent tools": lambda report: report["agent"].update(
                requested_tools=[{"tool": {"unsafe": True}}]
            ),
            "layer summary": lambda report: report["layers"][0].update(
                summary={"unsafe": True}
            ),
            "traceroute": lambda report: report.update(
                traceroute={"key": "traceroute", "name": {"unsafe": True}}
            ),
            "comparison": lambda report: report.update(
                comparison={"title": {"unsafe": True}}
            ),
            "timestamp": lambda report: report.update(
                created_at="not-a-date"
            ),
            "status mismatch": lambda report: report.update(status="error"),
            "failure mismatch": lambda report: report.update(
                first_problem="dns"
            ),
            "model mismatch": lambda report: report["agent"].update(
                model="other-model"
            ),
        }

        for name, mutate in cases.items():
            with self.subTest(name=name):
                report = remote_report()
                mutate(report)
                post.return_value = remote_response(report)
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
    def test_does_not_follow_remote_service_redirects(self, post):
        response = remote_response({"redirect": True})
        response.status_code = 302
        response.is_redirect = True
        response.headers["Location"] = "https://other.example/api/diagnose"
        post.return_value = response

        with self.assertRaisesRegex(RemoteError, "does not follow"):
            run_remote_diagnostics("example.com")

        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        post.assert_called_once()

    @patch("diagnostics.remote.monotonic", side_effect=[0, 121])
    @patch("diagnostics.remote.requests.post")
    @patch.dict(
        os.environ,
        {"REMOTE_SERVICE_URL": "https://servicepath.example"},
        clear=True,
    )
    def test_enforces_response_deadline(self, post, monotonic):
        post.return_value = remote_response(remote_report())

        with self.assertRaisesRegex(RemoteError, "time limit"):
            run_remote_diagnostics("example.com", timeout=120)


if __name__ == "__main__":
    unittest.main()
