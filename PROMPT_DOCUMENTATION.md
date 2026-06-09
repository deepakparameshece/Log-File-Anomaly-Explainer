# Prompt Documentation — Log File Anomaly Explainer (PS-02)

> **Mandatory compliance artifact.** This document tracks every core prompt
> template used to interact with the LLM during the build.

---

## 1. System Instruction (Gemini `system_instruction`)

**Location:** [`src/llm_client.py`](src/llm_client.py) → `SYSTEM_INSTRUCTION`

```text
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
<A numbered list of 3-6 actionable steps an on-call engineer can take immediately
to diagnose, mitigate, or permanently fix this issue.>

## Confidence
<A single word: HIGH / MEDIUM / LOW - your confidence in the above analysis given
the available context.>
```

### Design Rationale

| Decision | Reason |
|---|---|
| **Persona: SRE specialist** | Ensures domain-appropriate vocabulary and actionable output |
| **Strict output format** | Enables deterministic parsing in `GeminiClient._parse_response()` |
| **Confidence field** | Allows downstream consumers to filter or escalate low-confidence results |
| **"No extra prose" instruction** | Prevents the model from adding preamble/postamble that breaks parsing |

---

## 2. User Prompt Template

**Location:** [`src/llm_client.py`](src/llm_client.py) → `USER_PROMPT_TEMPLATE`

```text
### Log File Metadata
- **File:** {file_path}
- **Total lines in file:** {total_lines}
- **Primary anomaly at line:** {primary_line} (marked with >>>)
- **Context window:** lines {context_start} - {context_end}
- **Detected severity score:** {severity}/6

### Primary Error Line
{primary_line_content}

### Context Window (+-20 lines)
{formatted_context}

Please analyse the above log excerpt and provide your structured response.
```

### Template Variables

| Variable | Source | Description |
|---|---|---|
| `{file_path}` | `AnomalyBlock.file_path` | Absolute path to the parsed log file |
| `{total_lines}` | `AnomalyBlock.total_log_lines` | Total number of lines in the original file |
| `{primary_line}` | `AnomalyBlock.primary_line_number` | 1-indexed line number of the primary error |
| `{context_start}` | `AnomalyBlock.context_start` | First line number in the context window |
| `{context_end}` | `AnomalyBlock.context_end` | Last line number in the context window |
| `{severity}` | `AnomalyBlock.severity` | Severity score (0-6 scale) |
| `{primary_line_content}` | `AnomalyBlock.primary_line_content` | Raw text of the primary error line |
| `{formatted_context}` | `AnomalyBlock.formatted_context` | Numbered context with `>>>` marker |

### Design Rationale

| Decision | Reason |
|---|---|
| **Metadata block first** | Gives the LLM file-level awareness before seeing raw logs |
| **Severity score included** | Helps the model calibrate its confidence assessment |
| **`>>>` marker on primary line** | Unambiguous visual cue so the model doesn't guess which line is the error |
| **Explicit "analyse" instruction** | Direct call-to-action prevents the model from summarising without analysis |

---

## 3. Error Detection Patterns

**Location:** [`src/parser.py`](src/parser.py) → `ERROR_PATTERNS` and `SEVERITY_RANK`

The parser uses a ranked set of regex patterns to detect anomalies before any
LLM interaction occurs. These are not prompts but directly inform what gets
sent to the LLM:

| Pattern | Severity | Examples Matched |
|---|---|---|
| `CRITICAL` / `FATAL` | 6 | `CRITICAL [db] All reconnection attempts exhausted` |
| `panic` / `segfault` / `oom-kill` | 6 | `panic: runtime error: index out of range` |
| `EXCEPTION` / `Traceback` | 4 | `Traceback (most recent call last):` |
| `ERROR` | 3 | `ERROR [http] GET /api/orders 503` |
| `HTTP 4xx/5xx` | 2 | `"POST /api/process HTTP/1.1" 500 156` |
| `timeout` / `connection refused` | 2 | `connection refused after 3 retries` |
| `WARNING` / `WARN` | 1 | `WARN [db] Slow query detected` |

---

## 4. Prompt Engineering Notes

### What was tried and why

1. **Initial approach - raw log dump:**
   Sending the entire log file to the LLM produced unfocused responses and
   hit token limits on larger files. Switched to a +-20-line context window.

2. **Unstructured response format:**
   Early iterations asked the LLM to "explain the error". The output was
   inconsistent - sometimes a paragraph, sometimes bullet points. Adding the
   strict `## Section` format with parsing made output deterministic.

3. **Severity scoring:**
   Adding the severity score to the prompt improved the model's confidence
   calibration - it stopped saying "HIGH" confidence for minor warnings.

4. **Context markers (`>>>`):**
   Without the marker, the model sometimes analysed the wrong line. The `>>>`
   prefix on the primary error line eliminated this ambiguity.

---

## 5. Tool-Using Agent System Instruction

**Location:** [`src/agent.py`](src/agent.py) → `AGENT_SYSTEM_INSTRUCTION`

The agent mode uses a separate system instruction that describes the available
tools and the expected investigation workflow:

```text
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
3. If needed, read additional lines or search for related patterns to build
   a complete picture.
4. Once you have enough information, provide your final analysis.

(Same structured output format as Section 1.)
```

### Agent Tool Declarations

**Location:** [`src/agent.py`](src/agent.py) → `TOOL_DECLARATIONS`

Four tools are declared as Gemini function-calling schemas:

| Tool | Parameters | Description |
|---|---|---|
| `parse_log_file` | `file_path` (required), `context_window` (optional) | Finds the primary anomaly with ±N context lines |
| `scan_all_anomalies` | `file_path` (required), `context_window` (optional) | Lists all distinct anomaly clusters |
| `read_log_lines` | `file_path`, `start_line`, `end_line` (all required) | Reads a specific line range |
| `search_log_pattern` | `file_path`, `pattern` (both required) | Regex search across the file |

### Agent Loop Architecture

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────┐
│                   Agent Loop                        │
│                                                     │
│  ┌───────────┐    function_call?   ┌─────────────┐  │
│  │  Gemini   │──── YES ──────────▶│  Execute    │  │
│  │  API      │                     │  Tool       │  │
│  │           │◀── tool result ────│  (parser,   │  │
│  │           │                     │   scanner,  │  │
│  │           │──── NO (text) ─┐    │   reader,   │  │
│  └───────────┘                │    │   searcher) │  │
│                               │    └─────────────┘  │
│                               ▼                     │
│                        Final Analysis               │
│                    (max 10 iterations)               │
└─────────────────────────────────────────────────────┘
     │
     ▼
Structured Output
(Root Cause / Probable Cause / Remediation / Confidence)
```

### Design Rationale

| Decision | Reason |
|---|---|
| **Explicit workflow in system prompt** | Guides the agent toward a productive investigation order |
| **4 complementary tools** | Covers overview (scan), detail (parse), drill-down (read), and discovery (search) |
| **Max 10 iterations** | Prevents infinite loops and runaway API costs |
| **Float-to-int casting** | Gemini sometimes returns integer args as floats; casting prevents TypeError |
| **on_tool_call callback** | Enables live CLI progress without coupling agent to presentation |

---

*Last updated: 2026-06-09*
