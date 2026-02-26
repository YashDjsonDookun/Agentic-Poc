"""
Orchestrator policy (5.1): routing, solicitation, Chronicler trigger, re-open rules.
"""
from typing import Literal

from shared.config_loader import get_services_config


def route_phase(event_type: str, payload: dict) -> Literal["monitor", "triage", "chronicler"]:
    """Decide which phase to invoke. For MVP: ingest events go to monitor."""
    if event_type in ("alert", "metric", "health", "simulated"):
        return "monitor"
    if event_type == "incident_created":
        return "triage"
    if event_type == "incident_closed":
        return "chronicler"
    return "monitor"


def should_solicit(severity: str, runbooks: list) -> bool:
    """Solicit approval when there is a suggested action (runbook) and severity is below P1/critical."""
    if not runbooks:
        return False
    sev = (severity or "").strip().lower()
    if sev in ("critical", "p1", "1"):
        return False
    return True


def should_trigger_chronicler() -> bool:
    """Always trigger Chronicler after a close (for MVP). Config toggle for future control."""
    return True


def is_polling_enabled() -> bool:
    cfg = get_services_config().get("orchestrator", {})
    return bool(cfg.get("polling_enabled", False))


def get_poll_interval() -> int:
    cfg = get_services_config().get("orchestrator", {})
    return int(cfg.get("poll_interval_seconds", 60))
