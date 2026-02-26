"""
Incident Creator (1.3): create incident record; persist to CSV (no DB).
"""
import csv
import uuid
from pathlib import Path
from datetime import datetime, timezone

from shared.schema import Incident
from shared.config_loader import DATA_DIR
from shared import audit

INCIDENTS_DIR = DATA_DIR / "incidents"
INCIDENTS_CSV = INCIDENTS_DIR / "incidents.csv"


def _ensure_incidents_dir():
    INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)


def _infer_severity(metric: str, value: float) -> str:
    """Map metric + value to severity.  Covers cpu_percent, memory_percent,
    error_rate, up (bool), and latency_p99_ms from the simulator."""
    m = metric.lower()
    if m == "up":
        return "critical" if value == 0 else "low"
    if "error" in m:
        if value >= 0.20:
            return "critical"
        if value >= 0.10:
            return "high"
        return "medium" if value >= 0.05 else "low"
    if "latency" in m or m.endswith("_ms"):
        if value >= 3000:
            return "critical"
        if value >= 1500:
            return "high"
        if value >= 800:
            return "medium"
        return "low"
    if "percent" in m or "rate" in m:
        if value >= 95:
            return "critical"
        if value >= 80:
            return "high"
        if value >= 60:
            return "medium"
        return "low"
    return "medium"


def create_incident(
    service: str,
    summary: str,
    context: dict | None = None,
    severity: str | None = None,
    metric: str = "",
    value: float = 0,
) -> Incident:
    """Create incident and append to incidents CSV."""
    _ensure_incidents_dir()
    incident_id = f"inc_{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if severity is None:
        severity = _infer_severity(metric, value)
    incident = Incident(
        incident_id=incident_id,
        severity=severity,
        service=service,
        summary=summary,
        timestamp=ts,
        context=context or {},
    )
    row = {
        "incident_id": incident_id,
        "severity": severity,
        "service": service,
        "summary": summary,
        "timestamp": ts,
        "ticket_id": "",
        "ticket_system": "",
        "ticket_number": "",
        "status": "open",
    }
    file_exists = INCIDENTS_CSV.exists()
    with open(INCIDENTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            w.writeheader()
        w.writerow(row)
    audit.log_simple("sentinel", "incident_created", incident_id, "success")
    return incident


def get_incident_row(incident_id: str) -> dict | None:
    """Return the incident row as dict (including ticket_id, ticket_system, status if present) or None."""
    if not INCIDENTS_CSV.exists():
        return None
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("incident_id") == incident_id:
                if "status" not in row:
                    row["status"] = "open"
                return row
    return None


def set_incident_status(incident_id: str, status: str) -> bool:
    """Update incident row status (e.g. closed). Returns True if updated."""
    if not INCIDENTS_CSV.exists():
        return False
    rows = []
    fieldnames = None
    updated = False
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "status" not in fieldnames:
            fieldnames.append("status")
        for row in reader:
            if row.get("incident_id") == incident_id:
                row["status"] = status
                updated = True
            if "status" not in row:
                row["status"] = "open"
            rows.append(row)
    if not updated or not fieldnames:
        return False
    with open(INCIDENTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return True
