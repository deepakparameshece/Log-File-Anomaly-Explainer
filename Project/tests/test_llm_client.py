"""
Tests for src/llm_client.py — mocked to avoid live API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.parser import AnomalyBlock


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------
def _make_block(**overrides) -> AnomalyBlock:
    defaults = dict(
        file_path="/tmp/test.log",
        primary_line_number=42,
        primary_line_content="ERROR: Database connection refused after 3 retries",
        context_start=22,
        context_end=62,
        context_lines=["line content\n"] * 41,
        severity=3,
        total_log_lines=200,
    )
    defaults.update(overrides)
    return AnomalyBlock(**defaults)


MOCK_LLM_RESPONSE = """\
## Root Cause Analysis
The database connection pool exhausted all retry attempts, indicating the PostgreSQL \
instance at db.local:5432 was unreachable.

## Probable Cause
The context lines show timeout errors escalating over three consecutive attempts \
within a one-second window, suggesting a network partition or the database process \
crashed.

## Remediation Steps
1. SSH into the database host and check `systemctl status postgresql`.
2. Verify network connectivity: `ping db.local` and `telnet db.local 5432`.
3. Inspect PostgreSQL logs under `/var/log/postgresql/` for OOM or crash entries.
4. If the DB is healthy, increase the connection timeout in the app config.
5. Consider adding a circuit-breaker pattern to avoid cascading failures.

## Confidence
HIGH
"""


class TestGeminiClientParsing:
    """Test response parsing without hitting the live API."""

    def test_parse_response_extracts_all_sections(self):
        from src.llm_client import GeminiClient

        parsed = GeminiClient._parse_response(MOCK_LLM_RESPONSE)
        assert "Root Cause Analysis" in MOCK_LLM_RESPONSE  # sanity
        assert "PostgreSQL" in parsed["root_cause"]
        assert "network partition" in parsed["probable_cause"]
        assert "1." in parsed["remediation"]
        assert parsed["confidence"] == "HIGH"

    def test_parse_response_handles_missing_sections(self):
        from src.llm_client import GeminiClient

        partial = "## Root Cause Analysis\nSomething broke.\n"
        parsed = GeminiClient._parse_response(partial)
        assert parsed["root_cause"] == "Something broke."
        assert parsed["probable_cause"] == ""
        assert parsed["confidence"] == "UNKNOWN"


class TestGeminiClientInit:
    def test_raises_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from src.llm_client import GeminiClient
        with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
            GeminiClient(api_key=None)

    @patch("src.llm_client.genai.Client")
    def test_initialises_with_api_key(self, mock_client_cls):
        from src.llm_client import GeminiClient
        client = GeminiClient(api_key="test-key-123")
        mock_client_cls.assert_called_once_with(api_key="test-key-123")
        assert client.api_key == "test-key-123"


class TestGeminiClientExplain:
    @patch("src.llm_client.genai.Client")
    def test_explain_returns_structured_dict(self, mock_client_cls):
        # Set up mock response
        mock_response = MagicMock()
        mock_response.text = MOCK_LLM_RESPONSE
        mock_response.usage_metadata.prompt_token_count = 512

        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client_instance

        from src.llm_client import GeminiClient
        client = GeminiClient(api_key="fake-key")
        result = client.explain(_make_block())

        assert "root_cause" in result
        assert "probable_cause" in result
        assert "remediation" in result
        assert "confidence" in result
        assert result["confidence"] == "HIGH"
        assert result["prompt_tokens"] == 512
        assert "PostgreSQL" in result["root_cause"]
