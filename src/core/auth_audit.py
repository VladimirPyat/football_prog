"""Dedicated auth audit logging (login attempts only — never passwords)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_AUTH_AUDIT_LOGGER_NAME = "auth.audit"
_LOGIN_PATH = "/api/v1/auth/login"


def setup_auth_audit_logging(auth_log_file: Path) -> logging.Logger:
    """Configure a file-only logger for auth audit events."""
    auth_log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_AUTH_AUDIT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        handler = logging.FileHandler(auth_log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger


def _auth_audit_logger() -> logging.Logger:
    return logging.getLogger(_AUTH_AUDIT_LOGGER_NAME)


def _extract_login(body: bytes) -> str:
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return ""
    login = data.get("login")
    return str(login).strip() if login is not None else ""


def _log_login_attempt(
    *,
    client_ip: str,
    login: str,
    status_code: int,
) -> None:
    outcome = "success" if status_code == 200 else "failed"
    timestamp = datetime.now(UTC).isoformat()
    safe_login = login or "(missing)"
    line = (
        f"{timestamp} ip={client_ip} login={safe_login} "
        f"status={status_code} outcome={outcome}"
    )
    _auth_audit_logger().info(line)


class AuthAuditMiddleware(BaseHTTPMiddleware):
    """Log login attempts to auth audit log without touching auth router code."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST" or request.url.path != _LOGIN_PATH:
            return await call_next(request)

        body = await request.body()
        login = _extract_login(body)
        client_ip = request.client.host if request.client else "unknown"

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        replay_request = Request(request.scope, receive)
        response = await call_next(replay_request)
        _log_login_attempt(
            client_ip=client_ip,
            login=login,
            status_code=response.status_code,
        )
        return response
