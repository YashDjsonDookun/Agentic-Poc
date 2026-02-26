"""
Pipeline trace logger — records each agent step with decision, rationale, and outcome.
Written to data/trace/trace.csv for real-time UI consumption.
ticket_number is stamped onto all rows for a run once the ITSM ticket is created.
"""
import csv
from pathlib import Path
from datetime import datetime, timezone

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACE_PATH = _PROJECT_ROOT / "data" / "trace" / "trace.csv"

FIELDS = [
    "timestamp",
    "run_id",
    "incident_id",
    "ticket_number",
    "step_order",
    "agent",
    "action",
    "decision",
    "rationale",
    "outcome",
    "detail",
]


def _ensure_dir():
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_step(
    run_id: str,
    incident_id: str,
    step_order: int,
    agent: str,
    action: str,
    decision: str,
    rationale: str,
    outcome: str = "",
    detail: str = "",
    ticket_number: str = "",
) -> None:
    """Append a single pipeline step to the trace CSV."""
    _ensure_dir()
    row = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "incident_id": incident_id,
        "ticket_number": ticket_number,
        "step_order": step_order,
        "agent": agent,
        "action": action,
        "decision": decision,
        "rationale": rationale,
        "outcome": outcome,
        "detail": detail,
    }
    file_exists = TRACE_PATH.exists()
    with open(TRACE_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def get_run_id_for_incident(incident_id: str) -> str:
    """Return the most recent run_id associated with an incident_id, or ''."""
    if not TRACE_PATH.exists() or not incident_id:
        return ""
    last_run = ""
    with open(TRACE_PATH, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("incident_id") == incident_id:
                last_run = row.get("run_id", "")
    return last_run


def get_max_step(run_id: str) -> int:
    """Return the highest step_order for a given run_id."""
    if not TRACE_PATH.exists() or not run_id:
        return 0
    mx = 0
    with open(TRACE_PATH, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("run_id") == run_id:
                try:
                    mx = max(mx, int(row.get("step_order", 0)))
                except (ValueError, TypeError):
                    pass
    return mx


def stamp_ticket_number(run_id: str, ticket_number: str) -> None:
    """Backfill ticket_number on all rows for the given run_id."""
    if not TRACE_PATH.exists() or not ticket_number:
        return
    rows = []
    with open(TRACE_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "ticket_number" not in fieldnames:
            fieldnames.insert(fieldnames.index("step_order") if "step_order" in fieldnames else 3, "ticket_number")
        for row in reader:
            if row.get("run_id") == run_id:
                row["ticket_number"] = ticket_number
            for k in fieldnames:
                if k not in row:
                    row[k] = ""
            rows.append(row)
    with open(TRACE_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
