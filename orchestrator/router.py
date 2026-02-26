"""
Orchestrator router (0.2): receive event, log "would route to X", delegate to policy and pipelines.
Phase 2: after incident + ticket, invoke Triage (RCA, Recommender, Enricher) for ServiceNow.
Phase 3: when runbooks suggested and severity below P1, Solicitor sends approval request and store pending.
Every agent handoff is traced to data/trace/trace.csv for the Workflow UI.
"""
import os
import uuid

from shared import audit
from shared.config_loader import get_env
from shared.trace import log_step, stamp_ticket_number
from orchestrator.policy import route_phase, should_solicit
from orchestrator.approvals_store import create_pending


def _run_id() -> str:
    return f"run_{uuid.uuid4().hex[:10]}"


async def _run_triage_pipeline(run_id: str, incident, ticket: dict, step: int, t_num: str = "") -> tuple[list, int]:
    """Phase 2.1: RCA -> Recommender -> Enricher. Returns (runbooks, next_step)."""
    ticket_id = ticket.get("ticket_id")
    ticket_system = (ticket.get("ticket_system") or "").strip().lower()
    from agents.triage.rca import run_rca
    from agents.triage.recommender import suggest_runbooks
    from agents.triage.enricher import enrich_ticket

    # RCA
    log_step(run_id, incident.incident_id, step, "RCA Agent", "analyse_root_cause",
             "invoke", "Incident created with ticket — run root-cause analysis to identify hypotheses.",
             "started", ticket_number=t_num)
    hypotheses = run_rca(
        incident.incident_id, incident.service, incident.summary, {}, context=incident.context,
    )
    hyp_summary = "; ".join((h.text if hasattr(h, "text") else str(h))[:80] for h in hypotheses[:3]) if hypotheses else "none"
    log_step(run_id, incident.incident_id, step, "RCA Agent", "analyse_root_cause",
             f"{len(hypotheses)} hypotheses", f"Generated hypotheses from metric context: {hyp_summary}",
             "success", hyp_summary, ticket_number=t_num)
    step += 1

    # Recommender
    log_step(run_id, incident.incident_id, step, "Recommender", "suggest_runbooks",
             "invoke", "Search knowledge base for runbooks matching incident summary and service.",
             "started", ticket_number=t_num)
    runbooks = suggest_runbooks(incident.summary, incident.service)
    rb_names = ", ".join(r.get("name", r.get("path", "?")) for r in runbooks[:3]) if runbooks else "none"
    log_step(run_id, incident.incident_id, step, "Recommender", "suggest_runbooks",
             f"{len(runbooks)} runbooks found", f"Matched runbooks by keywords in summary/service: {rb_names}",
             "success", rb_names, ticket_number=t_num)
    step += 1

    # Enricher
    runbook_str = "; ".join(
        f"Try runbook: {r.get('name', r.get('path', ''))} ({r.get('reason', '')})" for r in runbooks
    ) if runbooks else ""
    if ticket_id and ticket_system:
        log_step(run_id, incident.incident_id, step, "Enricher", "enrich_ticket",
                 "invoke", f"Append RCA hypotheses and runbook suggestions as work notes on {ticket_system} ticket.",
                 "started", ticket_number=t_num)
        await enrich_ticket(ticket_id, ticket_system, hypotheses, runbook_str)
        log_step(run_id, incident.incident_id, step, "Enricher", "enrich_ticket",
                 "enriched", "Work notes appended with hypotheses and recommended runbooks.",
                 "success", f"ticket_id={ticket_id}", ticket_number=t_num)
    else:
        log_step(run_id, incident.incident_id, step, "Enricher", "enrich_ticket",
                 "skipped", "No ticket ID or ticket system — nothing to enrich.",
                 "skipped", ticket_number=t_num)
    step += 1

    audit.log_simple("triage", "enriched_ticket", incident.incident_id, "success")
    return runbooks, step


