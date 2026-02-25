"""
Orchestrator policy (5.1): when to create incident, when to call Triage, when to call Chronicler.
"""
from typing import Literal

# Phase routing: event -> "monitor" | "triage" | "chronicler"
def route_phase(event_type: str, payload: dict) -> Literal["monitor", "triage", "chronicler"]:
    """Decide which phase to invoke. For MVP: ingest events go to monitor."""
    if event_type in ("alert", "metric", "health", "simulated"):
        return "monitor"
    if event_type == "incident_created":
        return "triage"
    if event_type == "incident_closed":
        return "chronicler"
    return "monitor"
