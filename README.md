# Log File Anomaly Explainer (PS-02)

A CLI tool that ingests `.log` files, detects anomalies (errors, crashes,
timeouts), extracts contextual log windows, and uses **Google Gemini** to
explain the root cause with actionable remediation steps.

Built for on-call engineers who need to understand incidents *fast*.

---

## Features

- **Smart anomaly detection** — ranked severity scoring across 10+ error
  patterns (CRITICAL, FATAL, Traceback, HTTP 5xx, OOM, timeouts, etc.)
- **Context-aware extraction** — pulls +/-20 lines around the primary error
  so the LLM has full system-state awareness
- **Structured LLM analysis** — Root Cause, Probable Cause, Remediation
  Steps, and Confidence level
- **Multiple output formats** — Rich console, JSON, or Markdown reports
- **Scan mode** — quick anomaly inventory without burning an LLM call
- **Multi-anomaly support** — analyse all distinct error clusters in one run

---

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A free [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd log_anamoly_detection_system

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

### Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

```env
GEMINI_API_KEY=your-api-key-here
```

---

## Usage

### Analyse a log file (primary command)

```bash
# Basic usage
uv run log-explainer explain app.log

# With custom context window
uv run log-explainer explain app.log --context 30

# Output as JSON
uv run log-explainer explain app.log --output json --out-file result.json

# Output as Markdown report
uv run log-explainer explain app.log --output markdown --out-file report.md

# Analyse ALL anomaly clusters
uv run log-explainer explain app.log --all-anomalies

# Use a different Gemini model
uv run log-explainer explain app.log --model gemini-1.5-pro
```

### Quick scan (no LLM call)

```bash
uv run log-explainer scan app.log
```

### Run via Python directly

```bash
uv run python -m src.cli explain tests/fixtures/sample_app.log
```

---

## Project Structure

```
.
├── src/
│   ├── __init__.py          # Package init
│   ├── cli.py               # Click CLI with explain & scan commands
│   ├── parser.py            # Log scanning and context extraction
│   └── llm_client.py        # Gemini API integration and response parsing
├── tests/
│   ├── fixtures/            # Sample log files for testing
│   │   ├── sample_app.log   # App log with DB failure cascade
│   │   ├── sample_clean.log # Clean log (no errors)
│   │   └── sample_access.log# HTTP access log with 4xx/5xx
│   ├── test_parser.py       # Parser unit tests
│   └── test_llm_client.py   # LLM client tests (mocked)
├── prompt_documentation.md  # Mandatory prompt tracking document
├── pyproject.toml           # Project config & dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

---

## How It Works

```
┌──────────┐     ┌───────────────┐     ┌───────────────┐     ┌──────────────┐
│ .log file│────>│  Log Parser   │────>│ Context Block │────>│ Gemini API   │
│          │     │ (severity     │     │ (error + ±20  │     │ (structured  │
│          │     │  ranked scan) │     │  lines)       │     │  analysis)   │
└──────────┘     └───────────────┘     └───────────────┘     └──────┬───────┘
                                                                    │
                                                          ┌─────────v─────────┐
                                                          │ Rich Console /    │
                                                          │ JSON / Markdown   │
                                                          └───────────────────┘
```

1. **Parse** — Scans the log file line-by-line using 10+ regex patterns,
   each scored on a 0–6 severity scale.
2. **Extract** — Pulls +/-20 lines of context around the highest-severity
   anomaly to give the LLM system-state awareness.
3. **Analyse** — Sends a structured prompt (with metadata + context) to
   Google Gemini's free-tier API.
4. **Report** — Presents Root Cause Analysis, Probable Cause, Remediation
   Steps, and Confidence in your chosen format.

---

## Running Tests

```bash
uv run pytest tests/ -v
```

---

## License

MIT
