"""
Simulator scenarios (1.6): issue types that emit normalized events for Collector.
Same schema as real monitoring would produce (Phase 0.3).
"""
from datetime import datetime, timezone
import uuid
from typing import Iterator

# Event schema: event_id, source, metric, value, unit, service, timestamp, extra
SCENARIOS = {
    "high_cpu": {
        "metric": "cpu_percent",
        "value": 95.0,
        "unit": "percent",
        "service": "app-svc",
        "summary": "High CPU on app-svc",
    },
    "service_down": {
        "metric": "up",
        "value": 0.0,
        "unit": "bool",
        "service": "api-gw",
        "summary": "Service api-gw down",
    },
    "error_spike": {
        "metric": "error_rate",
        "value": 0.15,
        "unit": "ratio",
        "service": "app-svc",
        "summary": "Error rate spike on app-svc",
    },
    "high_memory": {
        "metric": "memory_percent",
        "value": 92.0,
        "unit": "percent",
        "service": "app-svc",
        "summary": "High memory on app-svc",
    },
    "latency_spike": {
        "metric": "latency_p99_ms",
        "value": 2000.0,
        "unit": "ms",
        "service": "api-gw",
        "summary": "P99 latency spike on api-gw",
    },
}


def emit_event(scenario_key: str) -> dict:
    """Emit one event for the given scenario. Returns normalized event dict."""
    if scenario_key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_key}. Choose from {list(SCENARIOS)}")
    s = SCENARIOS[scenario_key]
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "event_id": event_id,
        "source": "simulator",
        "metric": s["metric"],
        "value": s["value"],
        "unit": s["unit"],
        "service": s["service"],
        "timestamp": ts,
        "extra": {"summary": s["summary"]},
    }


def list_scenarios() -> list[str]:
    return list(SCENARIOS.keys())
