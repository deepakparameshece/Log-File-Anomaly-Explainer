"""
Agent Module
============
Implements a tool-using agent loop where the LLM iteratively calls tools
(log parser, line reader, pattern searcher) to investigate anomalies before
producing a final structured analysis.

This satisfies the "Tool-using agent" capability requirement.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any, Callable, Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

from src.tools import TOOL_REGISTRY

load_dotenv()

# ---------------------------------------------------------------------------
# Maximum iterations to prevent infinite loops
# ---------------------------------------------------------------------------
MAX_AGENT_ITERATIONS = 10

# ---------------------------------------------------------------------------
# Agent system instruction
# ---------------------------------------------------------------------------
AGENT_SYSTEM_INSTRUCTION = textwrap.dedent("""\
    You are an expert Site Reliability Engineer (SRE) agent with access to log
    analysis tools.  Your job is to investigate log files to find and explain
    anomalies.

    **Available tools:**
    1. **parse_log_file** — Parse a log file to find the primary (highest-severity)
       anomaly and extract surrounding context lines.
    2. **scan_all_anomalies** — Scan the entire log and list all distinct anomaly
       clusters with their severity scores.
    3. **read_log_lines** — Read a specific range of lines from the log file for
       deeper inspection.
    4. **search_log_pattern** — Search the log for a regex pattern and return
       matching lines with line numbers.

    **Investigation workflow:**
    1. Start by scanning the log to get an overview of all anomalies.
    2. Parse the log to get full context around the primary anomaly.
    3. If needed, read additional lines or search for related patterns (e.g.
       preceding warnings, correlated request IDs) to build a complete picture.
    4. Once you have enough information, provide your final analysis.

    **Your final response MUST use this exact structured format:**

    ## Root Cause Analysis
    <One concise paragraph explaining the technical root cause of the error.>

    ## Probable Cause
    <One concise paragraph explaining WHY this error likely occurred, referencing
    specific lines or values from the log.>

    ## Remediation Steps
    <A numbered list of 3–6 actionable steps an on-call engineer can take
    immediately to diagnose, mitigate, or permanently fix this issue.>

    ## Confidence
    <A single word: HIGH / MEDIUM / LOW>
