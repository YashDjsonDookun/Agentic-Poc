"""
Solicitor (3.1): send approval request via Adaptive Card to Teams or email. Store decision.
"""
from integrations.teams import send_message
from integrations.smtp import send_email


async def request_approval(incident_id: str, action_suggestion: str, callback_url: str) -> bool:
    """Send approval request (Teams card or email). Decision handled by webhook."""
    text = f"Approve action for incident {incident_id}: {action_suggestion}"
    sent = await send_message(text)
    if not sent:
        sent = await send_email("ops@example.com", f"Approval: {incident_id}", text)
    return sent
