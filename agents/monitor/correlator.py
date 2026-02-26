"""
Correlator (5.C): detect similar open incidents and group under a parent (master) ticket.
Similarity: same service + overlapping metric type within a configurable time window.
When >= 2 similar open incidents exist without a parent, create a parent incident in SNOW.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from shared.config_loader import DATA_DIR
from shared import audit

INCIDENTS_CSV = DATA_DIR / "incidents" / "incidents.csv"
CORRELATION_WINDOW_MINUTES = 30


def _load_open_incidents() -> list[dict]:
    if not INCIDENTS_CSV.exists():
        return []
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if (r.get("status") or "open").lower() != "closed"]


def _extract_metric_type(summary: str) -> str:
    """Extract a rough metric keyword from the summary for grouping."""
    s = summary.lower()
    for kw in ("cpu", "memory", "error", "latency", "down", "unavailable"):
        if kw in s:
            return kw
    return "general"


def _is_recent(ts_str: str, window_min: int = CORRELATION_WINDOW_MINUTES) -> bool:
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts) < timedelta(minutes=window_min)
    except (ValueError, TypeError):
        return False


def find_similar_open(
    service: str,
    summary: str,
    exclude_id: str = "",
) -> list[dict]:
    """Find open incidents with the same service and overlapping theme within the time window."""
    target_metric = _extract_metric_type(summary)
    matches = []
    for inc in _load_open_incidents():
        if inc.get("incident_id") == exclude_id:
            continue
        if inc.get("service", "").lower() != service.lower():
            continue
        inc_metric = _extract_metric_type(inc.get("summary", ""))
        if inc_metric != target_metric:
            continue
        if not _is_recent(inc.get("timestamp", "")):
            continue
        matches.append(inc)
    return matches


def get_existing_parent(service: str, summary: str) -> Optional[dict]:
    """Check if any open incident is already a parent for this service + theme."""
    target_metric = _extract_metric_type(summary)
    for inc in _load_open_incidents():
        if inc.get("service", "").lower() != service.lower():
            continue
        if _extract_metric_type(inc.get("summary", "")) != target_metric:
            continue
        pid = (inc.get("parent_incident_id") or "").strip()
        if pid == "SELF":
            return inc
    return None


def mark_as_parent(incident_id: str) -> None:
    """Set parent_incident_id=SELF on an incident row to mark it as a master ticket."""
    _update_field(incident_id, "parent_incident_id", "SELF")


def set_parent(child_id: str, parent_id: str, parent_ticket: str = "") -> None:
    """Link a child incident to a parent."""
    _update_field(child_id, "parent_incident_id", parent_id)
    if parent_ticket:
        _update_field(child_id, "parent_ticket_number", parent_ticket)


def _update_field(incident_id: str, field: str, value: str) -> None:
    if not INCIDENTS_CSV.exists():
        return
    rows = []
    fieldnames: list[str] = []
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if field not in fieldnames:
            fieldnames.append(field)
        for row in reader:
            if row.get("incident_id") == incident_id:
                row[field] = value
            for k in fieldnames:
                if k not in row:
                    row[k] = ""
            rows.append(row)
    with open(INCIDENTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def get_children(parent_incident_id: str) -> list[dict]:
    """Return all child incidents linked to the given parent_incident_id."""
    if not INCIDENTS_CSV.exists():
        return []
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        return [
            r for r in csv.DictReader(f)
            if (r.get("parent_incident_id") or "").strip() == parent_incident_id
            and r.get("incident_id") != parent_incident_id
        ]


async def correlate_and_group(
    incident_id: str,
    service: str,
    summary: str,
    severity: str,
) -> Optional[dict]:
    """Main entry: check for similar incidents. If enough exist, create or find a parent.
    Returns {parent_incident_id, parent_ticket_number, created_new_parent} or None."""
    existing_parent = get_existing_parent(service, summary)
    if existing_parent:
        parent_id = existing_parent.get("incident_id", "")
        parent_ticket = existing_parent.get("ticket_number", "")
        set_parent(incident_id, parent_id, parent_ticket)
        return {
            "parent_incident_id": parent_id,
            "parent_ticket_number": parent_ticket,
            "created_new_parent": False,
        }

    similar = find_similar_open(service, summary, exclude_id=incident_id)
    if len(similar) < 1:
        return None

    from integrations import servicenow
    parent_ticket_number = ""
    parent_sys_id = ""

    if servicenow.is_configured():
        theme = _extract_metric_type(summary)
        parent_desc = f"Multiple related incidents for {service}: {theme}"
        result = await servicenow.create_incident(
            short_description=f"[PARENT] Multiple incidents: {theme} on {service}",
            description=parent_desc,
            urgency="1",
            impact="1",
            severity="1",
            category="Software",
        )
        if result:
            parent_sys_id = result.get("sys_id", "")
            parent_ticket_number = result.get("number", "")

    parent_inc_id = f"parent_{incident_id}"
    if similar:
        first_similar = similar[0]
        mark_as_parent(first_similar["incident_id"])
        parent_inc_id = first_similar["incident_id"]
        if parent_ticket_number:
            _update_field(parent_inc_id, "parent_ticket_number", parent_ticket_number)
            _update_field(parent_inc_id, "ticket_number", parent_ticket_number)
            _update_field(parent_inc_id, "ticket_id", parent_sys_id)

    set_parent(incident_id, parent_inc_id, parent_ticket_number)
    for s in similar:
        if s.get("incident_id") != parent_inc_id:
            set_parent(s["incident_id"], parent_inc_id, parent_ticket_number)

    audit.log_simple("correlator", "parent_created", parent_ticket_number or parent_inc_id, "success")

    return {
        "parent_incident_id": parent_inc_id,
        "parent_ticket_number": parent_ticket_number,
        "created_new_parent": True,
    }
