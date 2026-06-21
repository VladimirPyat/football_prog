"""[MULTI-*] Stage 1.4 multi-contest isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from database.models import ContestLifecycleStatus, Round, RoundStatus, User
from tests.api.conftest import (
    API_PREFIX,
    TEST_PASSWORD,
    _load_teams_csv,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round_id,
)


@pytest.mark.asyncio
async def test_multi_isolate_teams(empty_api):
    """[MULTI-ISOLATE] Teams in contest A not visible in contest B."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    ca = await client.post(f"{API_PREFIX}/contests", headers=h, json={"name": "Contest A"})
    cb = await client.post(f"{API_PREFIX}/contests", headers=h, json={"name": "Contest B"})
    cid_a, cid_b = ca.json()["id"], cb.json()["id"]

    await client.post(
        contest_url(cid_a, "/teams"),
        headers=h,
        json={"name": "Alpha FC", "short_name": "ALP"},
    )
    await client.post(
        contest_url(cid_b, "/teams"),
        headers=h,
        json={"name": "Beta FC", "short_name": "BET"},
    )

    teams_a = await client.get(contest_url(cid_a, "/teams"), headers=h)
    teams_b = await client.get(contest_url(cid_b, "/teams"), headers=h)
    names_a = {t["name"] for t in teams_a.json()}
    names_b = {t["name"] for t in teams_b.json()}
    assert "Alpha FC" in names_a
    assert "Alpha FC" not in names_b
    assert "Beta FC" in names_b


@pytest.mark.asyncio
async def test_multi_running_while_draft(empty_api):
    """[MULTI-RUNNING] Contest A RUNNING while B still DRAFT."""
    client, sf, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    ca = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Running Contest", "total_teams": 16},
    )
    cb = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Draft Contest", "total_teams": 16},
    )
    cid_a, cid_b = ca.json()["id"], cb.json()["id"]

    for row in _load_teams_csv()[:2]:
        for cid in (cid_a, cid_b):
            await client.post(
                contest_url(cid, "/teams"),
                headers=h,
                json={"name": row["full_name"], "short_name": row["short_name"]},
            )

    teams_a = await client.get(contest_url(cid_a, "/teams"), headers=h)
    tids = [t["id"] for t in teams_a.json()[:2]]
    now = datetime.now(timezone.utc)
    match_at = now + timedelta(days=7)
    deadline = (match_at - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(cid_a, "/admin/rounds"),
        headers=h,
        json={
            "number": 1,
            "deadline": deadline,
            "matches": [
                {
                    "team1_id": tids[0],
                    "team2_id": tids[1],
                    "date_time": match_at.isoformat(),
                }
            ],
        },
    )
    rid = rnd.json()["round_id"]
    await client.post(contest_url(cid_a, f"/admin/rounds/{rid}/activate"), headers=h)

    detail_a = await client.get(contest_url(cid_a, ""), headers=h)
    detail_b = await client.get(contest_url(cid_b, ""), headers=h)
    assert detail_a.json()["status"] == ContestLifecycleStatus.RUNNING.value
    assert detail_b.json()["status"] == ContestLifecycleStatus.DRAFT.value


@pytest.mark.asyncio
async def test_multi_tiebreak_per_contest(loaded_api):
    """[MULTI-TIEBREAK] Same user, different exceptional points per contest."""
    client, sf, _ = loaded_api
    admin = await api_login(client, "admin_api")
    h_admin = auth_header(admin)

    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=auth_header(await api_login(client, "supervisor_api")),
        json={"name": "Second Contest"},
    )
    cid2 = created.json()["id"]

    async with sf() as session:
        from database.models import ContestParticipant, ParticipantStatus, User

        uid = await session.scalar(select(User.id).where(User.login == "shutov"))
        session.add(
            ContestParticipant(
                contest_id=cid2,
                user_id=uid,
                status=ParticipantStatus.ACCEPTED,
            )
        )
        await session.commit()

    await client.put(
        contest_url(1, f"/participants/{uid}/exceptional-tiebreak"),
        headers=h_admin,
        json={"points": 3},
    )
    await client.put(
        contest_url(cid2, f"/participants/{uid}/exceptional-tiebreak"),
        headers=h_admin,
        json={"points": 9},
    )

    async with sf() as session:
        from database.models import ContestParticipant

        p1 = await session.get(ContestParticipant, (1, uid))
        p2 = await session.get(ContestParticipant, (cid2, uid))
        assert p1.exceptional_tiebreak_points == 3
        assert p2.exceptional_tiebreak_points == 9
