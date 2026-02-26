"""
ServiceNow integration (INT.1): create incident, update work notes, close. Dev instance.
States: New=1, In Progress=2, On Hold=3, Resolved=6, Closed=7, Canceled=8.
Priority is derived from urgency + impact (1=High..3=Low for both).
Closing requires: close_code, close_notes, caller_id.
"""
import httpx
from typing import Optional

from shared.config_loader import get_integrations_config, get_integration_credentials

_caller_id_cache: dict[str, str] = {}


def _get_creds() -> tuple[str, str, str]:
    creds = get_integration_credentials("servicenow")
    return (
        (creds.get("instance_url") or "").strip(),
        (creds.get("username") or "").strip(),
        creds.get("password") or "",
    )


def is_configured() -> bool:
    cfg = get_integrations_config().get("servicenow", {})
    if not cfg.get("enabled"):
        return False
    base, user, _ = _get_creds()
    return bool(base and user)


async def _resolve_caller_id(base: str, user: str, password: str) -> str:
    """Lookup sys_id for the configured username from sys_user. Cached per session."""
    if user in _caller_id_cache:
        return _caller_id_cache[user]
    url = base.rstrip("/") + f"/api/now/table/sys_user?sysparm_query=user_name={user}&sysparm_fields=sys_id&sysparm_limit=1"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, auth=(user, password), headers={"Accept": "application/json"})
        if 200 <= r.status_code < 300:
            results = r.json().get("result", [])
            if results:
                sid = results[0].get("sys_id", "")
                _caller_id_cache[user] = sid
                return sid
    except Exception:
        pass
    return ""


async def test_connection() -> tuple[bool, str]:
    """Attempt a GET to the instance; success if status is 2xx. Returns (success, message)."""
    cfg = get_integrations_config().get("servicenow", {})
    if not cfg.get("enabled"):
        return False, "Integration is disabled. Enable it in Configuration (edit mode) and save, then test again."
    base, user, password = _get_creds()
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


_group_cache: dict[str, str] = {}


async def resolve_assignment_group(
    group_name: str,
) -> str:
    """Resolve a group name to its sys_id via sys_user_group. Cached."""
    if not group_name:
        return ""
    if group_name in _group_cache:
        return _group_cache[group_name]
    if not is_configured():
        return ""
    base, user, password = _get_creds()
    url = (
        base.rstrip("/")
        + f"/api/now/table/sys_user_group?sysparm_query=name={group_name}"
        + "&sysparm_fields=sys_id,name&sysparm_limit=1"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, auth=(user, password), headers={"Accept": "application/json"})
        if 200 <= r.status_code < 300:
            results = r.json().get("result", [])
            if results:
                sid = results[0].get("sys_id", "")
                _group_cache[group_name] = sid
                return sid
    except Exception:
        pass
    return ""


async def fetch_assignment_groups() -> list[dict]:
    """Fetch all user groups from SNOW sys_user_group. Returns [{sys_id, name}]."""
    if not is_configured():
        return []
    base, user, password = _get_creds()
    url = (
        base.rstrip("/")
        + "/api/now/table/sys_user_group?sysparm_fields=sys_id,name&sysparm_limit=200"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, auth=(user, password), headers={"Accept": "application/json"})
        if 200 <= r.status_code < 300:
            return r.json().get("result", [])
    except Exception:
        pass
    return []


async def create_incident(
    short_description: str,
    description: str = "",
    urgency: str = "2",
    impact: str = "2",
    severity: str = "2",
    category: str = "",
    subcategory: str = "",
    assignment_group: str = "",
) -> Optional[dict]:
    """Create ServiceNow incident with category, subcategory, and assignment group.
    Returns {"sys_id": "...", "number": "INC..."} on success."""
    if not is_configured():
        return None
    base, user, password = _get_creds()
    if not base or not user or not password:
        return None
    caller_id = await _resolve_caller_id(base, user, password)
    url = base.rstrip("/") + "/api/now/table/incident"
    body: dict = {
        "short_description": short_description[:160] if short_description else "Incident",
        "description": description or "",
        "urgency": str(urgency),
        "impact": str(impact),
        "severity": str(severity),
    }
    if caller_id:
        body["caller_id"] = caller_id
    if category:
        body["category"] = category
    if subcategory:
        body["subcategory"] = subcategory
    if assignment_group:
        group_sid = await resolve_assignment_group(assignment_group)
        if group_sid:
            body["assignment_group"] = group_sid
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                url,
                auth=(user, password),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code != 201:
                return None
            data = r.json()
            result = data.get("result") or data
            sys_id = result.get("sys_id")
            number = result.get("number") or ""
            out = {"sys_id": sys_id}
            if sys_id:
                out["number"] = number
            return out if sys_id else None
    except Exception:
        return None


