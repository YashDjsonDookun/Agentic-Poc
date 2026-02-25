"""
Audit logging — simple and comprehensive, file-based CSV (AL.1, AL.2, 5.4).
No PII in payload_summary by default (S.2).
"""
import csv
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Default paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SIMPLE_PATH = _PROJECT_ROOT / "data" / "audit" / "simple.csv"
AUDIT_COMPREHENSIVE_PATH = _PROJECT_ROOT / "data" / "audit" / "comprehensive.csv"


def _ensure_audit_dir():
    AUDIT_SIMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _write_row(path: Path, row: dict, write_headers: bool):
    _ensure_audit_dir()
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=row.keys())
        if write_headers and not file_exists:
            w.writeheader()
        w.writerow(row)


def log_simple(agent_id: str, action_type: str, entity_id: str, outcome: str):
    """Append one simple audit entry (AL.1)."""
    row = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent_id": agent_id,
        "action_type": action_type,
        "entity_id": entity_id,
        "outcome": outcome,
    }
    _write_row(AUDIT_SIMPLE_PATH, row, write_headers=True)


def log_comprehensive(
    agent_id: str,
    action_type: str,
    entity_id: str,
    outcome: str,
    duration_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    payload_summary: Optional[str] = None,
):
    """Append one comprehensive audit entry (AL.2). No PII in payload_summary."""
    row = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent_id": agent_id,
        "action_type": action_type,
        "entity_id": entity_id,
        "outcome": outcome,
        "detail_level": "comprehensive",
        "duration_ms": duration_ms or "",
        "error_message": error_message or "",
        "payload_summary": payload_summary or "",
    }
    _write_row(AUDIT_COMPREHENSIVE_PATH, row, write_headers=True)
