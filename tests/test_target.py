import unittest

from diagnostics.target import TargetError, normalize_target, validate_public_addresses


class NormalizeTargetTests(unittest.TestCase):
    def test_adds_https_to_bare_domain(self):
        target = normalize_target("Example.COM")

        self.assertEqual(target["hostname"], "example.com")
        self.assertEqual(target["url"], "https://example.com/")

    def test_preserves_path_query_and_port(self):
        target = normalize_target("http://example.com:8080/status?full=1#top")

        self.assertEqual(target["port"], 8080)
        self.assertEqual(target["url"], "http://example.com:8080/status?full=1")

    def test_rejects_unsupported_scheme(self):
        with self.assertRaises(TargetError):
            normalize_target("ftp://example.com")

    def test_rejects_credentials(self):
        with self.assertRaises(TargetError):
            normalize_target("https://user:pass@example.com")

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
        validate_public_addresses(["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"])


if __name__ == "__main__":
    unittest.main()
