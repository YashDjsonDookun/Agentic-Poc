"""Load YAML config; resolve paths relative to project root. No secrets in files (env only)."""
import os
from pathlib import Path
from typing import Any, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_TABLES_DIR = CONFIG_DIR / "tables"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_agents_config() -> dict:
    return _load_yaml(CONFIG_DIR / "agents.yaml")


def get_services_config() -> dict:
    return _load_yaml(CONFIG_DIR / "services.yaml")


def get_integrations_config() -> dict:
    return _load_yaml(CONFIG_DIR / "integrations.yaml")


def get_rag_config() -> dict:
    return _load_yaml(CONFIG_DIR / "rag.yaml")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get secret from env only (S.1)."""
    return os.environ.get(key, default)
