"""Stage 1.8 — GET /me/contests (B1)."""

from __future__ import annotations

import pytest
from core.security import hash_password
from database.models import User, UserRole

from tests.api.conftest import API_PREFIX, api_login, auth_header, contest_url
from tests.api.stage_112_helpers import (
    NEW_SECURE_PASSWORD,
    complete_setup,
    create_draft_contest,
    invite_participant,
)


@pytest.mark.asyncio
async def test_me_contests_user(stage_112_api):
    """[ME-CONTESTS-USER] Invited user sees enrolled contest with participant_status."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="My Contest")

    invite = await invite_participant(
        client,
        cid,
        h,
        email="invitee@example.com",
        first_name="Invite",
        last_name="User",
        login="invitee_me",
    )
    await complete_setup(client, invite["setup_url"])
    token = await api_login(client, invite["login"], NEW_SECURE_PASSWORD)

    resp = await client.get(f"{API_PREFIX}/me/contests", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == cid
    assert body[0]["participant_status"] == "ACCEPTED"
    assert body[0]["role"] == "USER"
    assert body[0]["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_me_contests_empty(stage_112_api):
    """[ME-CONTESTS-EMPTY] User with no enrollments gets empty list."""
    client, sf, _ = stage_112_api
    async with sf() as session:
        async with session.begin():
            session.add(
                User(
                    login="lonely_user",
                    password_hash=hash_password(NEW_SECURE_PASSWORD),
                    role=UserRole.USER.value,
                    first_name="Lonely",
                    last_name="User",
                    is_temp_password=False,
                )
            )
    token = await api_login(client, "lonely_user", NEW_SECURE_PASSWORD)

    resp = await client.get(f"{API_PREFIX}/me/contests", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_me_contests_rbac(stage_112_api):
    """[ME-CONTESTS-RBAC] Missing Authorization → 401."""
    client, _, _ = stage_112_api
    resp = await client.get(f"{API_PREFIX}/me/contests")
    assert resp.status_code == 401
