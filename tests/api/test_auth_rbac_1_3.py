"""[AUTH-*] [RBAC-*] Stage 1.3 auth and role checks."""

from __future__ import annotations

import httpx
import pytest

from tests.api.conftest import API_PREFIX, TEST_PASSWORD, api_login, auth_header


@pytest.mark.asyncio
async def test_auth_login_valid(loaded_api):
    """[AUTH-LOGIN] valid creds → 200 + token."""
    client, _, _ = loaded_api
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"login": "shutov", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data.get("is_temp_password") is False


@pytest.mark.asyncio
async def test_auth_login_invalid(loaded_api):
    """[AUTH-LOGIN] bad creds → 401."""
    client, _, _ = loaded_api
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"login": "shutov", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_temp_password_restricted(stage_112_api):
    """[AUTH-TEMP] temp login blocked; after complete-setup user gets JWT."""
    from tests.api.stage_112_helpers import (
        NEW_SECURE_PASSWORD,
        complete_setup,
        create_draft_contest,
        invite_participant,
        login_raw,
    )

    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Auth Temp")
    data = await invite_participant(
        client, cid, h, email="temp_gate@example.com", login="temp_gate_user"
    )

    blocked = await login_raw(client, data["login"], data["temp_password"])
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "PASSWORD_SETUP_REQUIRED"

    await complete_setup(client, data["setup_url"])
    token = await api_login(client, data["login"], NEW_SECURE_PASSWORD)
    headers = auth_header(token)

    me = await client.get(f"{API_PREFIX}/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["is_temp_password"] is False

    change = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=headers,
        json={"old_password": NEW_SECURE_PASSWORD, "new_password": "newpass456"},
    )
    assert change.status_code == 200


@pytest.mark.asyncio
async def test_rbac_user_cannot_supervisor(loaded_api):
    """[RBAC-USER] USER cannot call SUPERVISOR endpoint → 403."""
    client, _, _ = loaded_api
    token = await api_login(client, "shutov")
    resp = await client.get(
        f"{API_PREFIX}/admin/contest-settings",
        headers=auth_header(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_public_leaderboard(loaded_api):
    """[RBAC-PUB] public GET leaderboard without token → 200."""
    client, sf, _ = loaded_api
    from tests.api.conftest import ensure_contest_running, get_round_id

    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 1)
    calc = await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/calculate",
        headers=auth_header(sup),
    )
    assert calc.status_code == 200

    resp = await client.get(f"{API_PREFIX}/leaderboard")
    assert resp.status_code == 200
    assert "leaderboard" in resp.json()


@pytest.mark.asyncio
async def test_rbac_admin_recalculate(loaded_api):
    """[RBAC-ADMIN] recalculate ADMIN only."""
    client, sf, _ = loaded_api
    from tests.api.conftest import ensure_contest_running, get_round_id

    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 1)
    await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/calculate",
        headers=auth_header(sup),
    )

    user_token = await api_login(client, "shutov")
    denied = await client.post(
        f"{API_PREFIX}/admin/recalculate",
        headers=auth_header(user_token),
    )
    assert denied.status_code == 403

    admin = await api_login(client, "admin_api")
    ok = await client.post(
        f"{API_PREFIX}/admin/recalculate",
        headers=auth_header(admin),
    )
    assert ok.status_code == 200
