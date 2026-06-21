"""Admin notification stub — single extension point for critical alerts."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def notify_admin(event: str, *, detail: str, context: dict | None = None) -> None:
    """Log critical alert; replace with email/Telegram in one place later."""
    logger.error("ADMIN_ALERT event=%s detail=%s context=%s", event, detail, context)
