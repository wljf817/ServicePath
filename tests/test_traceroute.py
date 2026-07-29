import subprocess
import unittest
from unittest.mock import Mock, patch

from diagnostics.traceroute import check_traceroute


class TracerouteTests(unittest.TestCase):
    @patch("diagnostics.traceroute.subprocess.run")
    @patch("diagnostics.traceroute.shutil.which")
    @patch("diagnostics.traceroute.platform.system", return_value="Darwin")
    def test_runs_macos_traceroute(self, system, which, run):
        which.return_value = "/usr/sbin/traceroute"
        run.return_value = Mock(
            returncode=0,
            stdout="traceroute to 93.184.216.34\n1  192.0.2.1  2 ms",
            stderr="",
        )

        result = check_traceroute(["93.184.216.34"])

        self.assertEqual(result["status"], "passed")
        self.assertIn("192.0.2.1", result["details"]["Raw output"])
        command = run.call_args.args[0]
        self.assertEqual(command[-1], "93.184.216.34")
        self.assertNotIn("shell", run.call_args.kwargs)

    @patch("diagnostics.traceroute.subprocess.run")
    @patch("diagnostics.traceroute.shutil.which")
    @patch("diagnostics.traceroute.platform.system", return_value="Windows")
    def test_runs_windows_tracert(self, system, which, run):
        which.return_value = "C:\\Windows\\System32\\tracert.exe"
        run.return_value = Mock(returncode=0, stdout="Trace complete.", stderr="")

        result = check_traceroute(["93.184.216.34"])

        self.assertEqual(result["status"], "passed")
        command = run.call_args.args[0]
        self.assertIn("-d", command)
        self.assertIn("-h", command)

    @patch("diagnostics.traceroute.shutil.which", return_value=None)
    def test_skips_when_command_is_missing(self, which):
        result = check_traceroute(["93.184.216.34"])

        self.assertEqual(result["status"], "skipped")

    @patch("diagnostics.traceroute.subprocess.run")
    @patch("diagnostics.traceroute.shutil.which")
    def test_warns_for_unanswered_hop(self, which, run):
        which.return_value = "/usr/sbin/traceroute"
        run.return_value = Mock(returncode=0, stdout="1  *", stderr="")

        result = check_traceroute(["93.184.216.34"])

        self.assertEqual(result["status"], "warning")

    @patch("diagnostics.traceroute.subprocess.run")
    @patch("diagnostics.traceroute.shutil.which")
    def test_returns_partial_output_after_timeout(self, which, run):
        which.return_value = "/usr/sbin/traceroute"
        run.side_effect = subprocess.TimeoutExpired(
            cmd="traceroute",
            timeout=12,
            output="1  192.0.2.1",
        )

        result = check_traceroute(["93.184.216.34"])

        self.assertEqual(result["status"], "warning")
        self.assertIn("192.0.2.1", result["details"]["Raw output"])


if __name__ == "__main__":
    unittest.main()
