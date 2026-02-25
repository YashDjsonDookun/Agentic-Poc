"""
Executor (3.2): one safe action type; simulated execution only. Log outcome.
"""
from shared import audit


async def execute_approved_action(incident_id: str, action_type: str, params: dict) -> dict:
    """Simulated execution. Returns {success, message}."""
    audit.log_simple("triage", "executor_run", incident_id, "simulated")
    return {"success": True, "message": "Simulated execution (no real server)."}
