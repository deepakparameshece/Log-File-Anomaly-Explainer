# Demo Video

## Log File Anomaly Explainer — Live Demo

📺 **Video Link:** [https://drive.google.com/drive/folders/1O2iuCyTdRq9pVb9RB1amkmvmaJgj4X2n](#)


---

### What the demo covers

1. **`scan` command** — Quick anomaly detection without LLM (instant results table)
2. **`explain` command** — Single-pass LLM analysis with Root Cause, Probable Cause, and Remediation Steps
3. **`investigate` command** — Full agent mode where the LLM autonomously uses tools to investigate the log
4. **JSON/Markdown export** — Saving structured reports for sharing

### How to record

```bash
# From the Project/ directory:
cd Project
uv sync
uv run log-explainer scan sample_data/Thunderbird_2k.log
uv run log-explainer explain sample_data/Thunderbird_2k.log --all-anomalies
uv run log-explainer investigate sample_data/Thunderbird_2k.log
```
