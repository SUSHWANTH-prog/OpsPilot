"""Small, testable tools used by OpsPilot. Uses Python's built-in CSV library."""
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def _read_rows(csv_path):
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no header row.")
        rows = list(reader)
        if not rows:
            raise ValueError("CSV contains headers but no data rows.")
        return [name.strip() for name in reader.fieldnames], rows

def _number(value, field_name, row_number):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid number in '{field_name}' at data row {row_number}: {value!r}")

def _parse_date(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported or invalid date: {value!r}. Use YYYY-MM-DD.")

def _required(headers, required):
    normalized = {h.strip().lower(): h for h in headers}
    missing = [name for name in required if name not in normalized]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. Available columns: {headers}")
    return {name: normalized[name] for name in required}

def inspect_data(csv_path):
    headers, rows = _read_rows(csv_path)
    dates = []
    issues = []
    for i, row in enumerate(rows, start=2):
        if any(value is None or str(value).strip() == "" for value in row.values()):
            issues.append(f"Row {i} contains one or more blank values.")
        if row.get("date", "").strip():
            try:
                dates.append(_parse_date(row["date"]))
            except ValueError as exc:
                issues.append(f"Row {i}: {exc}")
    return {
        "row_count": len(rows),
        "columns": headers,
        "date_range": {"start": str(min(dates)), "end": str(max(dates))} if dates else None,
        "quality_issue_count": len(issues),
        "quality_issues": issues[:10],
    }

def calculate_kpis(csv_path):
    headers, rows = _read_rows(csv_path)
    cols = _required(headers, ["revenue"])
    revenue_col = cols["revenue"]
    revenues = [_number(row.get(revenue_col), revenue_col, i) for i, row in enumerate(rows, start=2)]
    dates = []
    date_col = next((h for h in headers if h.lower() == "date"), None)
    if date_col:
        for row in rows:
            dates.append(_parse_date(row.get(date_col)))
    total = sum(revenues)
    return {
        "row_count": len(rows),
        "total_revenue": round(total, 2),
        "average_revenue_per_row": round(total / len(rows), 2),
        "date_range": {"start": str(min(dates)), "end": str(max(dates))} if dates else None,
        "calculation": "Revenue values were summed from the CSV; average is total revenue divided by row count.",
    }

def compare_periods(csv_path):
    headers, rows = _read_rows(csv_path)
    cols = _required(headers, ["date", "revenue"])
    date_col, revenue_col = cols["date"], cols["revenue"]
    totals = defaultdict(float)
    for i, row in enumerate(rows, start=2):
        date = _parse_date(row.get(date_col))
        month = date.strftime("%Y-%m")
        totals[month] += _number(row.get(revenue_col), revenue_col, i)
    months = sorted(totals)
    if len(months) < 2:
        return {"message": "At least two different months are required for a month-to-month comparison.", "monthly_revenue": {m: round(totals[m], 2) for m in months}}
    first, last = months[0], months[-1]
    change = totals[last] - totals[first]
    pct = (change / totals[first] * 100) if totals[first] else None
    return {
        "earliest_month": first,
        "earliest_revenue": round(totals[first], 2),
        "latest_month": last,
        "latest_revenue": round(totals[last], 2),
        "change": round(change, 2),
        "percentage_change": round(pct, 2) if pct is not None else None,
        "monthly_revenue": {m: round(totals[m], 2) for m in months},
        "method": "Compares the earliest and latest month present in the dataset; it does not prove why a change occurred.",
    }

def revenue_by_category(csv_path):
    headers, rows = _read_rows(csv_path)
    cols = _required(headers, ["category", "revenue"])
    category_col, revenue_col = cols["category"], cols["revenue"]
    totals = defaultdict(float)
    for i, row in enumerate(rows, start=2):
        category = (row.get(category_col) or "").strip() or "Unknown"
        totals[category] += _number(row.get(revenue_col), revenue_col, i)
    return {"revenue_by_category": {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda item: item[1], reverse=True)}}

def verify_report(findings, csv_path):
    """Independent sanity check: recompute total revenue and check it is finite."""
    import math
    kpis = calculate_kpis(csv_path)
    total = kpis["total_revenue"]
    passed = math.isfinite(total)
    return {
        "passed": passed,
        "checks": ["Recomputed total revenue directly from CSV", "Checked total revenue is a finite number"],
        "recomputed_total_revenue": total,
        "message": "Verification passed." if passed else "Verification failed: total revenue is not finite.",
    }

def write_report(task, findings, action_log, verification, output_path):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# OpsPilot Business Analysis Report",
        "",
        f"**Business objective:** {task}",
        "",
        "## Findings",
        "",
    ]
    for item in findings:
        summary = item.get("summary", str(item))
        lines.extend([f"### {item.get('tool', 'Finding').replace('_', ' ').title()}", "", str(summary), ""])
    lines.extend([
        "## Verification",
        "",
        f"- Status: {'PASS' if verification['passed'] else 'FAIL'}",
        f"- Recomputed total revenue: {verification['recomputed_total_revenue']}",
        f"- Checks: {', '.join(verification['checks'])}",
        "",
        "## Limitations",
        "",
        "- Revenue changes show patterns in the supplied data; they do not establish causation.",
        "- Recommendations should be reviewed by a person before consequential business decisions.",
        "",
        "## Action log",
        "",
        "See `action_log.json` for the tool-by-tool execution record.",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")
    log_path = output.parent / "action_log.json"
    log_path.write_text(json.dumps(action_log, indent=2, ensure_ascii=False), encoding="utf-8")
    return output
