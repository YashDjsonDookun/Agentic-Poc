"""
Aggregator (4.1): on incident close, batch closed incidents; cluster by service + theme.
Feeds into Doc Writer for runbook/SOP generation.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

from shared.config_loader import DATA_DIR
from shared.trace import TRACE_PATH

INCIDENTS_CSV = DATA_DIR / "incidents" / "incidents.csv"

_THEME_KEYWORDS = {
    "high_cpu": ["cpu", "high cpu"],
    "high_memory": ["memory", "high memory"],
    "service_down": ["down", "service down", "unavailable"],
    "error_spike": ["error", "error rate", "error spike"],
    "latency_spike": ["latency", "p99", "latency spike", "slow"],
}


def _extract_theme(summary: str) -> str:
    s = summary.lower()
    for theme, keywords in _THEME_KEYWORDS.items():
        if any(kw in s for kw in keywords):
            return theme
    return "general"


def get_closed_incidents(limit: int = 200) -> list[dict]:
    """Return incidents with status=closed."""
    if not INCIDENTS_CSV.exists():
        return []
    with open(INCIDENTS_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if (r.get("status") or "").lower() == "closed"][-limit:]


def cluster_incidents(incidents: list[dict] | None = None) -> list[dict]:
    """Group closed incidents by (service, theme). Returns list of cluster dicts."""
    if incidents is None:
        incidents = get_closed_incidents()
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for inc in incidents:
        service = inc.get("service", "unknown")
        theme = _extract_theme(inc.get("summary", ""))
        buckets[(service, theme)].append(inc)
    clusters = []
    for (service, theme), incs in buckets.items():
        clusters.append({
            "cluster_key": f"{service}_{theme}",
            "service": service,
            "theme": theme,
            "incidents": incs,
            "count": len(incs),
            "severities": list({i.get("severity", "") for i in incs}),
            "summaries": list({i.get("summary", "") for i in incs}),
        })
    return sorted(clusters, key=lambda c: c["count"], reverse=True)


def get_trace_data_for_incidents(incident_ids: list[str]) -> list[dict]:
    """Pull trace rows for given incident_ids — used by Doc Writer for RCA and recommendations."""
    if not TRACE_PATH.exists() or not incident_ids:
        return []
    id_set = set(incident_ids)
    rows = []
    with open(TRACE_PATH, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("incident_id") in id_set and row.get("outcome") != "started":
                rows.append(row)
    return rows
