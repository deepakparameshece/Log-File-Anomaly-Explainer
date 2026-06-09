# Log File Anomaly Explainer (UC ID: PS-02)

> **AI-Powered Log Triage Agent** — A CLI tool that ingests `.log` files,
> detects anomalies, and uses Google Gemini to explain root causes with
> actionable remediation steps.

---

## 📁 Repository Structure

```
├── Project/              # Core codebase (all Python source code)
│   ├── src/              #   Source modules (parser, LLM client, agent, CLI)
│   ├── tests/            #   Test suite with fixtures
│   ├── sample_data/      #   Sample log files for demo
│   ├── pyproject.toml    #   Project config & dependencies
│   └── .env.example      #   API key template
│
├── Video/                # Demo video link
│   └── Video_Link.md
│
├── Team/                 # Team member details
│   └── Team_Details.md
│
├── Resume/               # Individual resumes
│   └── Harish_S_Resume.pdf.pdf
│
├── Document/             # Project documentation
│   ├── prompt_documentation.md   # Mandatory prompt tracking (compliance)
│   └── REPORT.md                 # Sample analysis report
│
└── README.md             # This file
```

---

## 🚀 Quick Start

```bash
# Navigate to the project directory
cd Project

# Install dependencies (requires Python 3.10+ and uv)
uv sync

# Configure your Gemini API key
cp .env.example .env
# Edit .env → set GEMINI_API_KEY=your-key

# Run a quick scan (no API key needed)
uv run log-explainer scan sample_data/Thunderbird_2k.log

# Run the full LLM analysis
uv run log-explainer explain sample_data/Thunderbird_2k.log

# Run the agent investigation mode
uv run log-explainer investigate sample_data/Thunderbird_2k.log
```

See [`Project/README.md`](Project/README.md) for detailed usage and technical documentation.

---

## 🧰 Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Interface | CLI (Click) |
| AI Integration | Google Gemini API (free tier) via `google-genai` SDK |
| Agent Capability | Tool-using agent loop with function calling |
| Data Source | Structured `.log` file parsing |
| Output | Rich console, JSON, Markdown reports |
| Package Manager | uv |

---

## 🎯 Key Capabilities

- **External API / Service Integration** — Google Gemini 2.0 Flash (free tier)
- **Tool-Using Agent Loop** — LLM autonomously calls analysis tools (parse, scan, read, search) and reasons iteratively
- **Severity-Ranked Detection** — 10+ error patterns scored on a 0–6 scale
- **±20-Line Context Windows** — Surrounding log context for full situational awareness
- **3 Output Formats** — Rich console, JSON, and Markdown

---

## 📝 Documentation

- [Prompt Documentation](Document/prompt_documentation.md) — All LLM prompts, templates, and design rationale
- [Analysis Report](Document/REPORT.md) — Sample analysis output from the tool
- [Technical README](Project/README.md) — Full usage docs, architecture, and testing guide

---

## 👥 Team

See [Team/Team_Details.md](Team/Team_Details.md) for team member details.

---

## 🎬 Demo

See [Video/Video_Link.md](Video/Video_Link.md) for the demo video link.
