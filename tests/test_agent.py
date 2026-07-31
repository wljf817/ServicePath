import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics.agent import (
    AgentConfigurationError,
    AgentRunError,
    run_agent_diagnostics,
)
from diagnostics.agent_models import AgentDiagnosis
from diagnostics.agent_tools import AGENT_TOOLS, DiagnosticContext
from diagnostics.result import make_result
from diagnostics.target import TargetError


def network_result():
    result = make_result(
        "client",
        "Client Network",
        "passed",
        "A network route is available.",
    )
    result["proxy_detected"] = False
    return result


def dns_result():
    result = make_result(
        "dns",
        "DNS",
        "passed",
        "Resolved one public address.",
        details={"addresses": ["93.184.216.34"]},
    )
    result["proxy_fake_ip"] = False
    return result


def many_address_dns_result():
    result = make_result(
        "dns",
        "DNS",
        "passed",
        "Resolved several public addresses.",
        details={
            "A records": [
                "93.184.216.34",
                "93.184.216.35",
                "93.184.216.36",
            ],
            "AAAA records": [
                "2606:2800:220:1:248:1893:25c8:1946",
                "2606:2800:220:1:248:1893:25c8:1947",
                "2606:2800:220:1:248:1893:25c8:1948",
            ],
            "addresses": [],
        },
    )
    result["proxy_fake_ip"] = False
    return result


def diagnosis(verdict="reachable", failure_stage=None):
    return AgentDiagnosis(
        verdict=verdict,
        headline="The target is reachable",
        summary="The selected checks completed successfully.",
        failure_stage=failure_stage,
        confidence="high",
        evidence=["HTTP returned 200."],
        likely_causes=[],
        actions=[],
    )


def http_result(status="passed", status_code=200):
    return make_result(
        "http",
        "HTTP",
        status,
        f"HTTP returned {status_code}.",
        details={"Status code": status_code},
    )


class AgentDiagnosticTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_requires_api_key_after_validating_target(self):
        with self.assertRaises(AgentConfigurationError):
            run_agent_diagnostics("example.com")

        with self.assertRaises(TargetError):
            run_agent_diagnostics("http://127.0.0.1")

    def test_agent_tools_cannot_accept_or_change_the_target(self):
        self.assertEqual(
            [tool.name for tool in AGENT_TOOLS],
            [
                "inspect_client_network",
                "inspect_dns",
                "inspect_tcp",
                "inspect_tls",
                "inspect_http",
                "inspect_traceroute",
            ],
        )
        for tool in AGENT_TOOLS:
            self.assertEqual(tool.params_json_schema.get("properties"), {})

    @patch("diagnostics.agent_tools.check_http")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-test"},
        clear=True,
    )
    def test_agent_builds_report_from_locked_tool_evidence(
        self,
        run_sync,
        check_network,
        check_dns,
        check_http,
    ):
        check_network.return_value = network_result()
        check_dns.return_value = dns_result()
        check_http.return_value = http_result()

        def execute_agent(agent, input, context, max_turns, run_config):
            self.assertEqual(context.target["url"], "https://example.com/")
            self.assertNotIn("example.com", [tool.name for tool in agent.tools])
            self.assertIs(agent.output_type, AgentDiagnosis)
            self.assertEqual(agent.model_settings.tool_choice, "required")
            self.assertFalse(agent.model_settings.parallel_tool_calls)
            self.assertTrue(run_config.model_provider._use_responses)
            self.assertEqual(max_turns, 8)
            self.assertFalse(run_config.trace_include_sensitive_data)
            self.assertNotIn(context.target["url"], input)
            context.inspect_http()
            return SimpleNamespace(
                final_output=diagnosis().model_copy(
                    update={"evidence": ["Invented model evidence."]}
                ),
                context_wrapper=SimpleNamespace(
                    usage=SimpleNamespace(
                        requests=2,
                        input_tokens=120,
                        output_tokens=40,
                        total_tokens=160,
                    )
                ),
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com", mode="remote")

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["analysis"]["source"], "agent")
        self.assertEqual(report["analysis"]["model"], "gpt-test")
        self.assertEqual(
            [layer["key"] for layer in report["layers"]],
            ["client", "dns", "http"],
        )
        self.assertEqual(report["agent"]["checks_used"], 3)
        self.assertEqual(report["agent"]["max_checks"], 6)
        self.assertEqual(report["agent"]["model_calls"], 2)
        self.assertEqual(report["agent"]["token_usage"]["total"], 160)
        self.assertEqual(
            report["analysis"]["evidence"],
            [
                "Client Network: A network route is available.",
                "DNS: Resolved one public address.",
                "HTTP: HTTP returned 200.",
            ],
        )
        self.assertNotIn("Invented model evidence.", str(report))
        run_sync.assert_called_once()

    @patch("diagnostics.agent_tools.check_tcp")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    def test_tool_context_runs_dependencies_once(
        self,
        check_network,
        check_dns,
        check_tcp,
    ):
        check_network.return_value = network_result()
        check_dns.return_value = dns_result()
        check_tcp.return_value = make_result(
            "tcp",
            "TCP",
            "passed",
            "TCP connected.",
        )
        context = DiagnosticContext(
            target={
                "url": "https://example.com/",
                "hostname": "example.com",
                "scheme": "https",
                "port": None,
            },
            mode="remote",
        )

        first = context.inspect_tcp()
        second = context.inspect_tcp()

        self.assertIs(first, second)
        self.assertEqual(context.checks_used, 3)
        check_network.assert_called_once_with()
        check_dns.assert_called_once()
        check_tcp.assert_called_once()

    @patch("diagnostics.agent_tools.check_tcp")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    def test_tcp_attempts_use_a_bounded_dual_stack_address_sample(
        self,
        check_network,
        check_dns,
        check_tcp,
    ):
        check_network.return_value = network_result()
        check_dns.return_value = many_address_dns_result()
        check_tcp.return_value = make_result("tcp", "TCP", "passed", "Connected.")
        context = DiagnosticContext(
            target={
                "url": "https://example.com/",
                "hostname": "example.com",
                "scheme": "https",
                "port": None,
            },
            mode="remote",
        )

        context.inspect_tcp()

        attempted_addresses = check_tcp.call_args.args[1]
        self.assertEqual(len(attempted_addresses), 4)
        self.assertEqual(
            attempted_addresses,
            [
                "93.184.216.34",
                "93.184.216.35",
                "2606:2800:220:1:248:1893:25c8:1946",
                "2606:2800:220:1:248:1893:25c8:1947",
            ],
        )

    @patch("diagnostics.agent_tools.check_client_network")
    def test_tool_context_enforces_check_budget(self, check_network):
        check_network.return_value = network_result()
        context = DiagnosticContext(
            target={
                "url": "https://example.com/",
                "hostname": "example.com",
                "scheme": "https",
                "port": None,
            },
            mode="remote",
            max_checks=1,
        )

        result = context.inspect_dns()

        self.assertEqual(result["status"], "skipped")
        self.assertIn("budget", result["summary"])
        self.assertEqual(context.checks_used, 1)

    def test_tool_payload_records_agent_selection(self):
        context = DiagnosticContext(
            target={
                "url": "https://example.com/",
                "hostname": "example.com",
                "scheme": "https",
                "port": None,
            },
            mode="remote",
        )
        result = network_result()

        payload = context.tool_payload("client", result)

        self.assertEqual(payload["locked_target"], "https://example.com/")
        self.assertEqual(context.requested_tools[0]["tool"], "client")

    @patch("diagnostics.agent_tools.check_tls")
    @patch("diagnostics.agent_tools.check_tcp")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    def test_http_target_skips_tls_and_its_dependencies(
        self,
        check_network,
        check_dns,
        check_tcp,
        check_tls,
    ):
        context = DiagnosticContext(
            target={
                "url": "http://example.com/",
                "hostname": "example.com",
                "scheme": "http",
                "port": None,
            },
            mode="local",
        )

        result = context.inspect_tls()

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(context.checks_used, 1)
        check_network.assert_not_called()
        check_dns.assert_not_called()
        check_tcp.assert_not_called()
        check_tls.assert_not_called()

    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_unsupported_reachable_verdict_uses_fallback(
        self,
        run_sync,
        check_network,
    ):
        check_network.return_value = network_result()

        def execute_agent(agent, input, context, max_turns, run_config):
            context.inspect_client()
            return SimpleNamespace(final_output=diagnosis())

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["analysis"]["verdict"], "inconclusive")
        self.assertEqual(report["agent"]["completion"], "fallback")

    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_unsupported_failure_stage_uses_fallback(
        self,
        run_sync,
        check_network,
        check_dns,
    ):
        check_network.return_value = network_result()
        check_dns.return_value = dns_result()

        def execute_agent(agent, input, context, max_turns, run_config):
            context.inspect_dns()
            return SimpleNamespace(
                final_output=diagnosis("unreachable", "dns")
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["analysis"]["verdict"], "inconclusive")
        self.assertIsNone(report["analysis"]["failure_stage"])
        self.assertEqual(report["agent"]["completion"], "fallback")

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_clear_errors_reject_degraded_verdicts(self, run_sync):
        cases = [
            (
                "dns",
                make_result("dns", "DNS", "error", "DNS failed."),
                "dns",
            ),
            (
                "tcp",
                make_result("tcp", "TCP", "error", "TCP failed."),
                "tcp",
            ),
            (
                "tls",
                make_result("tls", "TLS", "error", "TLS failed."),
                "tls",
            ),
            (
                "http",
                make_result("http", "HTTP", "error", "HTTP failed."),
                "http",
            ),
            (
                "http",
                http_result("error", 503),
                "application",
            ),
        ]

        for key, tool_result, stage in cases:
            with self.subTest(key=key, stage=stage):
                def execute_agent(
                    agent,
                    input,
                    context,
                    max_turns,
                    run_config,
                ):
                    context.results[key] = tool_result
                    return SimpleNamespace(
                        final_output=diagnosis("degraded", stage)
                    )

                run_sync.side_effect = execute_agent
                report = run_agent_diagnostics("example.com")

                self.assertEqual(report["analysis"]["verdict"], "inconclusive")
                self.assertEqual(report["analysis"]["failure_stage"], stage)
                self.assertEqual(report["agent"]["completion"], "fallback")

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_inconclusive_error_verdict_requires_matching_stage(self, run_sync):
        dns_error = make_result("dns", "DNS", "error", "DNS failed.")

        for reported_stage in (None, "tls"):
            with self.subTest(reported_stage=reported_stage):
                def execute_agent(
                    agent,
                    input,
                    context,
                    max_turns,
                    run_config,
                ):
                    context.results["dns"] = dns_error
                    return SimpleNamespace(
                        final_output=diagnosis("inconclusive", reported_stage)
                    )

                run_sync.side_effect = execute_agent
                report = run_agent_diagnostics("example.com")

                self.assertEqual(report["analysis"]["failure_stage"], "dns")
                self.assertEqual(report["agent"]["completion"], "fallback")

        def execute_supported(agent, input, context, max_turns, run_config):
            context.results["dns"] = dns_error
            return SimpleNamespace(
                final_output=diagnosis("inconclusive", "dns")
            )

        run_sync.side_effect = execute_supported
        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["analysis"]["failure_stage"], "dns")
        self.assertEqual(report["agent"]["completion"], "complete")

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_traceroute_error_does_not_support_unreachable(self, run_sync):
        def execute_agent(agent, input, context, max_turns, run_config):
            context.results["traceroute"] = make_result(
                "traceroute",
                "Traceroute",
                "error",
                "Route probe failed.",
            )
            return SimpleNamespace(
                final_output=diagnosis("unreachable", "route")
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["analysis"]["verdict"], "inconclusive")
        self.assertIsNone(report["analysis"]["failure_stage"])
        self.assertEqual(report["agent"]["completion"], "fallback")

    @patch("diagnostics.agent_tools.check_http")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_http_4xx_supports_degraded_application_verdict(
        self,
        run_sync,
        check_network,
        check_dns,
        check_http,
    ):
        check_network.return_value = network_result()
        check_dns.return_value = dns_result()
        check_http.return_value = http_result("warning", 404)

        def execute_agent(agent, input, context, max_turns, run_config):
            context.inspect_http()
            return SimpleNamespace(
                final_output=diagnosis("degraded", "application")
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["analysis"]["failure_stage"], "application")
        self.assertEqual(report["agent"]["completion"], "complete")

    @patch("diagnostics.agent_tools.check_http")
    @patch("diagnostics.agent_tools.check_dns")
    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_http_5xx_supports_unreachable_application_verdict(
        self,
        run_sync,
        check_network,
        check_dns,
        check_http,
    ):
        check_network.return_value = network_result()
        check_dns.return_value = dns_result()
        check_http.return_value = http_result("error", 503)

        def execute_agent(agent, input, context, max_turns, run_config):
            context.inspect_http()
            return SimpleNamespace(
                final_output=diagnosis("unreachable", "application")
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["status"], "error")
        self.assertEqual(report["analysis"]["failure_stage"], "application")
        self.assertEqual(report["agent"]["completion"], "complete")

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_agent_failure_returns_safe_error(self, run_sync):
        from agents import ModelBehaviorError

        run_sync.side_effect = ModelBehaviorError("private provider detail")

        with self.assertRaisesRegex(AgentRunError, "could not complete") as raised:
            run_agent_diagnostics("example.com")

        self.assertNotIn("private provider detail", str(raised.exception))

    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_agent_failure_preserves_evidence_collected_before_failure(
        self,
        run_sync,
        check_network,
    ):
        from agents import ModelBehaviorError

        check_network.return_value = network_result()

        def fail_after_check(agent, input, context, max_turns, run_config):
            context.inspect_client()
            raise ModelBehaviorError("private provider detail")

        run_sync.side_effect = fail_after_check

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["analysis"]["completion"], "fallback")
        self.assertEqual(report["agent"]["completion"], "fallback")
        self.assertEqual(report["layers"][0]["key"], "client")
        self.assertNotIn("private provider detail", str(report))

    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "http://127.0.0.1:8000/v1/",
        },
        clear=True,
    )
    def test_agent_uses_custom_api_base_url(
        self,
        run_sync,
        check_network,
    ):
        check_network.return_value = network_result()

        def execute_agent(agent, input, context, max_turns, run_config):
            self.assertEqual(
                run_config.model_provider._stored_base_url,
                "http://127.0.0.1:8000/v1",
            )
            self.assertTrue(run_config.tracing_disabled)
            self.assertFalse(run_config.model_provider._use_responses)
            self.assertIsNone(agent.output_type)
            self.assertEqual(agent.model_settings.tool_choice, "auto")
            self.assertFalse(agent.model_settings.parallel_tool_calls)
            self.assertEqual(
                agent.model_settings.extra_args,
                {"response_format": {"type": "json_object"}},
            )
            self.assertIn("valid JSON object", input)
            self.assertNotIn(context.target["url"], input)
            context.inspect_client()
            return SimpleNamespace(
                final_output=diagnosis(verdict="inconclusive").model_dump_json()
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["agent"]["completion"], "complete")
        self.assertEqual(report["agent"]["api_mode"], "chat_completions")

    @patch("diagnostics.agent_tools.check_client_network")
    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "http://127.0.0.1:8000/v1",
            "OPENAI_API_MODE": "responses",
        },
        clear=True,
    )
    def test_custom_api_can_explicitly_use_responses(
        self,
        run_sync,
        check_network,
    ):
        check_network.return_value = network_result()

        def execute_agent(agent, input, context, max_turns, run_config):
            self.assertTrue(run_config.model_provider._use_responses)
            self.assertIs(agent.output_type, AgentDiagnosis)
            self.assertFalse(agent.model_settings.parallel_tool_calls)
            self.assertIsNone(agent.model_settings.extra_args)
            context.inspect_client()
            return SimpleNamespace(final_output=diagnosis(verdict="inconclusive"))

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["agent"]["api_mode"], "responses")

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "ftp://invalid.example/v1",
        },
        clear=True,
    )
    def test_agent_rejects_invalid_custom_api_base_url(self, run_sync):
        with self.assertRaisesRegex(AgentConfigurationError, "must use http"):
            run_agent_diagnostics("example.com")

        run_sync.assert_not_called()

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_API_MODE": "legacy_completions",
        },
        clear=True,
    )
    def test_agent_rejects_invalid_api_mode(self, run_sync):
        with self.assertRaisesRegex(AgentConfigurationError, "protocol"):
            run_agent_diagnostics("example.com")

        run_sync.assert_not_called()

    @patch("diagnostics.agent.Runner.run_sync")
    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://api.deepseek.com",
            "OPENAI_MODEL": "deepseek-chat",
        },
        clear=True,
    )
    def test_agent_does_not_hardcode_provider_model_names(self, run_sync):
        def execute_agent(agent, input, context, max_turns, run_config):
            self.assertEqual(agent.model, "deepseek-chat")
            context.results["client"] = network_result()
            return SimpleNamespace(
                final_output=diagnosis(verdict="inconclusive").model_dump_json()
            )

        run_sync.side_effect = execute_agent

        report = run_agent_diagnostics("example.com")

        self.assertEqual(report["agent"]["model"], "deepseek-chat")
        run_sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
