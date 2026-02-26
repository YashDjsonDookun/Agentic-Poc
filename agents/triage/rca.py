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


# Rule-based templates: metric (or prefix) -> list of (hypothesis_text, confidence, evidence_snippet)
_RCA_TEMPLATES = {
    "cpu_percent": [
        ("High CPU likely due to load spike or runaway process", 0.75, "metric: cpu_percent"),
        ("Check for recent deployment or config change on same host", 0.5, "correlation window"),
    ],
    "memory_percent": [
        ("High memory may indicate leak or cache growth", 0.7, "metric: memory_percent"),
        ("Review recent code/config changes affecting heap or cache", 0.5, "correlation"),
    ],
    "error_rate": [
        ("Error spike may indicate deployment, dependency failure, or bad config", 0.8, "metric: error_rate"),
        ("Check upstream services and recent releases", 0.6, "dependency check"),
    ],
    "up": [
        ("Service down: check process, host, or network", 0.85, "metric: up=0"),
        ("Possible maintenance window or deployment in progress", 0.4, "time window"),
    ],
    "latency_p99_ms": [
        ("Latency spike may be due to saturation, slow dependency, or GC", 0.7, "metric: latency_p99_ms"),
        ("Check database or downstream service health", 0.55, "dependency"),
    ],
}


def run_rca(incident_id: str, service: str, summary: str, time_window: dict = None, context: dict = None) -> List[Hypothesis]:
    """Return 1–3 hypotheses. Rule-based: map metric + service to template hypotheses."""
    context = context or {}
    metric = context.get("metric", "")
    value = context.get("value")
    hypotheses = []
    # Match by exact metric or by prefix (e.g. latency_*)
    for key, template_list in _RCA_TEMPLATES.items():
        if key == metric or (metric and metric.startswith(key)):
            for text, conf, evidence in template_list[:2]:
                hypotheses.append(Hypothesis(text=text, confidence=conf, evidence_snippet=evidence))
            break
    if not hypotheses:
        hypotheses = [
            Hypothesis(
                f"Possible root cause for {service}: review logs and recent changes",
                0.5,
                f"service={service}, metric={metric}",
            ),
        ]
    return hypotheses[:3]
