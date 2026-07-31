import unittest
from unittest.mock import patch

from diagnostics.target import (
    TargetError,
    effective_port,
    normalize_target,
    validate_public_addresses,
)
from diagnostics.tcp import check_tcp


class NormalizeTargetTests(unittest.TestCase):
    def test_adds_https_to_bare_domain(self):
        target = normalize_target("Example.COM")

        self.assertEqual(target["hostname"], "example.com")
        self.assertEqual(target["url"], "https://example.com/")

    def test_preserves_path_query_and_port(self):
        target = normalize_target("http://example.com:8080/status?full=1#top")

        self.assertEqual(target["port"], 8080)
        self.assertEqual(target["url"], "http://example.com:8080/status?full=1")

    def test_normalizes_an_international_domain(self):
        target = normalize_target("https://bücher.example")

        self.assertEqual(target["hostname"], "xn--bcher-kva.example")
        self.assertEqual(target["url"], "https://xn--bcher-kva.example/")

    def test_uses_the_port_for_the_target_scheme(self):
        self.assertEqual(effective_port(normalize_target("http://example.com")), 80)
        self.assertEqual(effective_port(normalize_target("https://example.com")), 443)
        self.assertEqual(
            effective_port(normalize_target("https://example.com:8443")),
            8443,
        )

    @patch("diagnostics.tcp._connect", return_value=(True, None))
    def test_tcp_checks_only_the_effective_target_port(self, connect):
        result = check_tcp(
            normalize_target("http://example.com"),
            ["93.184.216.34"],
        )

        self.assertEqual(set(result["details"]["ports"]), {"80"})
        connect.assert_called_once_with("93.184.216.34", 80, 3)

    def test_rejects_unsupported_scheme(self):
        with self.assertRaises(TargetError):
            normalize_target("ftp://example.com")

    def test_rejects_credentials(self):
        with self.assertRaises(TargetError):
            normalize_target("https://user:pass@example.com")

    def test_rejects_invalid_hostname_syntax(self):
        invalid_targets = [
            "bad_name.example",
            "-bad.example",
            "bad-.example",
            "example..com",
            "xn--.example",
        ]

        for value in invalid_targets:
            with self.subTest(value=value):
                with self.assertRaises(TargetError):
                    normalize_target(value)

    def test_rejects_ambiguous_or_invalid_url_characters(self):
        invalid_targets = [
            "https://example.com\\@other.example",
            "https://example.com/path with space",
            "https://example.com\n.other.example",
        ]

        for value in invalid_targets:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TargetError, "invalid"):
                    normalize_target(value)

    def test_rejects_invalid_ports(self):
        for value in ("https://example.com:0", "https://example.com:"):
            with self.subTest(value=value):
                with self.assertRaises(TargetError):
                    normalize_target(value)

    def test_rejects_local_targets(self):
        blocked = ["localhost", "printer.local", "127.0.0.1", "10.0.0.2", "::1"]

        for value in blocked:
            with self.subTest(value=value):
                with self.assertRaises(TargetError):
                    normalize_target(value)

    def test_rejects_private_dns_results(self):
        with self.assertRaises(TargetError):
            validate_public_addresses(["93.184.216.34", "192.168.1.10"])

    def test_accepts_public_dns_results(self):
        validate_public_addresses(
            ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"]
        )

    def test_rejects_proxy_fake_ip_by_default(self):
        with self.assertRaises(TargetError):
            validate_public_addresses(["198.18.0.10"])

    def test_allows_proxy_fake_ip_when_requested(self):
        validate_public_addresses(["198.18.0.10"], allow_proxy_fake_ip=True)


if __name__ == "__main__":
    unittest.main()
