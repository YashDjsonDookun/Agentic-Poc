"""
SMTP notifier. Config-driven; stub if no credentials.
"""
from shared.config_loader import get_services_config, get_env


def is_configured() -> bool:
    cfg = get_services_config().get("smtp", {})
    if not cfg.get("enabled"):
        return False
    host = get_env(cfg.get("host_env", "SMTP_HOST"))
    return bool(host)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send email. Returns True if sent."""
    if not is_configured():
        return False
    # TODO: aiosmtplib or similar
    return False
