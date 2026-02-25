"""
Publisher (4.3): publish to local knowledge/; optional notify. Provision for Confluence/SN KB.
"""
from pathlib import Path
from agents.chronicler.doc_writer import write_runbook


def publish_runbook(runbook_path: Path, notify: bool = False) -> bool:
    """Publish is already local (knowledge/generated/). Optionally send 'New runbook' message."""
    if notify:
        # from integrations.teams import send_message
        pass
    return runbook_path.exists()
