"""
LLM Client Module
=================
Packages the extracted anomaly context into a structured prompt and sends it
to the Google Gemini API (free tier) using the modern ``google-genai`` SDK.
Returns a structured analysis dict.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any

from google import genai
from google.genai import types
from dotenv import load_dotenv

from src.parser import AnomalyBlock

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Prompt Templates (documented in prompt_documentation.md)
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = textwrap.dedent("""\
    You are an expert Site Reliability Engineer (SRE) and software debugging specialist.
    Your task is to analyse a section of a log file that contains an error or anomaly.

    You will receive:
    1. Metadata about the log file (path, line numbers, severity).
    2. A context window of log lines (±20 lines around the primary error), with the
       primary error line highlighted by ">>>" at the start of its row.

    You must respond in the following EXACT structured format (no extra prose outside
    the sections below):

    ## Root Cause Analysis
    <One concise paragraph explaining the technical root cause of the error.>

    ## Probable Cause
    <One concise paragraph explaining WHY this error likely occurred, referencing
    specific lines or values from the provided context.>

    ## Remediation Steps
    <A numbered list of 3–6 actionable steps an on-call engineer can take immediately
    to diagnose, mitigate, or permanently fix this issue.>

    ## Confidence
    <A single word: HIGH / MEDIUM / LOW — your confidence in the above analysis given
    the available context.>
""")

USER_PROMPT_TEMPLATE = textwrap.dedent("""\
    ### Log File Metadata
    - **File:** {file_path}
    - **Total lines in file:** {total_lines}
    - **Primary anomaly at line:** {primary_line} (marked with >>>)
    - **Context window:** lines {context_start} – {context_end}
    - **Detected severity score:** {severity}/6

    ### Primary Error Line
    ```
    {primary_line_content}
    ```

    ### Context Window (±20 lines)
    ```
    {formatted_context}
    ```

    Please analyse the above log excerpt and provide your structured response.
""")


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
class GeminiClient:
    """
    Thin wrapper around the Google GenAI SDK targeting the Gemini 2.0 Flash
    model (free tier).  Falls back gracefully if the API key is missing.
    """

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set.  "
                "Add it to your .env file or export it as an environment variable."
            )
        self._client = genai.Client(api_key=self.api_key)
        self.model_name = model or self.DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def explain(self, block: AnomalyBlock) -> dict[str, Any]:
        """
        Send the AnomalyBlock to Gemini and return a structured dict with keys:
          - raw_response  : full LLM text
          - root_cause    : extracted section
          - probable_cause: extracted section
          - remediation   : extracted section
          - confidence    : HIGH / MEDIUM / LOW
          - model         : model name used
          - prompt_tokens : approximate token count (if available)
        """
        prompt = self._build_prompt(block)
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )
        raw = response.text
        parsed = self._parse_response(raw)
        parsed["raw_response"] = raw
        parsed["model"] = self.model_name
        # Extract usage metadata if available
        try:
            parsed["prompt_tokens"] = response.usage_metadata.prompt_token_count
        except AttributeError:
            parsed["prompt_tokens"] = None
        return parsed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build_prompt(self, block: AnomalyBlock) -> str:
        return USER_PROMPT_TEMPLATE.format(
            file_path=block.file_path,
            total_lines=block.total_log_lines,
            primary_line=block.primary_line_number,
            context_start=block.context_start,
            context_end=block.context_end,
            severity=block.severity,
            primary_line_content=block.primary_line_content.strip(),
            formatted_context=block.formatted_context,
        )

    @staticmethod
    def _parse_response(text: str) -> dict[str, str]:
        """Extract the four structured sections from the LLM response."""
        sections: dict[str, str] = {
            "root_cause": "",
            "probable_cause": "",
            "remediation": "",
            "confidence": "UNKNOWN",
        }

        # Simple section splitter based on the markdown headers we instruct the model to use
        markers = {
            "root_cause": "## Root Cause Analysis",
            "probable_cause": "## Probable Cause",
            "remediation": "## Remediation Steps",
            "confidence": "## Confidence",
        }

        for key, header in markers.items():
            start = text.find(header)
            if start == -1:
                continue
            content_start = start + len(header)
            # Find the next section header
            next_header_pos = len(text)
            for other_key, other_header in markers.items():
                if other_key == key:
                    continue
                pos = text.find(other_header, content_start)
                if pos != -1 and pos < next_header_pos:
                    next_header_pos = pos
            sections[key] = text[content_start:next_header_pos].strip()

        return sections
