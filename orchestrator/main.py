"""
Orchestrator entry point (0.2): FastAPI app, async, single entry for events.
"""
from fastapi import FastAPI
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


@app.get("/health")
async def health():
    return {"status": "ok"}
