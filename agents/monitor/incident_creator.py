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
    """Simple mapping: high value -> higher severity."""
    if "error" in metric or "up" in metric:
        return "high" if value > 0.1 or value == 0 else "medium"
    if "percent" in metric or "rate" in metric:
        if value >= 95:
            return "critical"
        if value >= 80:
            return "high"
        if value >= 60:
            return "medium"
    return "low"


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
    }
    file_exists = INCIDENTS_CSV.exists()
    with open(INCIDENTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            w.writeheader()
        w.writerow(row)
    audit.log_simple("sentinel", "incident_created", incident_id, "success")
    return incident
