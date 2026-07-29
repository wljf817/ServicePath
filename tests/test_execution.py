import unittest
from unittest.mock import patch

from diagnostics.execution import ExecutionError, run_selected_diagnostics


def settings(role, remote_url=""):
    return {
        "instance_role": role,
        "remote_service_url": remote_url,
    }


class ExecutionTests(unittest.TestCase):
    @patch("diagnostics.execution.run_diagnostics")
    def test_remote_server_runs_remote_test_on_current_server(self, run_diagnostics):
        run_diagnostics.return_value = {"mode": "remote"}

        report = run_selected_diagnostics(
            "example.com",
            "remote",
            settings("remote_server"),
        )

        self.assertEqual(report["mode"], "remote")
        run_diagnostics.assert_called_once_with("example.com", mode="remote")

    def test_remote_server_rejects_local_test(self):
        with self.assertRaises(ExecutionError):
            run_selected_diagnostics(
                "example.com",
                "local",
                settings("remote_server"),
            )

    @patch("diagnostics.execution.run_diagnostics")
    def test_local_device_runs_local_test_on_current_device(self, run_diagnostics):
        run_diagnostics.return_value = {"mode": "local"}

        report = run_selected_diagnostics(
            "example.com",
            "local",
            settings("local_device"),
        )

        self.assertEqual(report["mode"], "local")
        run_diagnostics.assert_called_once_with("example.com", mode="local")

    @patch("diagnostics.execution.run_remote_diagnostics")
    def test_local_device_uses_configured_remote_url(self, run_remote):
        run_remote.return_value = {"mode": "remote"}

        run_selected_diagnostics(
            "example.com",
            "remote",
            settings("local_device", "https://servicepath.example"),
        )

        run_remote.assert_called_once_with(
            "example.com",
            service_url="https://servicepath.example",
        )

    @patch("diagnostics.execution.compare_reports")
    @patch("diagnostics.execution.run_diagnostics")
    @patch("diagnostics.execution.run_remote_diagnostics")
    def test_local_device_compares_both_reports(
        self,
        run_remote,
        run_diagnostics,
        compare_reports,
    ):
        local_report = {"mode": "local"}
        remote_report = {"mode": "remote"}
        combined_report = {"mode": "compare"}
        run_diagnostics.return_value = local_report
        run_remote.return_value = remote_report
        compare_reports.return_value = combined_report

        report = run_selected_diagnostics(
            "example.com",
            "compare",
            settings("local_device", "https://servicepath.example"),
        )

        self.assertEqual(report, combined_report)
        compare_reports.assert_called_once_with(local_report, remote_report)


if __name__ == "__main__":
    unittest.main()
