"""
Orchestrator router (0.2): receive event, log "would route to X", delegate to policy and pipelines.
"""
from shared import audit
from orchestrator.policy import route_phase


async def _run_monitor_pipeline(payload: dict) -> dict:
    """Phase 1: Collector -> Evaluator -> Alert Router -> Incident Creator (optional)."""
    from agents.monitor import collect, evaluate, should_create_incident, create_incident

    ev = collect(payload)
    decision, reason = evaluate(ev)
    if decision != "alert":
        return {"received": ev.event_id, "routed_to": "monitor", "decision": "no_alert"}
    create_ok, route_reason = should_create_incident(ev.service, ev.metric)
    if not create_ok:
        return {"received": ev.event_id, "routed_to": "monitor", "decision": "ignored", "reason": route_reason}
    summary = ev.extra.get("summary") or f"{ev.metric} {ev.value} {ev.unit}"
    incident = create_incident(
        service=ev.service,
        summary=summary,
        context={"metric": ev.metric, "value": ev.value, "event_id": ev.event_id},
        metric=ev.metric,
        value=ev.value,
    )
    # Optional: notify and create ticket (1.4, 1.5)
    from agents.notify import notify_incident
    from agents.tickets import create_ticket_for_incident
    await notify_incident(incident.incident_id, incident.service, incident.summary, incident.severity)
    ticket = await create_ticket_for_incident(
        incident.incident_id, incident.service, incident.summary, incident.severity,
        description=str(incident.context),
    )
    return {
        "received": ev.event_id,
        "routed_to": "monitor",
        "decision": "incident_created",
        "incident_id": incident.incident_id,
        "ticket": ticket,
    }


async def handle_event(event: dict) -> dict:
    """
    Single entry point: receive event, route by policy, run phase pipeline.
    """
    event_id = event.get("event_id", "unknown")
    event_type = event.get("type", "simulated")
    payload = event if event_type == "simulated" else event.get("payload", event)
    audit.log_simple("conductor", "received_event", event_id, "logged")
    phase = route_phase(event_type, payload)
    if phase == "monitor":
        return await _run_monitor_pipeline(payload)
    return {"received": event_id, "routed_to": phase}
