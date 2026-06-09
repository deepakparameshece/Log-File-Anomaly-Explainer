"""
Tests for src/agent.py — tool-using agent loop (mocked to avoid live API calls).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agent import LogAnalysisAgent, AGENT_SYSTEM_INSTRUCTION, TOOL_DECLARATIONS


# ---------------------------------------------------------------------------
# Mock LLM responses
# ---------------------------------------------------------------------------
MOCK_FINAL_RESPONSE = """\
## Root Cause Analysis
The database connection pool exhausted all retry attempts.

## Probable Cause
The PostgreSQL instance was unreachable due to max connection limits.

## Remediation Steps
1. Check database status with systemctl.
2. Verify network connectivity.
3. Increase connection pool limits.

## Confidence
HIGH
"""


class TestAgentInit:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
            LogAnalysisAgent(api_key=None)

    @patch("src.agent.genai.Client")
    def test_initialises_with_key(self, mock_client_cls):
        agent = LogAnalysisAgent(api_key="test-key")
        mock_client_cls.assert_called_once_with(api_key="test-key")
        assert agent.api_key == "test-key"


class TestAgentInvestigate:
    @patch("src.agent.genai.Client")
    def test_direct_response_no_tool_calls(self, mock_client_cls):
        """Agent returns immediately when LLM gives a final text response."""
        # Mock: LLM returns text with no function calls
        mock_part = MagicMock()
        mock_part.function_call = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_response.text = MOCK_FINAL_RESPONSE
        mock_response.usage_metadata.prompt_token_count = 256

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client_instance

        agent = LogAnalysisAgent(api_key="fake-key")
        result = agent.investigate("/tmp/test.log")

        assert result["confidence"] == "HIGH"
        assert "database" in result["root_cause"].lower()
        assert result["iterations"] == 1
        assert result["tool_calls_log"] == []

    @patch("src.agent.TOOL_REGISTRY", {
        "scan_all_anomalies": lambda **kw: {"status": "anomalies_found", "anomaly_count": 2},
    })
    @patch("src.agent.genai.Client")
    def test_agent_loop_with_tool_call(self, mock_client_cls):
        """Agent executes a tool call, sends result back, then gets final response."""
        # --- First response: LLM calls scan_all_anomalies ---
        mock_fn_call = MagicMock()
        mock_fn_call.name = "scan_all_anomalies"
        mock_fn_call.args = {"file_path": "/tmp/test.log"}

        mock_part_with_call = MagicMock()
        mock_part_with_call.function_call = mock_fn_call

        mock_candidate_1 = MagicMock()
        mock_candidate_1.content.parts = [mock_part_with_call]

        mock_response_1 = MagicMock()
        mock_response_1.candidates = [mock_candidate_1]

        # --- Second response: LLM returns final text ---
        mock_part_text = MagicMock()
        mock_part_text.function_call = None

        mock_candidate_2 = MagicMock()
        mock_candidate_2.content.parts = [mock_part_text]

        mock_response_2 = MagicMock()
        mock_response_2.candidates = [mock_candidate_2]
        mock_response_2.text = MOCK_FINAL_RESPONSE
        mock_response_2.usage_metadata.prompt_token_count = 512

        # Wire up generate_content to return responses in sequence
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = [
            mock_response_1,
            mock_response_2,
        ]
        mock_client_cls.return_value = mock_client_instance

        agent = LogAnalysisAgent(api_key="fake-key")
        result = agent.investigate("/tmp/test.log")

        assert result["iterations"] == 2
        assert len(result["tool_calls_log"]) == 1
        assert result["tool_calls_log"][0]["tool"] == "scan_all_anomalies"
        assert result["confidence"] == "HIGH"

    @patch("src.agent.genai.Client")
    def test_on_tool_call_callback_invoked(self, mock_client_cls):
        """Verify the on_tool_call callback is called during tool execution."""
        # Setup: one tool call then final response
        mock_fn_call = MagicMock()
        mock_fn_call.name = "parse_log_file"
        mock_fn_call.args = {"file_path": "/tmp/test.log", "context_window": 20.0}

        mock_part_call = MagicMock()
        mock_part_call.function_call = mock_fn_call

        mock_candidate_1 = MagicMock()
        mock_candidate_1.content.parts = [mock_part_call]
        mock_response_1 = MagicMock()
        mock_response_1.candidates = [mock_candidate_1]

        mock_part_text = MagicMock()
        mock_part_text.function_call = None
        mock_candidate_2 = MagicMock()
        mock_candidate_2.content.parts = [mock_part_text]
        mock_response_2 = MagicMock()
        mock_response_2.candidates = [mock_candidate_2]
        mock_response_2.text = MOCK_FINAL_RESPONSE
        mock_response_2.usage_metadata.prompt_token_count = 300

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = [
            mock_response_1, mock_response_2,
        ]
        mock_client_cls.return_value = mock_client_instance

        callback_log = []

        def my_callback(name, args, result):
            callback_log.append({"name": name, "args": args})

        agent = LogAnalysisAgent(api_key="fake-key")
        with patch("src.agent.TOOL_REGISTRY", {
            "parse_log_file": lambda **kw: {"status": "anomaly_found", "severity": 6},
        }):
            agent.investigate("/tmp/test.log", on_tool_call=my_callback)

        assert len(callback_log) == 1
        assert callback_log[0]["name"] == "parse_log_file"
        # Float args should be cast to int
        assert callback_log[0]["args"]["context_window"] == 20

    @patch("src.agent.genai.Client")
    def test_max_iterations_safety(self, mock_client_cls):
        """Agent returns a LOW-confidence fallback if max iterations exceeded."""
        # Always return a function call (infinite loop scenario)
        mock_fn_call = MagicMock()
        mock_fn_call.name = "scan_all_anomalies"
        mock_fn_call.args = {"file_path": "/tmp/test.log"}

        mock_part = MagicMock()
        mock_part.function_call = mock_fn_call

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client_instance

        with patch("src.agent.TOOL_REGISTRY", {
            "scan_all_anomalies": lambda **kw: {"status": "clean"},
        }):
            with patch("src.agent.MAX_AGENT_ITERATIONS", 3):
                agent = LogAnalysisAgent(api_key="fake-key")
                result = agent.investigate("/tmp/test.log")

        assert result["confidence"] == "LOW"
        assert result["iterations"] == 3


class TestAgentSystemPrompt:
    def test_system_instruction_contains_tool_descriptions(self):
        assert "parse_log_file" in AGENT_SYSTEM_INSTRUCTION
        assert "scan_all_anomalies" in AGENT_SYSTEM_INSTRUCTION
        assert "read_log_lines" in AGENT_SYSTEM_INSTRUCTION
        assert "search_log_pattern" in AGENT_SYSTEM_INSTRUCTION

    def test_tool_declarations_has_four_functions(self):
        assert len(TOOL_DECLARATIONS.function_declarations) == 4

    def test_tool_declaration_names(self):
        names = {fd.name for fd in TOOL_DECLARATIONS.function_declarations}
        assert names == {
            "parse_log_file",
            "scan_all_anomalies",
            "read_log_lines",
            "search_log_pattern",
        }
