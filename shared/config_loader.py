"""Load YAML config; resolve paths relative to project root. Integration credentials from UI (local file), not .env."""
import os
from pathlib import Path
from typing import Any, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_TABLES_DIR = CONFIG_DIR / "tables"
# UI-configured credentials (gitignored); not using .env for integrations
LOCAL_INTEGRATIONS_PATH = CONFIG_DIR / "local.integrations.yaml"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_agents_config() -> dict:
    return _load_yaml(CONFIG_DIR / "agents.yaml")


def get_services_config() -> dict:
    return _load_yaml(CONFIG_DIR / "services.yaml")


def get_integrations_config() -> dict:
    return _load_yaml(CONFIG_DIR / "integrations.yaml")


def get_rag_config() -> dict:
    return _load_yaml(CONFIG_DIR / "rag.yaml")


def get_local_integrations() -> dict:
    """Credentials and values configured from UI (stored in gitignored file)."""
    return _load_yaml(LOCAL_INTEGRATIONS_PATH)


def save_local_integrations(data: dict) -> None:
    """Save UI-configured integration values (credentials) to local file."""
    _save_yaml(LOCAL_INTEGRATIONS_PATH, data)


def get_integration_credentials(integration: str) -> dict:
    """Get credentials for one integration from UI config (local file). Returns dict of field names to values."""
    return get_local_integrations().get(integration) or {}


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get secret from env (used for services like LLM/Teams; integrations use UI config)."""
    return os.environ.get(key, default)
