"""Admin user management API tests."""

from __future__ import annotations

import httpx
import pytest

from tests.api.conftest import API_PREFIX, TEST_PASSWORD, api_login, auth_header


@pytest.mark.asyncio
async def test_admin_create_supervisor(loaded_api):
    """ADMIN can create SUPERVISOR via POST /admin/users/supervisor."""
    client, _, _ = loaded_api
    admin = await api_login(client, "admin_api")

    resp = await client.post(
        f"{API_PREFIX}/admin/users/supervisor",
        headers=auth_header(admin),
        json={
            "login": "new_supervisor",
            "password": "superpass123",
            "first_name": "New",
            "last_name": "Supervisor",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["user"]
    assert data["login"] == "new_supervisor"
    assert data["role"] == "SUPERVISOR"

    token = await api_login(client, "new_supervisor", password="superpass123")
    me = await client.get(f"{API_PREFIX}/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["role"] == "SUPERVISOR"


@pytest.mark.asyncio
async def test_supervisor_cannot_create_supervisor(loaded_api):
    """SUPERVISOR cannot create another SUPERVISOR → 403."""
    client, _, _ = loaded_api
    sup = await api_login(client, "supervisor_api")

    resp = await client.post(
        f"{API_PREFIX}/admin/users/supervisor",
        headers=auth_header(sup),
        json={
            "login": "blocked_supervisor",
            "password": "x",
            "first_name": "X",
            "last_name": "Y",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_supervisor_duplicate_login(loaded_api):
    """Duplicate login → 400 with VALIDATION_ERROR."""
    client, _, _ = loaded_api
    admin = await api_login(client, "admin_api")

    resp = await client.post(
        f"{API_PREFIX}/admin/users/supervisor",
        headers=auth_header(admin),
        json={
            "login": "supervisor_api",
            "password": "x",
            "first_name": "Dup",
            "last_name": "User",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"
