"""
Webhook endpoints (A.2, A.3): optional ingest + Teams callback + Phase 3 approval.
"""
from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from orchestrator.approvals_store import get_pending_by_request, get_pending_by_incident, record_decision
from shared import audit

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class ApprovalBody(BaseModel):
    request_id: Optional[str] = None
    incident_id: Optional[str] = None
    decision: Literal["approve", "reject"]


@router.post("/approval")
async def approval_webhook(body: ApprovalBody):
    """Phase 3: receive Approve/Reject; on approve run Executor then Ticket Updater and record decision."""
    if not body.request_id and not body.incident_id:
        raise HTTPException(status_code=400, detail="Provide request_id or incident_id")
    pending = None
    if body.request_id:
        pending = get_pending_by_request(body.request_id)
    if not pending and body.incident_id:
        pending = get_pending_by_incident(body.incident_id)
    if not pending:
        raise HTTPException(status_code=404, detail="No pending approval found")
    request_id = pending["request_id"]
    if body.decision == "reject":
        record_decision(request_id, "reject")
        audit.log_simple("triage", "approval_rejected", pending["incident_id"], "success")
        return {"status": "rejected", "request_id": request_id}
    # approve: record, then Executor -> Ticket Updater
    record_decision(request_id, "approve")
    incident_id = pending["incident_id"]
    action_type = pending.get("action_type") or "run_runbook"
    ticket_id = pending.get("ticket_id") or ""
    ticket_system = (pending.get("ticket_system") or "").strip().lower()
    from agents.triage.executor import execute_approved_action
    from agents.tickets.ticket_updater import update_ticket
    result = await execute_approved_action(incident_id, action_type, {"suggestion": pending.get("action_suggestion", "")})
    comment = f"Approved action executed: {result.get('message', 'ok')}"
    if ticket_id and ticket_system:
        await update_ticket(ticket_id, ticket_system, comment, transition=None)
    audit.log_simple("triage", "approval_executed", incident_id, "success")
    return {"status": "approved", "request_id": request_id, "executor": result}


@router.post("/ingest")
async def ingest_webhook(request: Request, x_idempotency_key: Optional[str] = Header(None)):
    """Optional: real-time ingestion. Validate payload; optional idempotency key."""
    body = await request.json()
    return {"status": "received", "idempotency_key": x_idempotency_key}


@router.post("/teams/callback")
async def teams_callback(request: Request):
    """Receive Adaptive Card submit actions from MS Teams (T.3)."""
    body = await request.json()
    return {"status": "ok"}
