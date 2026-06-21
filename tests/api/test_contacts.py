"""Stage 1.8 — GET/PATCH /auth/me/contacts (B3)."""

from __future__ import annotations

import pytest

from tests.api.conftest import API_PREFIX, api_login, auth_header, contest_url


@pytest.mark.asyncio
async def test_contacts_get_default(empty_api):
    """[CONTACTS-GET-DEFAULT] Missing contact row returns null defaults."""
    client, _, _ = empty_api
    token = await api_login(client, "temp_user")

    resp = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json() == {
        "email": None,
        "vk_id": None,
        "tg_id": None,
        "notify_enabled": False,
    }


@pytest.mark.asyncio
async def test_contacts_patch(empty_api):
    """[CONTACTS-PATCH] Partial PATCH updates only sent fields."""
    client, _, _ = empty_api
    token = await api_login(client, "temp_user")
    h = auth_header(token)

    patch1 = await client.patch(
        f"{API_PREFIX}/auth/me/contacts",
        headers=h,
        json={"vk_id": "@myvk", "notify_enabled": True},
    )
    assert patch1.status_code == 200
    assert patch1.json()["vk_id"] == "@myvk"
    assert patch1.json()["notify_enabled"] is True
    assert patch1.json()["email"] is None

    get1 = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=h)
    assert get1.json()["vk_id"] == "@myvk"
    assert get1.json()["notify_enabled"] is True
    assert get1.json()["email"] is None

    patch2 = await client.patch(
        f"{API_PREFIX}/auth/me/contacts",
        headers=h,
        json={"email": "user@example.com"},
    )
    assert patch2.status_code == 200
    get2 = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=h)
    assert get2.json()["email"] == "user@example.com"
    assert get2.json()["vk_id"] == "@myvk"


@pytest.mark.asyncio
async def test_contacts_invite(empty_api):
    """[CONTACTS-INVITE] Invite email appears in contacts after participant invite."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Contacts Contest"},
    )
    cid = created.json()["id"]
    invite = await client.post(
        contest_url(cid, "/participants"),
        headers=h,
        json={
            "email": "invited@example.com",
            "first_name": "Inv",
            "last_name": "User",
            "login": "contacts_invitee",
        },
    )
    data = invite.json()
    token = await api_login(client, data["login"], data["temp_password"])

    resp = await client.get(
        f"{API_PREFIX}/auth/me/contacts",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "invited@example.com"


@pytest.mark.asyncio
async def test_contacts_temp_password(empty_api):
    """[CONTACTS-TEMP-PW] Temp-password user can GET/PATCH contacts."""
    client, _, _ = empty_api
    token = await api_login(client, "temp_user")
    h = auth_header(token)

    get_resp = await client.get(f"{API_PREFIX}/auth/me/contacts", headers=h)
    assert get_resp.status_code == 200

    patch_resp = await client.patch(
        f"{API_PREFIX}/auth/me/contacts",
        headers=h,
        json={"tg_id": "123"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["tg_id"] == "123"
