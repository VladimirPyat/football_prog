"""[SETUP-*] Stage 1.4 contest setup phase over HTTP."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import ContestLifecycleStatus, User
from tests.api.conftest import (
    API_PREFIX,
    DEFAULT_CONTEST_ID,
    TEST_PASSWORD,
    _load_contest_defaults,
    _load_teams_csv,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round_id,
)


@pytest.mark.asyncio
async def test_setup_create_contest(empty_api):
    """[SETUP-CREATE] POST /contests → DRAFT, is_locked=false."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    defaults = _load_contest_defaults()
    structure = defaults["contest_structure"]
    resp = await client.post(
        f"{API_PREFIX}/contests",
        headers=auth_header(sup),
        json={
            "name": "Setup Test",
            "total_teams": structure["total_teams"],
            "matches_per_round": structure["matches_per_round"],
            "total_rounds": structure["total_rounds"],
            "is_round_robin": structure["is_round_robin"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == ContestLifecycleStatus.DRAFT.value
    assert data["is_locked"] is False


@pytest.mark.asyncio
async def test_setup_patch_before_activate(empty_api):
    """[SETUP-PATCH] PATCH rules before activate → 200."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Patch Test"},
    )
    cid = created.json()["id"]
    resp = await client.patch(
        contest_url(cid, ""),
        headers=h,
        json={"total_teams": 18},
    )
    assert resp.status_code == 200
    assert resp.json()["total_teams"] == 18


@pytest.mark.asyncio
async def test_setup_teams_crud_and_duplicate(empty_api):
    """[SETUP-TEAMS] CRUD 16 teams; duplicate name → 400."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Teams Test", "total_teams": 16},
    )
    cid = created.json()["id"]

    for row in _load_teams_csv():
        resp = await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={
                "name": row["full_name"],
                "short_name": row["short_name"],
            },
        )
        assert resp.status_code == 200, resp.text

    teams = await client.get(contest_url(cid, "/teams"), headers=h)
    assert len(teams.json()) == 16

    dup = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Duplicate", "short_name": "Дин"},
    )
    assert dup.status_code == 400


@pytest.mark.asyncio
async def test_setup_teams_locked_after_activate(empty_api):
    """[SETUP-TEAMS-LOCK] after activate, POST team → 403."""
    client, sf, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Lock Teams", "total_teams": 16},
    )
    cid = created.json()["id"]
    for row in _load_teams_csv()[:16]:
        await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )

    from datetime import datetime, timedelta, timezone

    teams_resp = await client.get(contest_url(cid, "/teams"), headers=h)
    team_ids = [t["id"] for t in teams_resp.json()[:2]]
    now = datetime.now(timezone.utc)
    match_at = now + timedelta(days=7)
    deadline = (match_at - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(cid, "/admin/rounds"),
        headers=h,
        json={
            "number": 1,
            "deadline": deadline,
            "matches": [
                {
                    "team1_id": team_ids[0],
                    "team2_id": team_ids[1],
                    "date_time": match_at.isoformat(),
                }
            ],
        },
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    await client.post(contest_url(cid, f"/admin/rounds/{rid}/activate"), headers=h)

    locked = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Extra", "short_name": "XTR"},
    )
    assert locked.status_code == 403


@pytest.mark.asyncio
async def test_setup_participant_invite(stage_112_api):
    """[SETUP-PART] POST participant → complete-setup → login works."""
    from tests.api.stage_112_helpers import NEW_SECURE_PASSWORD, complete_setup, invite_participant

    client, _, _ = stage_112_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Participants"},
    )
    cid = created.json()["id"]
    data = await invite_participant(
        client,
        cid,
        h,
        email="newuser@example.com",
        first_name="New",
        last_name="User",
        login="newuser_e2e",
    )
    assert data["temp_password"]
    await complete_setup(client, data["setup_url"])
    token = await api_login(client, data["login"], NEW_SECURE_PASSWORD)
    me = await client.get(f"{API_PREFIX}/auth/me", headers=auth_header(token))
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_setup_participant_lock_after_activate(loaded_api):
    """[SETUP-PART-LOCK] after activate, DELETE participant → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    async with sf() as session:
        uid = await session.scalar(select(User.id).where(User.login == "shutov"))
    resp = await client.delete(
        contest_url(DEFAULT_CONTEST_ID, f"/participants/{uid}"),
        headers=h,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_setup_list_counts(empty_api):
    """[SETUP-LIST] GET teams/participants as SUPERVISOR → correct counts."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "List Test", "total_teams": 16},
    )
    cid = created.json()["id"]
    for row in _load_teams_csv():
        await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )
    for i in range(10):
        await client.post(
            contest_url(cid, "/participants"),
            headers=h,
            json={
                "email": f"user{i}@example.com",
                "first_name": f"F{i}",
                "last_name": f"L{i}",
            },
        )

    teams = await client.get(contest_url(cid, "/teams"), headers=h)
    parts = await client.get(contest_url(cid, "/participants"), headers=h)
    assert len(teams.json()) == 16
    assert len(parts.json()) == 10
