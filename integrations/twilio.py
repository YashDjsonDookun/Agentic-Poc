"""
Twilio (SMS). Config-driven; stub if no credentials.
"""
from shared.config_loader import get_services_config, get_env


def is_configured() -> bool:
    cfg = get_services_config().get("twilio", {})
    if not cfg.get("enabled"):
        return False
    sid = get_env(cfg.get("account_sid_env", "TWILIO_ACCOUNT_SID"))
    return bool(sid)


async def send_sms(to: str, body: str) -> bool:
    """Send SMS. Returns True if sent."""
    if not is_configured():
        return False
    # TODO: httpx to Twilio API
    return False
