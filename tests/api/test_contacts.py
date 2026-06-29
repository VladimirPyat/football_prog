"""Stage 1.8 — GET/PATCH /auth/me/contacts (B3)."""

from __future__ import annotations

import pytest

from tests.api.conftest import API_PREFIX, api_login, auth_header, contest_url
from tests.api.stage_112_helpers import (
    NEW_SECURE_PASSWORD,
    complete_setup,
    create_draft_contest,
    invite_participant,
)


async def _token_for_setup_completed_user(client, login: str) -> str:
    return await api_login(client, login, NEW_SECURE_PASSWORD)


@pytest.mark.asyncio
async def test_contacts_get_default(stage_112_api):
    """[CONTACTS-GET-DEFAULT] Missing contact row returns null defaults."""
    from core.security import hash_password
    from database.models import User, UserRole

    client, sf, _ = stage_112_api
    async with sf() as session:
        async with session.begin():
            session.add(
                User(
                    login="contacts_lonely",
                    password_hash=hash_password(NEW_SECURE_PASSWORD),
                    role=UserRole.USER.value,
                    first_name="Lonely",
                    last_name="Contacts",
                    is_temp_password=False,
                )
            )
    token = await api_login(client, "contacts_lonely", NEW_SECURE_PASSWORD)

    resp = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == {
        "email": None,
        "vk_id": None,
        "tg_id": None,
        "notify_enabled": False,
    }


@pytest.mark.asyncio
async def test_contacts_patch(stage_112_api):
    """[CONTACTS-PATCH] Partial PATCH updates only sent fields."""
    from core.security import hash_password
    from database.models import User, UserRole

    client, sf, _ = stage_112_api
    async with sf() as session:
        async with session.begin():
            session.add(
                User(
                    login="contacts_patch_user",
                    password_hash=hash_password(NEW_SECURE_PASSWORD),
                    role=UserRole.USER.value,
                    first_name="Patch",
                    last_name="User",
                    is_temp_password=False,
                )
            )
    token = await api_login(client, "contacts_patch_user", NEW_SECURE_PASSWORD)
    auth = auth_header(token)

    patch1 = await client.patch(
        f"{API_PREFIX}/auth/me/contacts",
        headers=auth,
        json={"vk_id": "@myvk", "notify_enabled": True},
    )
    assert patch1.status_code == 200
    assert patch1.json()["vk_id"] == "@myvk"
    assert patch1.json()["notify_enabled"] is True
    assert patch1.json()["email"] is None

    get1 = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=auth)
    assert get1.json()["vk_id"] == "@myvk"
    assert get1.json()["notify_enabled"] is True
    assert get1.json()["email"] is None

    patch2 = await client.patch(
        f"{API_PREFIX}/auth/me/contacts",
        headers=auth,
        json={"email": "user@example.com"},
    )
    assert patch2.status_code == 200
    get2 = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=auth)
    assert get2.json()["email"] == "user@example.com"
    assert get2.json()["vk_id"] == "@myvk"


@pytest.mark.asyncio
async def test_contacts_invite(stage_112_api):
    """[CONTACTS-INVITE] Invite email appears in contacts after participant invite."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Contacts Contest")
    invite = await invite_participant(
        client,
        cid,
        h,
        email="invited@example.com",
        first_name="Inv",
        last_name="User",
        login="contacts_invitee",
    )
    await complete_setup(client, invite["setup_url"])
    token = await _token_for_setup_completed_user(client, invite["login"])

    resp = await client.get(
        f"{API_PREFIX}/auth/me/contacts",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "invited@example.com"


@pytest.mark.asyncio
async def test_contacts_temp_password(stage_112_api):
    """[CONTACTS-SETUP-COMPLETE] Setup-completed user can GET/PATCH contacts."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Contacts Setup")
    data = await invite_participant(
        client, cid, h, email="contacts_setup@example.com", login="contacts_setup_user"
    )
    await complete_setup(client, data["setup_url"])
    token = await _token_for_setup_completed_user(client, data["login"])
    auth = auth_header(token)

    get_resp = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=auth)
    assert get_resp.status_code == 200

    patch_resp = await client.patch(
        f"{API_PREFIX}/auth/me/contacts",
        headers=auth,
        json={"tg_id": "123"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["tg_id"] == "123"
