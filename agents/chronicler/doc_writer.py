"""
Doc Writer (4.2): from closed incidents, generate runbook/SOP (templates + rules; LLM placeholder).
"""
from pathlib import Path
from shared.config_loader import PROJECT_ROOT

GENERATED = PROJECT_ROOT / "knowledge" / "generated"


def write_runbook(incidents: list[dict], output_name: str = "generated_runbook.md") -> Path:
    """Generate one runbook from incident list. Template-based for MVP."""
    path = GENERATED / output_name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "# Generated Runbook\n\nBased on incidents.\n\n"
    for inc in incidents:
        content += f"- {inc.get('summary', '')} ({inc.get('service', '')})\n"
    path.write_text(content, encoding="utf-8")
    return path
