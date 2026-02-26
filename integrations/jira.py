"""
Jira integration (INT.2): create issue, add comment, transition. Dev instance; auth via env.
"""
from typing import Optional

import httpx
from shared.config_loader import get_integrations_config, get_integration_credentials


def is_configured() -> bool:
    cfg = get_integrations_config().get("jira", {})
    if not cfg.get("enabled"):
        return False
    creds = get_integration_credentials("jira")
    base = creds.get("base_url") or ""
    token = creds.get("api_token") or ""
    return bool(base and token)


async def test_connection() -> tuple[bool, str]:
    """GET /rest/api/3/myself with basic auth; success if status is 2xx. Returns (success, message)."""
    cfg = get_integrations_config().get("jira", {})
    if not cfg.get("enabled"):
        return False, "Integration is disabled. Enable it in Configuration (edit mode) and save, then test again."
    creds = get_integration_credentials("jira")
    base = (creds.get("base_url") or "").strip()
    username = (creds.get("username") or "").strip()
    token = creds.get("api_token") or ""
    if not base or not username or not token:
        return False, "Missing in Configuration: base URL, username (email), or API token. Enter in Integrations tab and save."
    url = base.rstrip("/") + "/rest/api/3/myself"
    auth = (username, token)  # Jira Cloud: email + API token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                url,
                auth=auth,
                headers={"Accept": "application/json"},
            )
            ok = 200 <= r.status_code < 300
            msg = f"HTTP {r.status_code}" + (f": {r.text[:200]}" if not ok and r.text else "")
            return ok, msg
    except Exception as e:
        return False, str(e)


async def create_issue(
    project_key: str,
    summary: str,
    description: str = "",
    priority: str = "Medium",
    issue_type: str = "Incident",
) -> tuple[Optional[dict], str]:
    """Create Jira issue. Returns ({"key": "PROJ-123", "id": "..."}, "") on success, (None, error_msg) on failure."""
    if not is_configured():
        return None, "Jira not configured."
    creds = get_integration_credentials("jira")
    base = (creds.get("base_url") or "").strip()
    username = (creds.get("username") or "").strip()
    token = creds.get("api_token") or ""
    proj = (project_key or creds.get("project_key") or "").strip()
    if not base or not username or not token:
        return None, "Missing Jira base URL, username, or API token in Configuration."
    if not proj:
        return None, "Missing Jira project key. Set it in Configuration (Integrations → Jira → Project key)."
    url = base.rstrip("/") + "/rest/api/3/issue"
    desc_content = description or ""
    body = {
        "fields": {
            "project": {"key": proj},
            "summary": summary[:255] if summary else "Incident",
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc_content}]}]},
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                url,
                auth=(username, token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=body,
            )
            if r.status_code == 201:
                data = r.json()
                return {"key": data.get("key"), "id": data.get("id")}, ""
            err = r.text
            try:
                j = r.json()
                err = j.get("errorMessages", [])
                if isinstance(err, list) and err:
                    err = "; ".join(str(m) for m in err)
                elif isinstance(j.get("errors"), dict):
                    err = "; ".join(f"{k}: {v}" for k, v in j["errors"].items())
                else:
                    err = r.text
            except Exception:
                pass
            return None, f"HTTP {r.status_code}: {err or r.reason_phrase}"
    except Exception as e:
        return None, str(e)


async def add_comment(issue_key: str, body: str) -> bool:
    if not is_configured():
        return False
    # TODO: POST /rest/api/3/issue/{key}/comment
    return False


async def transition(issue_key: str, transition_id: str) -> bool:
    if not is_configured():
        return False
    # TODO: POST /rest/api/3/issue/{key}/transitions
    return False
