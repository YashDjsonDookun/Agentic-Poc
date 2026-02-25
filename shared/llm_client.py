"""
LLM client: extension point for when LLM is provided (config-only until then).
Swap this for a real client when endpoint/key are available.
"""
from typing import Optional


async def complete(prompt: str, system: str = "", max_tokens: int = 1024) -> Optional[str]:
    """No-op until LLM is configured. Returns None or placeholder."""
    return None
