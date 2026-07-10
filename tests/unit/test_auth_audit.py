"""Unit tests for auth audit logging."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from core.auth_audit import AuthAuditMiddleware, setup_auth_audit_logging


@pytest.fixture
def auth_log_path(tmp_path: Path) -> Path:
    path = tmp_path / "auth.log"
    setup_auth_audit_logging(path)
    return path


def _build_login_app():
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(AuthAuditMiddleware)

    @app.post("/api/v1/auth/login")
    async def login(body: dict) -> JSONResponse:
        if body.get("login") == "good" and body.get("password") == "secret":
            return JSONResponse({"access_token": "tok"})
        return JSONResponse({"detail": "fail"}, status_code=401)

    return app


def test_auth_audit_logs_success_and_failure(auth_log_path: Path) -> None:
    client = TestClient(_build_login_app())

    ok = client.post(
        "/api/v1/auth/login",
        json={"login": "good", "password": "secret"},
    )
    assert ok.status_code == 200

    bad = client.post(
        "/api/v1/auth/login",
        json={"login": "bad", "password": "wrong"},
    )
    assert bad.status_code == 401

    lines = auth_log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert "login=good" in lines[0]
    assert "outcome=success" in lines[0]
    assert "password" not in lines[0]
    assert "login=bad" in lines[1]
    assert "outcome=failed" in lines[1]
