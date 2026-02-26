"""
Alert Router (1.2): maintenance window, dedupe by service+metric, re-open detection.
Decision: create incident, re-open alert, or ignore.
"""
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

from shared.config_loader import CONFIG_TABLES_DIR, DATA_DIR

MAINTENANCE_WINDOWS_PATH = CONFIG_TABLES_DIR / "maintenance_windows.csv"
INCIDENTS_CSV = DATA_DIR / "incidents" / "incidents.csv"

REOPEN_WINDOW_HOURS = 24


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


def _find_recently_closed(service: str, metric: str) -> dict | None:
    """Find a recently closed incident matching service + metric keyword (within REOPEN_WINDOW_HOURS)."""
    if not INCIDENTS_CSV.exists():
        return None
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=REOPEN_WINDOW_HOURS)
    metric_kw = metric.lower()

    candidates = []
    with open(INCIDENTS_CSV, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").lower() not in ("closed", "resolved"):
                continue
            if (row.get("service") or "").lower() != service.lower():
                continue
            summary_lower = (row.get("summary") or "").lower()
            if metric_kw not in summary_lower and not any(kw in summary_lower for kw in metric_kw.split("_")):
                continue
            try:
                ts = datetime.fromisoformat(row.get("timestamp", "").replace("Z", "+00:00"))
                if ts >= cutoff:
                    candidates.append(row)
            except (ValueError, TypeError):
                continue
    return candidates[-1] if candidates else None


def check_reopen(service: str, metric: str) -> dict | None:
    """If a recently closed incident matches, return it (for re-open alert). None otherwise."""
    return _find_recently_closed(service, metric)


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
