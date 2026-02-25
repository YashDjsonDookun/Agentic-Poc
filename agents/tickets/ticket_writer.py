"""
Ticket Writer (1.5): create one ticket per incident in Jira or ServiceNow. Map severity -> priority from CSV.
"""
import csv
from pathlib import Path
from typing import Optional

from shared.config_loader import CONFIG_TABLES_DIR
from shared import audit
from integrations import jira, servicenow

SEVERITY_PRIORITY_PATH = CONFIG_TABLES_DIR / "severity_priority.csv"


def _priority_for_severity(severity: str, system: str) -> str:
    """Read severity -> priority from config/tables/severity_priority.csv."""
    if not SEVERITY_PRIORITY_PATH.exists():
        return "Medium" if system == "jira" else "3"
    with open(SEVERITY_PRIORITY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("severity") == severity:
                return row.get(f"{system}_priority", row.get("jira_priority", "Medium"))
    return "Medium" if system == "jira" else "3"


async def create_ticket_for_incident(
    incident_id: str,
    service: str,
    summary: str,
    severity: str,
    description: str = "",
) -> Optional[dict]:
    """Create ticket in Jira or ServiceNow (whichever is configured). Returns {ticket_id, ticket_system}."""
    if jira.is_configured():
        priority = _priority_for_severity(severity, "jira")
        result = await jira.create_issue("", summary, description, priority=priority)
        if result:
            audit.log_simple("sentinel", "ticket_created", result.get("key", incident_id), "success")
            return {"ticket_id": result.get("key"), "ticket_system": "jira"}
    if servicenow.is_configured():
        priority = _priority_for_severity(severity, "servicenow")
        result = await servicenow.create_incident(summary, description, priority=priority)
        if result:
            audit.log_simple("sentinel", "ticket_created", result.get("sys_id", incident_id), "success")
            return {"ticket_id": result.get("sys_id"), "ticket_system": "servicenow"}
    return None
