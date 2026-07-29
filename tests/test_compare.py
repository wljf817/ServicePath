import unittest

from diagnostics.compare import compare_reports
from diagnostics.result import make_result


LAYER_NAMES = {
    "client": "Client Network",
    "dns": "DNS",
    "tcp": "TCP",
    "tls": "TLS",
    "http": "HTTP",
}


def report(problem=None, problem_status="error"):
    layers = []

    for key, name in LAYER_NAMES.items():
        status = problem_status if key == problem else "passed"
        layers.append(make_result(key, name, status, f"{name} {status}"))

    return {
        "target": {"url": "https://example.com/"},
        "mode": "local",
        "created_at": "2026-07-29T12:00:00+00:00",
        "duration_ms": 100,
        "status": problem_status if problem else "passed",
        "first_problem": problem,
        "layers": layers,
    }


class CompareReportsTests(unittest.TestCase):
    def test_reports_no_issue_when_both_pass(self):
        result = compare_reports(report(), report())

        self.assertEqual(result["comparison"]["classification"], "no_issue")
        self.assertEqual(result["status"], "passed")

    def test_reports_local_only_problem(self):
        result = compare_reports(report("dns"), report())

        self.assertEqual(result["comparison"]["classification"], "local_only")
        self.assertIn("local", result["comparison"]["title"].lower())

    def test_reports_remote_only_problem(self):
        result = compare_reports(report(), report("tcp"))

        self.assertEqual(result["comparison"]["classification"], "remote_only")

    def test_reports_shared_problem(self):
        result = compare_reports(report("http"), report("http"))

        self.assertEqual(result["comparison"]["classification"], "shared_problem")
        self.assertEqual(result["first_problem"], "http")

    def test_reports_different_problem_layers(self):
        result = compare_reports(report("dns"), report("tls"))

        self.assertEqual(
            result["comparison"]["classification"],
            "different_results",
        )
        self.assertEqual(len(result["comparison"]["layers"]), 5)


if __name__ == "__main__":
    unittest.main()
