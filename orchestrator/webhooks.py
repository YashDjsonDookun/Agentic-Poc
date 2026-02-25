"""
Webhook endpoints (A.2, A.3): optional ingest + Teams callback.
"""
from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/ingest")
async def ingest_webhook(request: Request, x_idempotency_key: Optional[str] = Header(None)):
    """Optional: real-time ingestion. Validate payload; optional idempotency key."""
    body = await request.json()
    # TODO: validate payload size (S.4), verify auth (S.5)
    return {"status": "received", "idempotency_key": x_idempotency_key}


@router.post("/teams/callback")
async def teams_callback(request: Request):
    """Receive Adaptive Card submit actions from MS Teams (T.3)."""
    body = await request.json()
    # TODO: validate Teams payload, update state, continue flow
    return {"status": "ok"}
