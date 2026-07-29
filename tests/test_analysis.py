import os
import unittest
from unittest.mock import patch

from diagnostics.analysis import analyze_report, collect_issues
from diagnostics.result import make_result


def report(status="warning"):
    return {
        "target": {"url": "https://example.com/"},
        "mode": "local",
        "status": status,
        "first_problem": "http" if status != "passed" else None,
        "layers": [
            make_result("dns", "DNS", "passed", "DNS passed."),
            make_result("http", "HTTP", status, "HTTP returned 404."),
        ],
    }


class AnalysisTests(unittest.TestCase):
    def test_collects_only_warnings_and_errors(self):
        issues = collect_issues(report())

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["layer"], "HTTP")
        self.assertEqual(issues[0]["status"], "warning")

    def test_collects_issues_from_both_locations(self):
        local_report = report("error")
        remote_report = report("warning")
        comparison_report = {
            "mode": "compare",
            "local_report": local_report,
            "remote_report": remote_report,
        }

        issues = collect_issues(comparison_report)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]["location"], "Local Test")
        self.assertEqual(issues[1]["location"], "Remote Test")

    @patch.dict(os.environ, {}, clear=True)
    def test_reports_unconfigured_ai_without_advice(self):
        analysis = analyze_report(report())

        self.assertEqual(analysis["source"], "not_configured")
        self.assertEqual(len(analysis["issues"]), 1)
        self.assertNotIn("actions", analysis)
        self.assertNotIn("causes", analysis)

    @patch("diagnostics.analysis.request_openai_analysis")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_reports_ai_failure_without_fallback_advice(self, request_analysis):
        request_analysis.side_effect = RuntimeError("service unavailable")

        analysis = analyze_report(report("error"))

        self.assertEqual(analysis["source"], "unavailable")
        self.assertEqual(len(analysis["issues"]), 1)
        self.assertNotIn("actions", analysis)
        self.assertNotIn("service unavailable", analysis["message"])


if __name__ == "__main__":
    unittest.main()
