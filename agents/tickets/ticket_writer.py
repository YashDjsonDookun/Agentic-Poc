"""
Ticket Writer (1.5): create one ticket per incident in Jira or ServiceNow. Map severity -> priority from CSV.
Persists ticket_id and ticket_system back to the incident row in incidents.csv.
Includes category/subcategory lookup and assignment group routing.
"""
import csv
from pathlib import Path
from typing import Optional

from shared.config_loader import CONFIG_TABLES_DIR, DATA_DIR
from shared import audit
from integrations import jira, servicenow

SEVERITY_PRIORITY_PATH = CONFIG_TABLES_DIR / "severity_priority.csv"
CATEGORY_MAPPING_PATH = CONFIG_TABLES_DIR / "category_mapping.csv"
ASSIGNMENT_ROUTING_PATH = CONFIG_TABLES_DIR / "assignment_routing.csv"
INCIDENTS_CSV = DATA_DIR / "incidents" / "incidents.csv"


def _priority_for_severity(severity: str, system: str) -> str:
    """Read severity -> jira_priority from config/tables/severity_priority.csv."""
    if not SEVERITY_PRIORITY_PATH.exists():
        return "Medium" if system == "jira" else "3"
    with open(SEVERITY_PRIORITY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("severity") == severity:
                if system == "jira":
                    return row.get("jira_priority", "Medium")
    return "Medium" if system == "jira" else "3"


def _snow_fields_for_severity(severity: str) -> tuple[str, str, str]:
    """Read severity -> (urgency, impact, snow_severity) for ServiceNow from CSV.
    Defaults to (2, 2, 2) if not found."""
    if not SEVERITY_PRIORITY_PATH.exists():
        return "2", "2", "2"
    with open(SEVERITY_PRIORITY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("severity") == severity:
                return (
                    row.get("servicenow_urgency", "2"),
                    row.get("servicenow_impact", "2"),
                    row.get("servicenow_severity", "2"),
                )
    return "2", "2", "2"


def _category_for_metric(metric: str, service: str) -> tuple[str, str]:
    """Look up (category, subcategory) from category_mapping.csv.
    Falls back to ('Inquiry', 'General') when no match."""
    if not CATEGORY_MAPPING_PATH.exists():
        return "Inquiry", "General"
    metric_l = metric.lower().strip()
    service_l = service.lower().strip()
    with open(CATEGORY_MAPPING_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row_metric = (row.get("metric") or "").lower().strip()
            row_service = (row.get("service") or "").lower().strip()
            if row_metric and row_metric in metric_l:
                if not row_service or row_service in service_l:
                    return row.get("category", "Inquiry"), row.get("subcategory", "General")
    return "Inquiry", "General"


def _assignment_group_for_category(category: str, service: str) -> str:
    """Look up assignment_group_name from assignment_routing.csv.
    Returns empty string if no match (SNOW will use its default)."""
    if not ASSIGNMENT_ROUTING_PATH.exists():
        return ""
    cat_l = category.lower().strip()
    svc_l = service.lower().strip()
    with open(ASSIGNMENT_ROUTING_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row_cat = (row.get("category") or "").lower().strip()
            row_svc = (row.get("service") or "").lower().strip()
            if row_cat and row_cat in cat_l:
                if not row_svc or row_svc in svc_l:
                    return (row.get("assignment_group_name") or "").strip()
    return ""


def _update_incident_ticket(
    incident_id: str,
    ticket_id: str,
    ticket_system: str,
    ticket_number: str = "",
) -> None:
    """Update the incident row in incidents.csv with ticket_id, ticket_system, and optional ticket_number (e.g. ServiceNow INC0010001)."""
    if not INCIDENTS_CSV.exists():
        return
    rows = []
    fieldnames = None
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []
        if not fieldnames or "incident_id" not in fieldnames:
            return
        for name in ("ticket_id", "ticket_system", "ticket_number"):
            if name not in fieldnames:
                fieldnames.append(name)
        for row in reader:
            if row.get("incident_id") == incident_id:
                row["ticket_id"] = ticket_id
                row["ticket_system"] = ticket_system
                row["ticket_number"] = ticket_number or ""
            for k in fieldnames:
                if k not in row:
                    row[k] = ""
            rows.append(row)
    if fieldnames:
        with open(INCIDENTS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


async def create_ticket_for_incident(
    incident_id: str,
    service: str,
    summary: str,
    severity: str,
    description: str = "",
    metric: str = "",
) -> Optional[dict]:
    """Create ticket in Jira or ServiceNow with category and assignment group routing."""
    category, subcategory = _category_for_metric(metric, service) if metric else ("Inquiry", "General")
    assignment_group = _assignment_group_for_category(category, service)

    jira_error: Optional[str] = None
    if jira.is_configured():
        priority = _priority_for_severity(severity, "jira")
        result, err = await jira.create_issue("", summary, description, priority=priority)
        if result:
            ticket_id = result.get("key")
            audit.log_simple("sentinel", "ticket_created", ticket_id or incident_id, "success")
            out = {"ticket_id": ticket_id, "ticket_system": "jira"}
            _update_incident_ticket(incident_id, ticket_id or "", "jira")
            return out
        jira_error = err or "Jira create failed"
        audit.log_simple("sentinel", "ticket_created", incident_id, f"jira_failed:{jira_error[:80]}")

    if servicenow.is_configured():
        urgency, impact, snow_sev = _snow_fields_for_severity(severity)
        result = await servicenow.create_incident(
            summary, description,
            urgency=urgency, impact=impact, severity=snow_sev,
            category=category,
            subcategory=subcategory,
            assignment_group=assignment_group,
        )
        if result:
            ticket_id = result.get("sys_id")
            ticket_number = result.get("number") or ""
            audit.log_simple("sentinel", "ticket_created", ticket_number or ticket_id or incident_id, "success")
            out = {
                "ticket_id": ticket_id,
                "ticket_system": "servicenow",
                "ticket_number": ticket_number,
                "category": category,
                "assignment_group": assignment_group,
            }
            if jira_error:
                out["jira_error"] = jira_error
            _update_incident_ticket(incident_id, ticket_id or "", "servicenow", ticket_number)
            return out
    return None
