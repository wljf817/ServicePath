import os
import unittest
from unittest.mock import patch

from diagnostics.analysis import analyze_report, rule_based_analysis


def report(first_problem):
    return {
        "target": {"url": "https://example.com/"},
        "status": "error" if first_problem else "passed",
        "first_problem": first_problem,
        "layers": [],
    }


class AnalysisTests(unittest.TestCase):
    def test_explains_dns_failure(self):
        analysis = rule_based_analysis(report("dns"))

        self.assertEqual(analysis["source"], "rules")
        self.assertIn("DNS", analysis["title"])
        self.assertTrue(analysis["actions"])

    def test_explains_successful_report(self):
        analysis = rule_based_analysis(report(None))

        self.assertEqual(analysis["title"], "No failure was detected")

    @patch.dict(os.environ, {}, clear=True)
    def test_uses_rules_without_api_key(self):
        analysis = analyze_report(report("http"))

        self.assertEqual(analysis["source"], "rules")

    @patch("diagnostics.analysis.request_openai_analysis")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_falls_back_when_ai_request_fails(self, request_analysis):
        request_analysis.side_effect = RuntimeError("service unavailable")

        analysis = analyze_report(report("tls"))

        self.assertEqual(analysis["source"], "rules")
        self.assertIn("AI analysis was unavailable", analysis["note"])


if __name__ == "__main__":
    unittest.main()
