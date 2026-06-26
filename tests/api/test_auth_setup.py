"""Stage 1.12 — B11 auth setup, invite links, password reset."""

from __future__ import annotations

import pytest
from tests.api.conftest import API_PREFIX, contest_url
from tests.api.stage_112_helpers import (
    NEW_SECURE_PASSWORD,
    apply_env,
    complete_setup,
    create_draft_contest,
    extract_setup_token,
    invite_participant,
    login_raw,
)


@pytest.mark.asyncio
async def test_invite_out(stage_112_api):
    """[INVITE-OUT] Invite response includes login, temp_password, setup_url."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client)
    data = await invite_participant(
        client, cid, h, email="invite@example.com", login="invite_user"
    )
    assert data["user_id"]
    assert data["login"] == "invite_user"
    assert data["temp_password"]
    assert data["status"] == "PENDING"
    assert "/auth/setup?token=" in data["setup_url"]


@pytest.mark.asyncio
async def test_setup_preview(stage_112_api):
    """[SETUP-PREVIEW] setup-preview returns login, mode, already_completed=false."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client)
    data = await invite_participant(
        client, cid, h, email="preview@example.com", login="preview_user"
    )
    token = extract_setup_token(data["setup_url"])
    resp = await client.get(f"{API_PREFIX}/auth/setup-preview", params={"token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["login"] == "preview_user"
    assert body["mode"] == "password_form"
    assert body["already_completed"] is False


@pytest.mark.asyncio
async def test_setup_complete(stage_112_api):
    """[SETUP-COMPLETE] complete-setup accepts invite and enables login with new password."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client)
    data = await invite_participant(
        client, cid, h, email="complete@example.com", login="complete_user"
    )
    result = await complete_setup(client, data["setup_url"])
    assert result["accepted"] is True
    assert result["already_completed"] is False

    parts = await client.get(contest_url(cid, "/participants"), headers=h)
    invited = next(p for p in parts.json() if p["user_id"] == data["user_id"])
    assert invited["status"] == "ACCEPTED"

    login = await login_raw(client, data["login"], NEW_SECURE_PASSWORD)
    assert login.status_code == 200
    assert login.json()["is_temp_password"] is False


@pytest.mark.asyncio
async def test_setup_idempotent(stage_112_api):
    """[SETUP-IDEMPOTENT] repeat complete-setup returns already_completed."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client)
    data = await invite_participant(
        client, cid, h, email="idem@example.com", login="idem_user"
    )
    token = extract_setup_token(data["setup_url"])
    first = await client.post(
        f"{API_PREFIX}/auth/complete-setup",
        json={"token": token, "new_password": NEW_SECURE_PASSWORD},
    )
    assert first.status_code == 200
    second = await client.post(
        f"{API_PREFIX}/auth/complete-setup",
        json={"token": token, "new_password": NEW_SECURE_PASSWORD},
    )
    assert second.status_code == 200
    assert second.json()["already_completed"] is True


@pytest.mark.asyncio
async def test_login_gate_enforce_true(stage_112_api):
    """[LOGIN-GATE] temp password login blocked when ENFORCE_PASSWORD_SETUP=true."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client)
    data = await invite_participant(
        client, cid, h, email="gate@example.com", login="gate_user"
    )
    resp = await login_raw(client, data["login"], data["temp_password"])
    assert resp.status_code == 403
    assert resp.json()["code"] == "PASSWORD_SETUP_REQUIRED"


@pytest.mark.asyncio
async def test_login_gate_enforce_false(tmp_path, monkeypatch):
    """[LOGIN-GATE] legacy temp login allowed when ENFORCE_PASSWORD_SETUP=false."""
    apply_env(monkeypatch, {"ENFORCE_PASSWORD_SETUP": "false"})
    from tests.api.conftest import _make_api_client

    async for client, _, _ in _make_api_client(
        tmp_path, monkeypatch, "login_gate_legacy.db", instant_delete=False, load_data=False
    ):
        cid, h = await create_draft_contest(client)
        data = await invite_participant(
            client, cid, h, email="legacy@example.com", login="legacy_user"
        )
        resp = await login_raw(client, data["login"], data["temp_password"])
        assert resp.status_code == 200
        assert resp.json()["is_temp_password"] is True
        break


@pytest.mark.asyncio
async def test_reset_request(stage_112_api):
    """[RESET-REQUEST] password reset always returns 200 with privacy message."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client)
    data = await invite_participant(
        client, cid, h, email="reset@example.com", login="reset_user"
    )
    await complete_setup(client, data["setup_url"], new_password=NEW_SECURE_PASSWORD)

    known = await client.post(
        f"{API_PREFIX}/auth/request-password-reset",
        json={"email": "reset@example.com"},
    )
    assert known.status_code == 200
    msg = known.json()["message"]

    unknown = await client.post(
        f"{API_PREFIX}/auth/request-password-reset",
        json={"email": "nobody@example.com"},
    )
    assert unknown.status_code == 200
    assert unknown.json()["message"] == msg
