"""
Persist approval requests and decisions (Phase 3.1). data/approvals.csv keyed by request_id / incident_id.
"""
import csv
import uuid
from pathlib import Path
from datetime import datetime, timezone

from shared.config_loader import DATA_DIR

APPROVALS_CSV = DATA_DIR / "approvals.csv"
FIELDS = ("request_id", "incident_id", "action_suggestion", "action_type", "ticket_id", "ticket_system", "status", "created_at", "decided_at")


def _ensure_dir():
    APPROVALS_CSV.parent.mkdir(parents=True, exist_ok=True)


def create_pending(incident_id: str, action_suggestion: str, ticket_id: str, ticket_system: str) -> str:
    """Append a pending approval row. Returns request_id."""
    _ensure_dir()
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    action_type = "run_runbook"  # single safe action type for Phase 3
    row = {
        "request_id": request_id,
        "incident_id": incident_id,
        "action_suggestion": action_suggestion,
        "action_type": action_type,
        "ticket_id": ticket_id or "",
        "ticket_system": ticket_system or "",
        "status": "pending",
        "created_at": ts,
        "decided_at": "",
    }
    file_exists = APPROVALS_CSV.exists()
    with open(APPROVALS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)
    return request_id


def get_pending_by_request(request_id: str) -> dict | None:
    """Return approval row if status is pending, else None."""
    if not APPROVALS_CSV.exists():
        return None
    with open(APPROVALS_CSV, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("request_id") == request_id and row.get("status") == "pending":
                return row
    return None


def get_pending_by_incident(incident_id: str) -> dict | None:
    """Return first pending approval for incident_id."""
    if not APPROVALS_CSV.exists():
        return None
    with open(APPROVALS_CSV, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("incident_id") == incident_id and row.get("status") == "pending":
                return row
    return None


def record_decision(request_id: str, decision: str) -> bool:
    """Update row to approved or rejected; set decided_at. Returns True if updated."""
    if decision not in ("approve", "reject") or not APPROVALS_CSV.exists():
        return False
    status = "approved" if decision == "approve" else "rejected"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    fieldnames = None
    updated = False
    with open(APPROVALS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or list(FIELDS)
        for row in reader:
            if row.get("request_id") == request_id:
                row["status"] = status
                row["decided_at"] = ts
                updated = True
            rows.append(row)
    if not updated:
        return False
    with open(APPROVALS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return True
