"""
Notifier (1.4): on new incident, send one notification (Teams or email). Config-driven.
"""
from integrations.teams import is_configured as teams_configured, send_message as teams_send
from integrations.smtp import is_configured as smtp_configured, send_email as smtp_send


async def notify_incident(incident_id: str, service: str, summary: str, severity: str) -> bool:
    """Send one notification (Teams preferred, else email if configured)."""
    text = f"[{severity}] {service}: {summary} (incident_id={incident_id})"
    if teams_configured():
        return await teams_send(text)
    if smtp_configured():
        # Would need configured "to" address from config
        return await smtp_send("ops@example.com", f"Incident: {incident_id}", text)
    return False
