"""
Aggregator (4.1): on incident close, batch closed incidents; simple clustering (service + error type).
"""
from pathlib import Path
from shared.config_loader import DATA_DIR

INCIDENTS_CSV = DATA_DIR / "incidents" / "incidents.csv"


def get_closed_incidents(limit: int = 100) -> list[dict]:
    """Return recent incidents (could filter by status when we have it)."""
    import csv
    if not INCIDENTS_CSV.exists():
        return []
    with open(INCIDENTS_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]
