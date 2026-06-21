"""Stage 1.8 — GET /me/contests (B1)."""

from __future__ import annotations

import pytest

from tests.api.conftest import API_PREFIX, api_login, auth_header, contest_url


@pytest.mark.asyncio
async def test_me_contests_user(empty_api):
    """[ME-CONTESTS-USER] Invited user sees enrolled contest with participant_status."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "My Contest"},
    )
    assert created.status_code == 200
    cid = created.json()["id"]

    invite = await client.post(
        contest_url(cid, "/participants"),
        headers=h,
        json={
            "email": "invitee@example.com",
            "first_name": "Invite",
            "last_name": "User",
            "login": "invitee_me",
        },
    )
    assert invite.status_code == 200
    data = invite.json()
    token = await api_login(client, data["login"], data["temp_password"])

    resp = await client.get(f"{API_PREFIX}/me/contests", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == cid
    assert body[0]["participant_status"] == "PENDING"
    assert body[0]["role"] == "USER"
    assert body[0]["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_me_contests_empty(empty_api):
    """[ME-CONTESTS-EMPTY] User with no enrollments gets empty list."""
    client, _, _ = empty_api
    token = await api_login(client, "temp_user")

    resp = await client.get(f"{API_PREFIX}/me/contests", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_me_contests_rbac(empty_api):
    """[ME-CONTESTS-RBAC] Missing Authorization → 401."""
    client, _, _ = empty_api
    resp = await client.get(f"{API_PREFIX}/me/contests")
    assert resp.status_code == 401
