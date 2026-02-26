"""
Closer (3.4): when healthy or human mark resolved, close incident, update ticket, optional notify.
Uses ticket_id (sys_id for ServiceNow) for API calls; logs entity_id as ticket_number when present for visibility.
"""
from integrations import jira, servicenow
from shared import audit


async def close_incident_and_ticket(
    incident_id: str,
    ticket_id: str,
    ticket_system: str,
    ticket_number: str = "",
) -> bool:
    """Update ticket to closed/resolved; log. ticket_id = sys_id for ServiceNow (required for API)."""
    entity_id = (ticket_number or ticket_id or incident_id).strip()
    ts = (ticket_system or "").strip().lower()

    if ts == "jira":
        ok = await jira.transition(ticket_id, "Done")
        outcome = "success" if ok else "no_ticket"
    elif ts == "servicenow":
        if not (ticket_id and ticket_id.strip()):
            outcome = "no_ticket: missing ticket_id (sys_id) in incident row"
            ok = False
        else:
            ok, msg = await servicenow.close_incident(ticket_id)
            outcome = "success" if ok else f"no_ticket: {msg}"
    else:
        ok = False
        outcome = "no_ticket: unknown ticket_system or none"
    audit.log_simple("triage", "incident_closed", entity_id, outcome)
    return ok
