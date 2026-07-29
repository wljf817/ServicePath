import unittest
from unittest.mock import patch

from diagnostics.dns import check_dns
from diagnostics.network import check_client_network


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


if __name__ == "__main__":
    unittest.main()
