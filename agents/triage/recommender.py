"""
Recommender (2.4): match incident to runbooks; suggest 1–2 with link. No auto-action.
"""
from pathlib import Path
from shared.config_loader import PROJECT_ROOT

KNOWLEDGE = PROJECT_ROOT / "knowledge" / "runbooks"
SOP = PROJECT_ROOT / "knowledge" / "sops"
GENERATED = PROJECT_ROOT / "knowledge" / "generated"


def suggest_runbooks(incident_summary: str, service: str) -> list[dict]:
    """Return list of {path, reason}. Keyword/tag match for MVP."""
    results = []
    for base in (KNOWLEDGE, SOP, GENERATED):
        if not base.exists():
            continue
        for f in base.glob("*.md"):
            name = f.stem.lower()
            if service.lower() in name or any(w in incident_summary.lower() for w in name.split("_")):
                results.append({"path": str(f), "reason": f"Match: {f.stem}"})
    return results[:2]
