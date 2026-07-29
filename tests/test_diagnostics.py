import unittest
from unittest.mock import patch

from diagnostics.result import make_result
from diagnostics.runner import run_diagnostics


def result(key, status="passed", details=None):
    names = {
        "client": "Client Network",
        "dns": "DNS",
        "tcp": "TCP",
        "tls": "TLS",
        "http": "HTTP",
    }
    return make_result(key, names[key], status, "Test result", details=details)


class DiagnosticRunnerTests(unittest.TestCase):
    @patch("diagnostics.runner.check_http")
    @patch("diagnostics.runner.check_tls")
    @patch("diagnostics.runner.check_tcp")
    @patch("diagnostics.runner.check_dns")
    @patch("diagnostics.runner.check_client_network")
    @patch("diagnostics.runner.check_traceroute")
    def test_runs_all_five_layers(self, traceroute, network, dns, tcp, tls, http):
        network.return_value = result("client")
        dns.return_value = result("dns", details={"addresses": ["93.184.216.34"]})
        tcp.return_value = result(
            "tcp",
            details={"ports": {"443": {"status": "passed"}}},
        )
        tls.return_value = result("tls")
        http.return_value = result("http")
        traceroute.return_value = make_result(
            "traceroute",
            "Traceroute",
            "passed",
            "Trace passed",
        )

        report = run_diagnostics("example.com")

        self.assertEqual(len(report["layers"]), 5)
        self.assertEqual(report["status"], "passed")
        self.assertIsNone(report["first_problem"])
        self.assertEqual(report["traceroute"]["status"], "passed")

    @patch("diagnostics.runner.check_dns")
    @patch("diagnostics.runner.check_client_network")
    def test_skips_dependent_layers_after_dns_error(self, network, dns):
        network.return_value = result("client")
        dns.return_value = result("dns", "error", {"addresses": []})

        report = run_diagnostics("example.com")

        self.assertEqual(report["first_problem"], "dns")
        self.assertEqual(
            [layer["status"] for layer in report["layers"]],
            ["passed", "error", "skipped", "skipped", "skipped"],
        )
        self.assertEqual(report["traceroute"]["status"], "skipped")

    @patch("diagnostics.runner.check_http")
    @patch("diagnostics.runner.check_tls")
    @patch("diagnostics.runner.check_tcp")
    @patch("diagnostics.runner.check_dns")
    @patch("diagnostics.runner.check_client_network")
    @patch("diagnostics.runner.check_traceroute")
    def test_reports_first_warning_when_no_errors(
        self,
        traceroute,
        network,
        dns,
        tcp,
        tls,
        http,
    ):
        network.return_value = result("client", "warning")
        dns.return_value = result("dns", details={"addresses": ["93.184.216.34"]})
        tcp.return_value = result(
            "tcp",
            details={"ports": {"443": {"status": "passed"}}},
        )
        tls.return_value = result("tls")
        http.return_value = result("http")
        traceroute.return_value = make_result(
            "traceroute",
            "Traceroute",
            "passed",
            "Trace passed",
        )

        report = run_diagnostics("example.com")

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["first_problem"], "client")


if __name__ == "__main__":
    unittest.main()