async def _run_monitor_pipeline(payload: dict) -> dict:
    """Phase 1: Collector -> Evaluator -> Alert Router -> Incident Creator (optional)."""
    from agents.monitor import collect, evaluate, should_create_incident, create_incident

    run_id = _run_id()
    step = 1

    # Collector
    log_step(run_id, "", step, "Collector", "normalise_event",
             "invoke", "Incoming payload received — normalise into standard event schema.",
             "started")
    ev = collect(payload)
    log_step(run_id, "", step, "Collector", "normalise_event",
             "normalised", f"Event {ev.event_id} from {ev.source}: {ev.metric}={ev.value} {ev.unit} on {ev.service}.",
             "success", ev.event_id)
    step += 1

    # Evaluator
    log_step(run_id, "", step, "Evaluator", "evaluate_thresholds",
             "invoke", "Check event metric against alert_rules.csv thresholds.",
             "started")
    decision, reason = evaluate(ev)
    log_step(run_id, "", step, "Evaluator", "evaluate_thresholds",
             decision, reason,
             "success", f"metric={ev.metric} value={ev.value}")
    step += 1

    if decision != "alert":
        log_step(run_id, "", step, "Pipeline", "end",
                 "no_alert", f"Evaluator returned '{decision}' — pipeline stops. Reason: {reason}",
                 "completed")
        return {"received": ev.event_id, "routed_to": "monitor", "decision": "no_alert", "run_id": run_id}

    # Alert Router
    log_step(run_id, "", step, "Alert Router", "check_dedup_maintenance",
             "invoke", "Alert triggered — check deduplication window and maintenance windows.",
             "started")
    create_ok, route_reason = should_create_incident(ev.service, ev.metric)
    log_step(run_id, "", step, "Alert Router", "check_dedup_maintenance",
             "create" if create_ok else "suppress",
             route_reason,
             "success" if create_ok else "suppressed")
    step += 1

    if not create_ok:
        log_step(run_id, "", step, "Pipeline", "end",
                 "suppressed", f"Alert Router suppressed: {route_reason}",
                 "completed")
        return {"received": ev.event_id, "routed_to": "monitor", "decision": "ignored", "reason": route_reason, "run_id": run_id}

    # Re-open detection — alert if a recently closed incident matches
    from agents.monitor.alert_router import check_reopen
    reopen_match = check_reopen(ev.service, ev.metric)
    if reopen_match:
        old_ticket = reopen_match.get("ticket_number") or reopen_match.get("incident_id") or "?"
        log_step(run_id, "", step, "Alert Router", "reopen_detection",
                 "reopen_alert",
                 f"Resolved incident {old_ticket} may be recurring — new event detected for "
                 f"{ev.service}/{ev.metric}.",
                 "warning", f"old_ticket={old_ticket}")
        audit.log_simple("alert_router", "reopen_detected", old_ticket, "warning")
        from integrations.teams import is_configured as teams_configured, send_message
        if teams_configured():
            try:
                await send_message(
                    f"⚠️ **Re-open alert**: Resolved incident **{old_ticket}** may be recurring.\n"
                    f"New event: {ev.metric}={ev.value} on {ev.service}."
                )
            except Exception:
                pass
        step += 1

    # Incident Creator
    summary = ev.extra.get("summary") or f"{ev.metric} {ev.value} {ev.unit}"
    log_step(run_id, "", step, "Incident Creator", "create_incident",
             "invoke", f"Threshold breached and no suppression — create incident for {ev.service}.",
             "started")
    incident = create_incident(
        service=ev.service, summary=summary,
        context={"metric": ev.metric, "value": ev.value, "event_id": ev.event_id},
        metric=ev.metric, value=ev.value,
    )
    log_step(run_id, incident.incident_id, step, "Incident Creator", "create_incident",
             "created", f"Incident {incident.incident_id} created with severity={incident.severity} for {incident.service}.",
             "success", f"severity={incident.severity}")
    step += 1

    # Correlator — check for similar open incidents, group under master
    from agents.monitor.correlator import correlate_and_group
    log_step(run_id, incident.incident_id, step, "Correlator", "correlate_incidents",
             "invoke", "Scanning open incidents for similar service + metric to detect correlated issues.",
             "started")
    correlation = await correlate_and_group(
        incident.incident_id, incident.service, incident.summary, incident.severity,
    )
    if correlation:
        p_id = correlation.get("parent_incident_id", "")
        p_ticket = correlation.get("parent_ticket_number", "")
        new_parent = correlation.get("created_new_parent", False)
        rationale = (
            f"{'Created new' if new_parent else 'Found existing'} parent {p_ticket or p_id}. "
            f"Incident linked as child."
        )
        log_step(run_id, incident.incident_id, step, "Correlator", "correlate_incidents",
                 "correlated", rationale, "success", f"parent={p_ticket or p_id}")
    else:
        log_step(run_id, incident.incident_id, step, "Correlator", "correlate_incidents",
                 "no_match", "No similar open incidents found within the correlation window.",
                 "success")
    step += 1

    # Notifier
    from agents.notify import notify_incident
    log_step(run_id, incident.incident_id, step, "Notifier", "send_notifications",
             "invoke", "Notify configured channels (Teams, email) about new incident.",
             "started")
    await notify_incident(incident.incident_id, incident.service, incident.summary, incident.severity)
    log_step(run_id, incident.incident_id, step, "Notifier", "send_notifications",
             "notified", "Notification dispatched to configured channels.",
             "success")
    step += 1

    # Ticket Writer
    from agents.tickets import create_ticket_for_incident
    inc_metric = (incident.context or {}).get("metric", "") if hasattr(incident, "context") and isinstance(incident.context, dict) else ""
    log_step(run_id, incident.incident_id, step, "Ticket Writer", "create_ticket",
             "invoke", "Create ITSM ticket (ServiceNow / Jira) mapped from severity, category, and assignment group.",
             "started")
    ticket = await create_ticket_for_incident(
        incident.incident_id, incident.service, incident.summary, incident.severity,
        description=str(incident.context),
        metric=inc_metric,
    )
    t_num = ""
    if ticket:
        t_num = ticket.get("ticket_number") or ticket.get("ticket_id") or ""
        t_sys = ticket.get("ticket_system", "")
        log_step(run_id, incident.incident_id, step, "Ticket Writer", "create_ticket",
                 "created", f"Ticket {t_num} created in {t_sys}. Severity mapped to urgency/impact/severity fields.",
                 "success", f"{t_sys}:{t_num}", ticket_number=t_num)
        stamp_ticket_number(run_id, t_num)
    else:
        log_step(run_id, incident.incident_id, step, "Ticket Writer", "create_ticket",
                 "failed", "No ITSM integration configured or API call failed.",
                 "failed")
    step += 1

    # Triage pipeline
    runbooks = []
    if ticket:
        runbooks, step = await _run_triage_pipeline(run_id, incident, ticket, step, t_num=t_num)

    # Solicitor (Phase 3.1)
    if ticket and runbooks and should_solicit(incident.severity, runbooks):
        log_step(run_id, incident.incident_id, step, "Solicitor", "request_approval",
                 "invoke",
                 f"Severity is '{incident.severity}' (not critical/P1) and {len(runbooks)} runbook(s) suggested — "
                 "human approval required before execution.",
                 "started", ticket_number=t_num)
        action_suggestion = "; ".join(
            f"Run runbook: {r.get('name', r.get('path', ''))} ({r.get('reason', '')})" for r in runbooks[:1]
        )
        request_id = create_pending(
            incident.incident_id, action_suggestion,
            ticket.get("ticket_id") or "", ticket.get("ticket_system") or "",
        )
        base_url = (get_env("ORCHESTRATOR_BASE_URL") or os.environ.get("ORCHESTRATOR_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        callback_url = f"{base_url}/webhooks/approval?request_id={request_id}"
        from agents.triage.solicitor import request_approval
        sent = await request_approval(incident.incident_id, action_suggestion, callback_url)
        outcome = "success" if sent else "skipped_no_channel"
        rationale = ("Approval request sent to Teams/email." if sent
                     else "No notification channel configured — approval request stored but not dispatched.")
        log_step(run_id, incident.incident_id, step, "Solicitor", "request_approval",
                 "sent" if sent else "no_channel", rationale, outcome, f"request_id={request_id}",
                 ticket_number=t_num)
        audit.log_simple("triage", "solicit_sent", incident.incident_id, outcome)
        step += 1
    elif ticket and runbooks:
        log_step(run_id, incident.incident_id, step, "Solicitor", "request_approval",
                 "skipped",
                 f"Severity is '{incident.severity}' (critical/P1) — auto-execute without human approval.",
                 "skipped", ticket_number=t_num)
        step += 1

    # Pipeline complete
    log_step(run_id, incident.incident_id, step, "Pipeline", "end",
             "completed", "All pipeline phases executed.", "completed", ticket_number=t_num)

    return {
        "received": ev.event_id,
        "routed_to": "monitor",
        "decision": "incident_created",
        "incident_id": incident.incident_id,
        "ticket": ticket,
        "run_id": run_id,
    }


async def handle_event(event: dict) -> dict:
    """Single entry point: receive event, route by policy, run phase pipeline."""
    event_id = event.get("event_id", "unknown")
    event_type = event.get("type", "simulated")
    payload = event if event_type == "simulated" else event.get("payload", event)
    audit.log_simple("conductor", "received_event", event_id, "logged")
    phase = route_phase(event_type, payload)
    if phase == "monitor":
        return await _run_monitor_pipeline(payload)
    return {"received": event_id, "routed_to": phase}
