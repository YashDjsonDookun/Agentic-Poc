"""
Collector (Phase 1.1): ingest from simulator (or normalized source); pass through to Evaluator.
"""
from shared.schema import MonitoringEvent


def collect(event: dict) -> MonitoringEvent:
    """Normalize raw event dict to MonitoringEvent."""
    return MonitoringEvent(
        event_id=event.get("event_id", ""),
        source=event.get("source", "unknown"),
        metric=event.get("metric", ""),
        value=float(event.get("value", 0)),
        unit=event.get("unit", ""),
        service=event.get("service", ""),
        timestamp=event.get("timestamp", ""),
        extra=event.get("extra", {}),
    )
