"""
MS Teams: webhook + Adaptive Cards (T.2). Config from UI (local.integrations) or env.
"""
import os
from typing import Any

import httpx
from shared.config_loader import get_services_config, get_env, get_integration_credentials


def is_configured() -> bool:
    """True if webhook URL is set (UI config or env)."""
    creds = get_integration_credentials("teams") or {}
    url = (creds.get("webhook_url") or "").strip()
    if url:
        return True
    cfg = get_services_config().get("teams", {})
    if not cfg.get("enabled"):
        return False
    url = get_env(cfg.get("webhook_url_env", "TEAMS_WEBHOOK_URL")) or ""
    return bool(url.strip())


def _get_webhook_url() -> str:
    """Webhook URL from UI config first, then env."""
    creds = get_integration_credentials("teams") or {}
    url = (creds.get("webhook_url") or "").strip()
    if url:
        return url
    cfg = get_services_config().get("teams", {})
    return (get_env(cfg.get("webhook_url_env", "TEAMS_WEBHOOK_URL")) or "").strip()


async def send_message(text: str, card: dict | None = None) -> bool:
    """Send text or Adaptive Card to Teams. Returns True if sent (2xx)."""
    if not is_configured():
        return False
    url = _get_webhook_url()
    if not url:
        return False
    try:
        payload = {"text": text}
        if card:
            payload["@type"] = "MessageCard"
            payload["@context"] = "https://schema.org/extensions"
            payload["summary"] = (text or "")[:100]
            payload["sections"] = [{"activityTitle": "Approval", "text": text}]
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
        return 200 <= r.status_code < 300
    except Exception:
        return False
