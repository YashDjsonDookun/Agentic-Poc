"""
Enricher (2.3): take RCA output; update ticket in Jira/ServiceNow (description, runbook link).
"""
from agents.triage.rca import Hypothesis
from integrations import jira, servicenow


async def enrich_ticket(ticket_id: str, ticket_system: str, hypotheses: list[Hypothesis], runbook_link: str = "") -> bool:
    """Update ticket with RCA summary and optional runbook link."""
    body = "\n".join(f"- {h.text} (confidence: {h.confidence})" for h in hypotheses)
    if runbook_link:
        body += f"\nRunbook: {runbook_link}"
    if ticket_system == "jira":
        return await jira.add_comment(ticket_id, body)
    if ticket_system == "servicenow":
        return await servicenow.update_work_notes(ticket_id, body)
    return False
