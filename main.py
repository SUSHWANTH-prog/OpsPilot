import argparse
import os
from pathlib import Path

from tools.data_tools import (
    inspect_data,
    calculate_kpis,
    compare_periods,
    revenue_by_category,
    verify_report,
    write_report,
)
from agent import run_agent

TOOLS = {
    "inspect_data": inspect_data,
    "calculate_kpis": calculate_kpis,
    "compare_periods": compare_periods,
    "revenue_by_category": revenue_by_category,
}

def main():
    parser = argparse.ArgumentParser(description="OpsPilot: autonomous business operations analyst")
    parser.add_argument("--file", default="data/sample_sales.csv", help="Path to a sales CSV file")
    parser.add_argument("--task", default="Analyze sales performance, identify important findings, and recommend actions.",
                        help="Business objective for the agent")
    parser.add_argument("--offline", action="store_true", help="Run without an LLM API key")
    args = parser.parse_args()

    csv_path = Path(args.file)
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    api_key = os.getenv("OPENAI_API_KEY")
    use_llm = bool(api_key) and not args.offline

    print("\n=== OpsPilot: Business Operations Analyst ===")
    print(f"Dataset: {csv_path}")
    print(f"Mode: {'LLM tool-calling' if use_llm else 'offline fallback (no API key needed)'}")
    print(f"Task: {args.task}\n")

    if use_llm:
        try:
            findings, action_log = run_agent(args.task, str(csv_path), TOOLS, api_key)
        except Exception as exc:
            print(f"LLM mode failed: {exc}")
            print("Switching to offline fallback so you can still test the project.")
            findings, action_log = run_agent(args.task, str(csv_path), TOOLS, None)
    else:
        findings, action_log = run_agent(args.task, str(csv_path), TOOLS, None)

    verification = verify_report(findings, csv_path)
    report_path = Path("reports/ops_report.md")
    write_report(args.task, findings, action_log, verification, report_path)

    print("=== Findings ===")
    for item in findings:
        print(f"- {item.get('summary', item)}")
    print("\n=== Verification ===")
    print(verification["message"])
    print(f"\nReport saved to: {report_path}")
    print(f"Action log saved to: reports/action_log.json")
    print("Done.")

if __name__ == "__main__":
    main()