async def update_work_notes(sys_id: str, notes: str) -> bool:
    """Append work notes to an incident. PATCH /api/now/table/incident/{sys_id}."""
    if not is_configured() or not sys_id or not notes:
        return False
    base, user, password = _get_creds()
    if not base or not user or not password:
        return False
    url = base.rstrip("/") + f"/api/now/table/incident/{sys_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(
                url,
                auth=(user, password),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json={"work_notes": notes},
            )
            return 200 <= r.status_code < 300
    except Exception:
        return False


VALID_CLOSE_CODES = [
    "Solved (Permanently)",
    "Solved (Work Around)",
    "Solved Remotely (Permanently)",
    "Solved Remotely (Work Around)",
    "Not Solved (Not Reproducible)",
    "Not Solved (Too Costly)",
    "Closed/Resolved by Caller",
    "Solution provided",
]


async def _stop_sla(base: str, user: str, password: str, task_sys_id: str) -> None:
    """Best-effort: mark active SLA records for this task as completed/breached."""
    url = (
        base.rstrip("/")
        + f"/api/now/table/task_sla?sysparm_query=task={task_sys_id}^active=true"
        + "&sysparm_fields=sys_id"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, auth=(user, password), headers={"Accept": "application/json"})
        if not (200 <= r.status_code < 300):
            return
        sla_records = r.json().get("result", [])
        for rec in sla_records:
            sla_id = rec.get("sys_id")
            if not sla_id:
                continue
            sla_url = base.rstrip("/") + f"/api/now/table/task_sla/{sla_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.patch(
                    sla_url,
                    auth=(user, password),
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                    json={"active": "false"},
                )
    except Exception:
        pass


async def close_incident(
    sys_id: str,
    close_notes: str = "Closed via SENTRY/ARGUS.",
    close_code: str = "Solution provided",
) -> tuple[bool, str]:
    """Resolve (state=6), stop SLA, then close (state=7).
    Mandatory SNOW fields: close_code, close_notes, caller_id."""
    if not is_configured():
        return False, "servicenow not configured"
    if not (sys_id and sys_id.strip()):
        return False, "missing sys_id (ticket_id)"
    base, user, password = _get_creds()
    if not base or not user or not password:
        return False, "missing credentials"
    caller_id = await _resolve_caller_id(base, user, password)
    if not caller_id:
        return False, "could not resolve caller_id for user"
    url = base.rstrip("/") + f"/api/now/table/incident/{sys_id.strip()}"
    close_notes = close_notes or "Closed via SENTRY/ARGUS."
    close_code = close_code if close_code in VALID_CLOSE_CODES else "Solution provided"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Step 1 — Resolve (state=6) with mandatory fields
    resolve_body: dict = {
        "state": "6",
        "close_code": close_code,
        "close_notes": close_notes,
        "caller_id": caller_id,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(url, auth=(user, password), headers=headers, json=resolve_body)
        if not (200 <= r.status_code < 300):
            return False, f"resolve HTTP {r.status_code}: {(r.text or '')[:300]}"
    except Exception as e:
        return False, f"resolve error: {e}"

    # Step 2 — Stop any active SLAs tied to this incident
    await _stop_sla(base, user, password, sys_id.strip())

    # Step 3 — Close (state=7)
    close_body: dict = {
        "state": "7",
        "close_code": close_code,
        "close_notes": close_notes,
        "caller_id": caller_id,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(url, auth=(user, password), headers=headers, json=close_body)
        if 200 <= r.status_code < 300:
            return True, "closed"
        return False, f"resolved but close failed HTTP {r.status_code}: {(r.text or '')[:300]}"
    except Exception as e:
        return False, f"resolved but close error: {e}"
