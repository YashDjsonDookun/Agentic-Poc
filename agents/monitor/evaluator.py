"""
Evaluator (Phase 1.1): apply threshold rules from config/tables/alert_rules.csv.
Output: "alert" or "no alert".
"""
import csv
from pathlib import Path

from shared.schema import MonitoringEvent
from shared.config_loader import CONFIG_TABLES_DIR

ALERT_RULES_PATH = CONFIG_TABLES_DIR / "alert_rules.csv"


def _load_rules() -> list[dict]:
    if not ALERT_RULES_PATH.exists():
        return []
    with open(ALERT_RULES_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def evaluate(event: MonitoringEvent) -> tuple[str, str | None]:
    """
    Apply rules. Return ("alert", reason) or ("no_alert", None).
    """
    rules = _load_rules()
    for row in rules:
        if row.get("enabled", "true").lower() != "true":
            continue
        if row.get("service") != event.service or row.get("metric") != event.metric:
            continue
        try:
            threshold = float(row["threshold"])
        except (KeyError, ValueError):
            continue
        op = row.get("operator", "gt").strip().lower()
        if op == "gt" and event.value > threshold:
            return "alert", f"{event.metric} {event.value} > {threshold}"
        if op == "gte" and event.value >= threshold:
            return "alert", f"{event.metric} {event.value} >= {threshold}"
        if op == "lt" and event.value < threshold:
            return "alert", f"{event.metric} {event.value} < {threshold}"
    return "no_alert", None
