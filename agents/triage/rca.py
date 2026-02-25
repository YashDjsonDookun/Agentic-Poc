"""
RCA Agent (2.2): hypotheses + confidence + evidence. LLM config-only; use rules/templates until wired.
"""
from typing import List
from dataclasses import dataclass


@dataclass
class Hypothesis:
    text: str
    confidence: float
    evidence_snippet: str


def run_rca(incident_id: str, service: str, summary: str, time_window: dict) -> List[Hypothesis]:
    """Return 1–3 hypotheses. For MVP: rule-based or placeholder."""
    return [
        Hypothesis("Simulated root cause (deploy or config change)", 0.7, "Evidence placeholder"),
    ]
