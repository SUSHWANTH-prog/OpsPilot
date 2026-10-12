"""LLM-driven tool loop with a safe, bounded offline fallback."""
import json
from pathlib import Path

MAX_TOOL_CALLS = 8

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_data",
            "description": "Inspect CSV columns, row count, date range, and data-quality issues.",
            "parameters": {
                "type": "object",
                "properties": {"csv_path": {"type": "string", "description": "Path to the CSV file"}},
                "required": ["csv_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_kpis",
            "description": "Calculate overall revenue, order count, average order value, and date range.",
            "parameters": {
                "type": "object",
                "properties": {"csv_path": {"type": "string"}},
                "required": ["csv_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": "Compare revenue between the earliest and latest month in the CSV.",
            "parameters": {
                "type": "object",
                "properties": {"csv_path": {"type": "string"}},
                "required": ["csv_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "revenue_by_category",
            "description": "Calculate revenue totals by product category.",
            "parameters": {
                "type": "object",
                "properties": {"csv_path": {"type": "string"}},
                "required": ["csv_path"],
                "additionalProperties": False,
            },
        },
    },
]

def _offline_run(csv_path, tools):
    """A deterministic fallback for testing when no API key is available."""
    results = []
    log = []
    for name in ("inspect_data", "calculate_kpis", "compare_periods", "revenue_by_category"):
        try:
            result = tools[name](csv_path)
            results.append({"tool": name, "summary": json.dumps(result, ensure_ascii=False), "data": result})
            log.append({"tool": name, "status": "success", "result": result, "mode": "offline"})
        except Exception as exc:
            error = {"error": str(exc)}
            results.append({"tool": name, "summary": f"{name} failed: {exc}", "data": error})
            log.append({"tool": name, "status": "error", "result": error, "mode": "offline"})
    return results, log

def run_agent(task, csv_path, tools, api_key=None):
    if not api_key:
        return _offline_run(csv_path, tools)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    model = "gpt-4o-mini"
    messages = [
        {
            "role": "system",
            "content": (
                "You are OpsPilot, a cautious business operations analyst. Use the provided tools "
                "to inspect the dataset and gather evidence before making claims. Use at least "
                "inspect_data and calculate_kpis; use other tools when useful. Never invent numbers. "
                "Distinguish measured facts from hypotheses. The only allowed actions are the listed "
                "read-only analysis tools. Finish with a concise evidence-based business report and "
                "recommendations. The CSV path is supplied by the application."
            ),
        },
        {"role": "user", "content": f"Dataset path: {csv_path}\nBusiness task: {task}"},
    ]
    action_log = []
    tool_results = []
    calls_made = 0

    while calls_made < MAX_TOOL_CALLS:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            final_text = message.content or "The model returned no final report."
            tool_results.append({"tool": "final_analysis", "summary": final_text, "data": {"text": final_text}})
            action_log.append({"tool": "final_analysis", "status": "success", "result": final_text, "mode": "llm"})
            return tool_results, action_log

        messages.append(message)
        for call in message.tool_calls:
            if calls_made >= MAX_TOOL_CALLS:
                break
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
                # The program controls the input path; the model cannot choose another file.
                arguments["csv_path"] = csv_path
                if name not in tools:
                    raise ValueError(f"Tool is not permitted: {name}")
                result = tools[name](**arguments)
                result_text = json.dumps(result, ensure_ascii=False)
                tool_results.append({"tool": name, "summary": result_text, "data": result})
                action_log.append({"tool": name, "status": "success", "arguments": arguments, "result": result, "mode": "llm"})
            except Exception as exc:
                result_text = json.dumps({"error": str(exc)})
                action_log.append({"tool": name, "status": "error", "result": {"error": str(exc)}, "mode": "llm"})
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result_text,
            })
            calls_made += 1

    messages.append({"role": "user", "content": "The tool-call limit has been reached. Summarize only the evidence already gathered and state any limitations."})
    response = client.chat.completions.create(model=model, messages=messages, temperature=0)
    final_text = response.choices[0].message.content or "No final report returned."
    tool_results.append({"tool": "final_analysis", "summary": final_text, "data": {"text": final_text}})
    action_log.append({"tool": "final_analysis", "status": "success", "result": final_text, "mode": "llm"})
    return tool_results, action_log
