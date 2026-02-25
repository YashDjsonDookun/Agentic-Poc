"""
Shared event and incident schemas — single internal format for simulator and agents.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class MonitoringEvent:
    """Normalized event from Collector/simulator (Phase 0.3, 1.1)."""
    event_id: str
    source: str  # e.g. "simulator"
    metric: str
    value: float
    unit: str
    service: str
    timestamp: str  # ISO 8601
    extra: dict = field(default_factory=dict)


@dataclass
class Incident:
    """Incident record created by Incident Creator (1.3)."""
    incident_id: str
    severity: str  # critical, high, medium, low
    service: str
    summary: str
    timestamp: str
    context: dict = field(default_factory=dict)  # metrics, logs snippet
    ticket_id: Optional[str] = None
    ticket_system: Optional[str] = None  # "jira" | "servicenow"


@dataclass
class AuditEntry:
    """One audit log row (AL.1, AL.2)."""
    timestamp: str
    agent_id: str
    action_type: str
    entity_id: str
    outcome: str
    detail_level: str = "simple"  # "simple" | "comprehensive"
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    payload_summary: Optional[str] = None
