"""
ServiceNow integration (INT.1): create incident, update work notes, close. Dev instance.
"""
import httpx
from typing import Optional

from shared.config_loader import get_integrations_config, get_integration_credentials


def is_configured() -> bool:
    cfg = get_integrations_config().get("servicenow", {})
    if not cfg.get("enabled"):
        return False
    creds = get_integration_credentials("servicenow")
    url = creds.get("instance_url") or ""
    user = creds.get("username") or ""
    return bool(url and user)


async def test_connection() -> tuple[bool, str]:
    """Attempt a GET to the instance; success if status is 2xx. Returns (success, message)."""
    cfg = get_integrations_config().get("servicenow", {})
    if not cfg.get("enabled"):
        return False, "Integration is disabled. Enable it in Configuration (edit mode) and save, then test again."
    creds = get_integration_credentials("servicenow")
    base = (creds.get("instance_url") or "").strip()
    user = (creds.get("username") or "").strip()
    password = creds.get("password") or ""
    if not base or not user or not password:
        missing = [x for x, v in [("instance URL", base), ("username", user), ("password", password)] if not v]
        return False, f"Missing in Configuration: {', '.join(missing)}. Enter values in Integrations tab and save."
    url = base.rstrip("/") + "/api/now/table/sys_user?sysparm_limit=1"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                url,
                auth=(user, password),
                headers={"Accept": "application/json"},
            )
            ok = 200 <= r.status_code < 300
            msg = f"HTTP {r.status_code}" + (f": {r.text[:200]}" if not ok and r.text else "")
            return ok, msg
    except Exception as e:
        return False, str(e)


async def create_incident(
    short_description: str,
    description: str = "",
    priority: str = "3",
    category: str = "",
) -> Optional[dict]:
    """Create ServiceNow incident. Returns sys_id if created."""
    if not is_configured():
        return None
    # TODO: httpx.AsyncClient POST /api/now/table/incident
    return {"sys_id": "placeholder_sys_id"}


async def update_work_notes(sys_id: str, notes: str) -> bool:
    if not is_configured():
        return False
    # TODO: PATCH /api/now/table/incident/{sys_id}
    return False


async def close_incident(sys_id: str) -> bool:
    if not is_configured():
        return False
    # TODO: PATCH state to closed
    return False
