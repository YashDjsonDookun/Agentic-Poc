"""
Ticket Updater (3.3): on approval/execution, add comment to Jira/ServiceNow; optionally transition status.
"""
from integrations import jira, servicenow


async def update_ticket(ticket_id: str, ticket_system: str, comment: str, transition: str | None = None) -> bool:
    """Add comment; optionally transition (e.g. In Progress -> Resolved)."""
    if ticket_system == "jira":
        ok = await jira.add_comment(ticket_id, comment)
        if ok and transition:
            await jira.transition(ticket_id, transition)
        return ok
    if ticket_system == "servicenow":
        return await servicenow.update_work_notes(ticket_id, comment)
    return False
