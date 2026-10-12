# OpsPilot — Autonomous Business Operations Analyst

OpsPilot is a small project-based prototype of an AI employee for business data analysis. It accepts a business objective and a sales CSV, uses Python tools to inspect and analyze the data, records actions, checks a key numerical result, and writes a report.

## Why this project
It demonstrates a bounded agent workflow: goal → tool selection → execution → observation → final report, with an execution limit and an action log.

## Features
- CSV inspection and basic data-quality checks
- Revenue KPIs and earliest-vs-latest-month comparison
- Revenue grouped by category
- Optional LLM tool calling through the OpenAI Python SDK
- Offline fallback so data tools can be tested without an API key
- Independent total-revenue verification
- JSON action log, Markdown report, and unit tests

## Requirements
- Python 3.10 or newer
- Optional: an API key with access to a model that supports Chat Completions tool calling

## Setup (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run without an API key
```powershell
python main.py --offline
```

## Run with LLM tool calling
Set your API key for the current PowerShell session:
```powershell
$env:OPENAI_API_KEY="YOUR_KEY_HERE"
python main.py --task "Analyze sales performance, identify important findings, and recommend actions."
```
Never commit your real API key. The model name is set in `agent.py` and may need changing to a model available to your API account.

## Use another CSV
The default expected columns are `date`, `revenue`, and `category` for the corresponding tools.
```powershell
python main.py --file data/sample_sales.csv --task "Compare monthly revenue and identify the strongest category."
```

## Tests
```powershell
python -m unittest discover -s tests -v
```

## Output
- `reports/ops_report.md`: findings and verification summary
- `reports/action_log.json`: tool-by-tool execution record

## Safety and limitations
- Analysis tools are read-only and operate on the supplied CSV.
- Tool calls are limited to eight per run.
- The offline mode uses a fixed sequence of analysis tools; it is a testing fallback, not LLM-driven autonomy.
- Month-to-month differences are descriptive and do not prove causation.
- The current verifier independently recomputes total revenue, but it does not validate every natural-language claim in the LLM's report.
- Review recommendations before making consequential business decisions.
- This is a prototype, not a production-ready enterprise agent.

## Suggested next improvements
- Add schema adaptation with explicit confirmation
- Add tests for malformed rows, invalid dates, and unsupported columns
- Add a browser research tool with source URL logging
- Measure task completion, numerical accuracy, and verification pass rate over a fixed test set
