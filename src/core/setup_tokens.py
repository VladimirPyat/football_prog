"""Signed setup tokens for invite acceptance and password reset."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from config.settings import get_settings
from jose import JWTError, jwt

SETUP_PURPOSE = "setup_password"


def create_setup_token(*, user_id: int, contest_id: int | None = None) -> str:
    """Issue a short-lived JWT for /auth/setup and complete-setup."""
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(hours=settings.setup_token_expire_hours)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "purpose": SETUP_PURPOSE,
        "exp": expire,
    }
    if contest_id is not None:
        payload["contest_id"] = contest_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_setup_token(token: str) -> dict[str, Any]:
    """Validate token signature, expiry, and purpose."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("purpose") != SETUP_PURPOSE:
        raise ValueError("Invalid token purpose")
    return payload


def build_setup_url(token: str) -> str:
    """Frontend deep link consumed by /auth/setup."""
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/auth/setup?token={quote(token, safe='')}"
