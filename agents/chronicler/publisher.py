"""
Publisher (4.3): writes generated docs to knowledge/generated/ and optionally notifies via Teams.
Provision for Confluence/ServiceNow KB publishing in future.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.config_loader import get_integrations_config


async def publish(
    generated_paths: dict[str, Path],
    cluster_key: str = "",
    notify: bool = True,
) -> dict[str, Any]:
    """Publish generated files and optionally send a Teams notification.
    Returns {"published": [...], "notified": bool}."""
    published: list[str] = []
    for fmt, path in generated_paths.items():
        if path.exists():
            published.append(str(path))

    notified = False
    if notify and published:
        try:
            from integrations.teams import is_configured, send_message
            if is_configured():
                file_list = ", ".join(p.suffix for p in generated_paths.values() if p.exists())
                msg = (
                    f"📄 New runbook generated for **{cluster_key}**\n"
                    f"Formats: {file_list}\n"
                    f"Location: knowledge/generated/"
                )
                notified = await send_message(msg)
        except Exception:
            pass

    return {"published": published, "notified": notified}
