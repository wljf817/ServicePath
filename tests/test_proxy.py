import unittest
from unittest.mock import patch

from diagnostics.dns import check_dns
from diagnostics.http import check_http
from diagnostics.network import check_client_network
from diagnostics.result import make_result
from diagnostics.runner import run_diagnostics


TARGET = {
    "hostname": "example.com",
    "scheme": "https",
    "port": None,
    "url": "https://example.com/",
}


class ProxyDiagnosticTests(unittest.TestCase):
    @patch("diagnostics.dns.resolve_addresses")
    def test_dns_rejects_fake_ip_by_default(self, resolve_addresses):
        resolve_addresses.return_value = (["198.18.0.10"], [])

        result = check_dns(TARGET)

        self.assertEqual(result["status"], "error")
        self.assertFalse(result["proxy_fake_ip"])

    @patch("diagnostics.dns.resolve_addresses")
    def test_dns_warns_when_proxy_fake_ip_is_allowed(self, resolve_addresses):
        resolve_addresses.return_value = (["198.18.0.10"], [])

        result = check_dns(TARGET, allow_proxy_fake_ip=True)

        self.assertEqual(result["status"], "warning")
        self.assertTrue(result["proxy_fake_ip"])
        self.assertIn("Fake-IP", result["summary"])

    @patch("diagnostics.network.getproxies")
    @patch("diagnostics.network._outbound_address")
    def test_client_network_marks_system_proxy(self, outbound_address, getproxies):
        outbound_address.side_effect = ["192.0.2.10", None]
        getproxies.return_value = {"http": "http://127.0.0.1:7890"}

        result = check_client_network()

        self.assertEqual(result["status"], "warning")
        self.assertTrue(result["proxy_detected"])
        self.assertEqual(result["details"]["Proxy"], "http")

    @patch("diagnostics.runner.check_http")
    @patch("diagnostics.runner.check_tls")
    @patch("diagnostics.runner.check_tcp")
    @patch("diagnostics.runner.check_dns")
    @patch("diagnostics.runner.check_client_network")
    def test_local_test_uses_proxy_for_fake_ip(
        self,
        client_network,
        dns,
        tcp,
        tls,
        http,
    ):
        network_result = make_result(
            "client",
            "Client Network",
            "warning",
            "Proxy detected.",
        )
        network_result["proxy_detected"] = True
        client_network.return_value = network_result

        dns_result = make_result(
            "dns",
            "DNS",
            "warning",
            "Fake-IP detected.",
            details={"addresses": ["198.18.0.10"]},
        )
        dns_result["proxy_fake_ip"] = True
        dns.return_value = dns_result
        http.return_value = make_result(
            "http",
            "HTTP",
            "passed",
            "HTTP passed.",
        )

        report = run_diagnostics("example.com", mode="local")

        self.assertEqual(
            [layer["status"] for layer in report["layers"]],
            ["warning", "warning", "skipped", "skipped", "passed"],
        )
        tcp.assert_not_called()
        tls.assert_not_called()
        http.assert_called_once_with(
            report["target"],
            use_proxy=True,
            allow_proxy_fake_ip=True,
        )

    @patch("diagnostics.runner.check_dns")
    @patch("diagnostics.runner.check_client_network")
    def test_remote_test_does_not_allow_proxy_fake_ip(self, client_network, dns):
        network_result = make_result(
            "client",
            "Client Network",
            "warning",
            "Proxy detected.",
        )
        network_result["proxy_detected"] = True
        client_network.return_value = network_result
        dns.return_value = make_result(
            "dns",
            "DNS",
            "error",
            "Reserved address.",
            details={"addresses": []},
        )

        run_diagnostics("example.com", mode="remote")

        dns.assert_called_once()
        self.assertFalse(dns.call_args.kwargs["allow_proxy_fake_ip"])

    @patch("diagnostics.http.resolve_addresses")
    @patch("diagnostics.http.requests.Session")
    def test_http_uses_system_proxy(self, session_class, resolve_addresses):
        resolve_addresses.return_value = (["198.18.0.10"], [])
        session = session_class.return_value
        response = session.get.return_value
        response.is_redirect = False
        response.is_permanent_redirect = False
        response.iter_content.return_value = [b"<title>Example</title>"]
        response.encoding = "utf-8"
        response.status_code = 200
        response.headers = {}

        result = check_http(
            TARGET,
            use_proxy=True,
            allow_proxy_fake_ip=True,
        )

        self.assertEqual(result["status"], "passed")
        self.assertTrue(session.trust_env)
        self.assertEqual(result["details"]["System proxy"], "Used")


if __name__ == "__main__":
    unittest.main()