""")

# ---------------------------------------------------------------------------
# Function declarations for Gemini function calling
# ---------------------------------------------------------------------------
TOOL_DECLARATIONS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="parse_log_file",
            description=(
                "Parse a log file to detect the primary (highest-severity) anomaly "
                "and extract surrounding context lines."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Absolute path to the log file to analyse.",
                    ),
                    "context_window": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of context lines before/after the anomaly. Default: 20.",
                    ),
                },
                required=["file_path"],
            ),
        ),
        types.FunctionDeclaration(
            name="scan_all_anomalies",
            description=(
                "Scan a log file and return a summary of ALL distinct anomaly "
                "clusters with their severity scores."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Absolute path to the log file.",
                    ),
                    "context_window": types.Schema(
                        type=types.Type.INTEGER,
                        description="Context window size for cluster de-duplication. Default: 20.",
                    ),
                },
                required=["file_path"],
            ),
        ),
        types.FunctionDeclaration(
            name="read_log_lines",
            description=(
                "Read a specific range of lines from the log file for deeper "
                "inspection. Lines are 1-indexed and inclusive."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Absolute path to the log file.",
                    ),
                    "start_line": types.Schema(
                        type=types.Type.INTEGER,
                        description="First line to read (1-indexed).",
                    ),
                    "end_line": types.Schema(
                        type=types.Type.INTEGER,
                        description="Last line to read (1-indexed, inclusive).",
                    ),
                },
                required=["file_path", "start_line", "end_line"],
            ),
        ),
        types.FunctionDeclaration(
            name="search_log_pattern",
            description=(
                "Search the log file for a regex pattern. Returns up to 50 "
                "matching lines with their line numbers."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "file_path": types.Schema(
                        type=types.Type.STRING,
                        description="Absolute path to the log file.",
                    ),
                    "pattern": types.Schema(
                        type=types.Type.STRING,
                        description="Regex pattern to search for (case-insensitive).",
                    ),
                },
                required=["file_path", "pattern"],
            ),
        ),
    ]
)


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------
class LogAnalysisAgent:
    """
    Tool-using agent that iteratively investigates log files.

    The agent loop:
      1. Sends the user request + tool declarations to Gemini.
      2. If Gemini returns function_call(s), executes them and sends results back.
      3. Repeats until Gemini produces a final text response (no more tool calls).
      4. Parses the structured response and returns it.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set.  "
                "Add it to your .env file or export it as an environment variable."
            )
        self._client = genai.Client(api_key=self.api_key)
        self.model_name = model or "gemini-2.0-flash"
        self.tool_calls_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def investigate(
        self,
        log_file_path: str,
        user_query: str | None = None,
        on_tool_call: Optional[Callable[[str, dict, dict], None]] = None,
    ) -> dict[str, Any]:
        """
        Run the agent loop to investigate a log file.

        Args:
            log_file_path:  Absolute path to the log file.
            user_query:     Optional extra context or question from the user.
            on_tool_call:   Optional callback(tool_name, args, result) for
                            live progress reporting.

        Returns:
            dict with keys: root_cause, probable_cause, remediation,
            confidence, raw_response, model, tool_calls_log, iterations.
        """
        self.tool_calls_log = []

        # Build initial user message
        initial_prompt = (
            f"Investigate the log file at: {log_file_path}\n\n"
            "Use your tools to scan for anomalies, read context, and search "
            "for related patterns. Then provide your structured analysis."
        )
        if user_query:
            initial_prompt += f"\n\nAdditional context from the engineer: {user_query}"

        # Conversation history
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=initial_prompt)],
            )
        ]

        config = types.GenerateContentConfig(
            tools=[TOOL_DECLARATIONS],
            system_instruction=AGENT_SYSTEM_INSTRUCTION,
        )

        # --- Agent loop ---
        for iteration in range(MAX_AGENT_ITERATIONS):
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]

            # Collect any function calls from the response
            function_calls = [
                part for part in candidate.content.parts
                if part.function_call is not None
            ]

            if not function_calls:
                # ── Final text response ──
                raw = response.text
                parsed = self._parse_response(raw)
                parsed["raw_response"] = raw
                parsed["model"] = self.model_name
                parsed["tool_calls_log"] = self.tool_calls_log
                parsed["iterations"] = iteration + 1
                try:
                    parsed["prompt_tokens"] = response.usage_metadata.prompt_token_count
                except AttributeError:
                    parsed["prompt_tokens"] = None
                return parsed

            # ── Execute tool calls ──
            # Append the model's message (containing function_call parts)
            contents.append(candidate.content)

            function_response_parts: list[types.Part] = []
            for part in function_calls:
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args) if part.function_call.args else {}

                # Cast numeric args that arrive as floats
                for k, v in fn_args.items():
                    if isinstance(v, float) and v == int(v):
                        fn_args[k] = int(v)

                # Dispatch
                tool_fn = TOOL_REGISTRY.get(fn_name)
                if tool_fn is not None:
                    result = tool_fn(**fn_args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                # Log
                self.tool_calls_log.append({
                    "iteration": iteration + 1,
                    "tool": fn_name,
                    "args": fn_args,
                    "result_preview": str(result)[:300],
                })

                # Callback for live UI
                if on_tool_call:
                    on_tool_call(fn_name, fn_args, result)

                function_response_parts.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response=result,
                    )
                )

            # Send tool results back to the model
            contents.append(
                types.Content(
                    role="user",
                    parts=function_response_parts,
                )
            )

        # ── Exhausted iterations ──
        return {
            "root_cause": "Agent reached maximum iterations without completing analysis.",
            "probable_cause": "",
            "remediation": "",
            "confidence": "LOW",
            "raw_response": "",
            "model": self.model_name,
            "tool_calls_log": self.tool_calls_log,
            "iterations": MAX_AGENT_ITERATIONS,
            "prompt_tokens": None,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_response(text: str) -> dict[str, str]:
        """Extract the four structured sections from the LLM response."""
        sections: dict[str, str] = {
            "root_cause": "",
            "probable_cause": "",
            "remediation": "",
            "confidence": "UNKNOWN",
        }
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
            next_header_pos = len(text)
            for other_key, other_header in markers.items():
                if other_key == key:
                    continue
                pos = text.find(other_header, content_start)
                if pos != -1 and pos < next_header_pos:
                    next_header_pos = pos
            sections[key] = text[content_start:next_header_pos].strip()
        return sections
