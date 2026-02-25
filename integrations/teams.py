"""
MS Teams: webhook + Adaptive Cards (T.2). Config-driven; stub if no credentials.
"""
import os
from typing import Any

from shared.config_loader import get_services_config, get_env


def is_configured() -> bool:
    cfg = get_services_config().get("teams", {})
    if not cfg.get("enabled"):
        return False
    url = get_env(cfg.get("webhook_url_env", "TEAMS_WEBHOOK_URL"))
    return bool(url)


async def send_message(text: str, card: dict | None = None) -> bool:
    """Send text or Adaptive Card to Teams. Returns True if sent."""
    if not is_configured():
        return False
    # TODO: httpx.AsyncClient post to webhook; card as attachment if provided
    return False
