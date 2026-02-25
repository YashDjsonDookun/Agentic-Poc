"""
Closer (3.4): when healthy or human mark resolved, close incident, update ticket, optional notify.
"""
from integrations import jira, servicenow
from shared import audit


async def close_incident_and_ticket(incident_id: str, ticket_id: str, ticket_system: str) -> bool:
    """Update ticket to closed/resolved; log."""
    if ticket_system == "jira":
        ok = await jira.transition(ticket_id, "Done")
    elif ticket_system == "servicenow":
        ok = await servicenow.close_incident(ticket_id)
    else:
        ok = False
    audit.log_simple("triage", "incident_closed", incident_id, "success" if ok else "no_ticket")
    return ok
