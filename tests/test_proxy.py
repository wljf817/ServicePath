import unittest
from unittest.mock import patch

from diagnostics.agent_tools import DiagnosticContext
from diagnostics.dns import check_dns
from diagnostics.http import check_http
from diagnostics.network import check_client_network
from diagnostics.result import make_result


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

    @patch("diagnostics.agent_tools.check_http")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    def test_agent_context_uses_proxy_for_fake_ip(
        self,
        client_network,
        dns,
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

        context = DiagnosticContext(TARGET, mode="local")
        result = context.inspect_http()

        self.assertEqual(result["status"], "passed")
        self.assertEqual(set(context.results), {"client", "dns", "http"})
        http.assert_called_once_with(
            TARGET,
            use_proxy=True,
            allow_proxy_fake_ip=True,
        )

    @patch("diagnostics.agent_tools.check_http")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    def test_agent_context_uses_detected_proxy_for_public_dns(
        self,
        client_network,
        dns,
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
            "passed",
            "Resolved one public address.",
            details={"addresses": ["93.184.216.34"]},
        )
        dns_result["proxy_fake_ip"] = False
        dns.return_value = dns_result
        http.return_value = make_result(
            "http",
            "HTTP",
            "passed",
            "HTTP passed.",
        )

        context = DiagnosticContext(TARGET, mode="remote")
        context.inspect_http()

        self.assertTrue(dns.call_args.kwargs["allow_proxy_fake_ip"])
        http.assert_called_once_with(
            TARGET,
            use_proxy=True,
        )

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
