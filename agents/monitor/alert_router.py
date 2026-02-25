"""
Alert Router (1.2): maintenance window, dedupe by service+metric. Decision: create incident or ignore.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

from shared.config_loader import CONFIG_TABLES_DIR

MAINTENANCE_WINDOWS_PATH = CONFIG_TABLES_DIR / "maintenance_windows.csv"


def _in_maintenance_window(service: str) -> bool:
    if not MAINTENANCE_WINDOWS_PATH.exists():
        return False
    now = datetime.now(timezone.utc)
    with open(MAINTENANCE_WINDOWS_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("service") != service:
                continue
            try:
                start = datetime.fromisoformat(row["start_utc"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(row["end_utc"].replace("Z", "+00:00"))
                if start <= now <= end:
                    return True
            except (KeyError, ValueError):
                continue
    return False


def should_create_incident(service: str, metric: str, dedupe_cache: set | None = None) -> tuple[bool, str]:
    """
    Returns (create_incident: bool, reason: str).
    Dedupe: pass a set of (service, metric) to avoid creating duplicate incidents in same run.
    """
    if _in_maintenance_window(service):
        return False, "maintenance_window"
    if dedupe_cache is not None and (service, metric) in dedupe_cache:
        return False, "dedupe"
    return True, "create"
