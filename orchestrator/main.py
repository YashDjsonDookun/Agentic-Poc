"""
Orchestrator entry point (0.2): FastAPI app, async, single entry for events.
Phase 3.4: Close incident API.
Phase 4: Chronicler (doc-gen) triggered on close and via manual endpoint.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from orchestrator.router import handle_event
from orchestrator.webhooks import router as webhooks_router

app = FastAPI(title="SENTRY/ARGUS Orchestrator", version="0.1.0")
app.include_router(webhooks_router)


class EventIn(BaseModel):
    event_id: Optional[str] = None
    type: str = "simulated"
    payload: Optional[dict] = None


@app.post("/events")
async def post_event(event: EventIn):
    """Receive events (simulator or external); route via orchestrator."""
    payload = event.payload or {}
    body = {"event_id": event.event_id or payload.get("event_id", "unknown"), "type": event.type, **payload}
    return await handle_event(body)


@app.post("/incidents/{incident_id}/close")
async def close_incident(incident_id: str):
    """Close incident and ticket; mark incident status closed; auto-trigger Chronicler."""
    from agents.monitor.incident_creator import get_incident_row, set_incident_status
    from agents.triage.closer import close_incident_and_ticket
    from shared.trace import log_step, get_run_id_for_incident, get_max_step
    from orchestrator.chronicler_pipeline import run_chronicler

    row = get_incident_row(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    if (row.get("status") or "open").lower() == "closed":
        return {"status": "already_closed", "incident_id": incident_id}

    ticket_id = (row.get("ticket_id") or "").strip()
    ticket_system = (row.get("ticket_system") or "").strip().lower()
    ticket_number = (row.get("ticket_number") or "").strip()

    run_id = get_run_id_for_incident(incident_id)
    step = get_max_step(run_id) + 1 if run_id else 1

    log_step(run_id, incident_id, step, "Closer", "close_incident",
             "invoke",
             f"Manual close requested for {ticket_number or incident_id}. "
             f"Will resolve + stop SLA + close on {ticket_system or 'N/A'}.",
             "started", ticket_number=ticket_number)

    ok = await close_incident_and_ticket(incident_id, ticket_id, ticket_system, ticket_number)
    step += 1

    if ok:
        log_step(run_id, incident_id, step, "Closer", "close_incident",
                 "closed",
                 f"Ticket {ticket_number or ticket_id} resolved, SLA stopped, and closed on {ticket_system}.",
                 "success", f"{ticket_system}:{ticket_number or ticket_id}",
                 ticket_number=ticket_number)
    else:
        log_step(run_id, incident_id, step, "Closer", "close_incident",
                 "failed",
                 f"Could not close {ticket_number or ticket_id} on {ticket_system}. "
                 "Check audit logs for detailed ServiceNow/Jira error.",
                 "failed", f"{ticket_system}:{ticket_number or ticket_id}",
                 ticket_number=ticket_number)

    set_incident_status(incident_id, "closed")
    step += 1

    log_step(run_id, incident_id, step, "Pipeline", "close_complete",
             "completed",
             f"Incident {ticket_number or incident_id} marked closed locally."
             + (" ITSM ticket also closed." if ok else " ITSM close failed — see audit logs."),
             "completed", ticket_number=ticket_number)

    # Auto-trigger Chronicler after close
    try:
        await run_chronicler(incident_id=incident_id, ticket_number=ticket_number)
    except Exception:
        pass

    return {"status": "closed", "incident_id": incident_id, "ticket_updated": ok}


@app.post("/incidents/{incident_id}/cascade-close")
async def cascade_close_incident(incident_id: str):
    """Close a master ticket and all its children. Each child is closed on ITSM + locally.
    Full audit trail for every step."""
    from agents.monitor.incident_creator import get_incident_row, set_incident_status
    from agents.monitor.correlator import get_children
    from agents.triage.closer import close_incident_and_ticket
    from shared.trace import log_step, get_run_id_for_incident, get_max_step
    from shared import audit
    from orchestrator.chronicler_pipeline import run_chronicler

    row = get_incident_row(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    is_master = (row.get("parent_incident_id") or "").strip() == "SELF"
    if not is_master:
        raise HTTPException(status_code=400, detail="Incident is not a master ticket")

    if (row.get("status") or "open").lower() == "closed":
        return {"status": "already_closed", "incident_id": incident_id, "children_closed": 0}

    ticket_id = (row.get("ticket_id") or "").strip()
    ticket_system = (row.get("ticket_system") or "").strip().lower()
    ticket_number = (row.get("ticket_number") or "").strip()

    run_id = get_run_id_for_incident(incident_id) or f"cascade_{incident_id}"
    step = get_max_step(run_id) + 1 if get_run_id_for_incident(incident_id) else 1

    audit.log_comprehensive(
        "cascade_closer", "cascade_close_start", ticket_number or incident_id,
        "started", payload_summary=f"Cascade close initiated for master {ticket_number or incident_id}")

    log_step(run_id, incident_id, step, "CascadeCloser", "cascade_close",
             "invoke",
             f"Cascade close started for master ticket {ticket_number or incident_id}. "
             "Will close all children first, then the master.",
             "started", ticket_number=ticket_number)
    step += 1

    children = get_children(incident_id)
    children_closed = 0
    children_failed = 0

    for child in children:
        c_id = child.get("incident_id", "")
        c_status = (child.get("status") or "open").lower()
        c_ticket_id = (child.get("ticket_id") or "").strip()
        c_ticket_sys = (child.get("ticket_system") or "").strip().lower()
        c_ticket_num = (child.get("ticket_number") or "").strip()

        if c_status == "closed":
            audit.log_simple("cascade_closer", "child_already_closed",
                             c_ticket_num or c_id, "skipped")
            continue

        log_step(run_id, incident_id, step, "CascadeCloser", "close_child",
                 "invoke",
                 f"Closing child ticket {c_ticket_num or c_id} (under master {ticket_number or incident_id}).",
                 "started", ticket_number=ticket_number)
        step += 1

        ok = await close_incident_and_ticket(c_id, c_ticket_id, c_ticket_sys, c_ticket_num)
        set_incident_status(c_id, "closed")

        if ok:
            children_closed += 1
            audit.log_comprehensive(
                "cascade_closer", "child_closed", c_ticket_num or c_id, "success",
                payload_summary=f"Child {c_ticket_num or c_id} closed via cascade from {ticket_number or incident_id}")
            log_step(run_id, incident_id, step, "CascadeCloser", "close_child",
                     "closed",
                     f"Child {c_ticket_num or c_id} closed successfully on {c_ticket_sys}.",
                     "success", c_ticket_num or c_id, ticket_number=ticket_number)
        else:
            children_failed += 1
            audit.log_comprehensive(
                "cascade_closer", "child_close_failed", c_ticket_num or c_id, "failed",
                error_message=f"Failed to close child on {c_ticket_sys}",
                payload_summary=f"Cascade child close failed for {c_ticket_num or c_id}")
            log_step(run_id, incident_id, step, "CascadeCloser", "close_child",
                     "failed",
                     f"Failed to close child {c_ticket_num or c_id} on {c_ticket_sys}. See audit logs.",
                     "failed", c_ticket_num or c_id, ticket_number=ticket_number)
        step += 1

    # Close the master itself
    log_step(run_id, incident_id, step, "CascadeCloser", "close_master",
             "invoke",
             f"Closing master ticket {ticket_number or incident_id} after {children_closed} children closed.",
             "started", ticket_number=ticket_number)
    step += 1

    master_ok = await close_incident_and_ticket(incident_id, ticket_id, ticket_system, ticket_number)
    set_incident_status(incident_id, "closed")

    if master_ok:
        audit.log_comprehensive(
            "cascade_closer", "master_closed", ticket_number or incident_id, "success",
            payload_summary=f"Master {ticket_number or incident_id} closed. "
                           f"Children closed: {children_closed}, failed: {children_failed}")
    else:
        audit.log_comprehensive(
            "cascade_closer", "master_close_failed", ticket_number or incident_id, "failed",
            error_message="Master ticket ITSM close failed",
            payload_summary=f"Master ITSM close failed. Children closed: {children_closed}")

    log_step(run_id, incident_id, step, "CascadeCloser", "cascade_complete",
             "completed",
             f"Cascade close finished for {ticket_number or incident_id}. "
             f"Children OK: {children_closed}, failed: {children_failed}. "
             f"Master ITSM: {'success' if master_ok else 'failed'}.",
             "completed", ticket_number=ticket_number)

    try:
        await run_chronicler(incident_id=incident_id, ticket_number=ticket_number)
    except Exception:
        pass

    return {
        "status": "closed",
        "incident_id": incident_id,
        "ticket_updated": master_ok,
        "children_closed": children_closed,
        "children_failed": children_failed,
    }


@app.post("/generate-docs")
async def generate_docs_endpoint():
    """Manual trigger: run the Chronicler pipeline across all closed incidents."""
    from orchestrator.chronicler_pipeline import run_chronicler
    result = await run_chronicler()
    return result


@app.post("/check")
async def check_state_changes():
    """Polling endpoint: scan incidents for state changes, trigger actions accordingly.
    Called by UI periodically when orchestrator_polling_enabled is true."""
    import csv
    from shared.config_loader import DATA_DIR
    from shared import audit
    from orchestrator.chronicler_pipeline import run_chronicler

    incidents_csv = DATA_DIR / "incidents" / "incidents.csv"
    if not incidents_csv.exists():
        return {"checked": 0, "actions": []}

    actions = []

    with open(incidents_csv, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        status = (row.get("status") or "open").lower()
        inc_id = row.get("incident_id", "")
        ticket_number = row.get("ticket_number", "")

        if status == "closed" and not row.get("docs_generated"):
            try:
                await run_chronicler(incident_id=inc_id, ticket_number=ticket_number)
                actions.append({"action": "chronicler", "incident_id": inc_id})
            except Exception:
                pass

    return {"checked": len(rows), "actions": actions}


@app.get("/health")
async def health():
    return {"status": "ok"}
