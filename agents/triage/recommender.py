"""
Recommender (2.4): match incident to runbooks; suggest 1–2 with link. No auto-action.
"""
from pathlib import Path
from shared.config_loader import PROJECT_ROOT

KNOWLEDGE = PROJECT_ROOT / "knowledge" / "runbooks"
SOP = PROJECT_ROOT / "knowledge" / "sops"
GENERATED = PROJECT_ROOT / "knowledge" / "generated"


def suggest_runbooks(incident_summary: str, service: str) -> list[dict]:
    """Return list of {path, reason, name}. Keyword/tag match over knowledge/runbooks, sops, generated."""
    results = []
    summary_lower = (incident_summary or "").lower()
    service_lower = (service or "").lower()
    for base in (KNOWLEDGE, SOP, GENERATED):
        if not base.exists():
            continue
        for f in sorted(base.glob("*.md")):
            name = f.stem.lower()
            words = name.replace("-", " ").split("_")
            if service_lower in name or any(w in summary_lower for w in words if len(w) > 2):
                results.append({"path": str(f), "reason": f"Match: {f.stem}", "name": f.stem})
    return results[:2]
