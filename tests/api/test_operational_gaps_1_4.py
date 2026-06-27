"""Stage 1.4.1 operational gap tests — contest-scoped paths."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from database.models import Match, Round
from tests.api.conftest import (
    API_PREFIX,
    DEFAULT_CONTEST_ID,
    TEST_PASSWORD,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round10_match_ids,
    get_round_id,
)


@pytest.mark.asyncio
async def test_op_pred_privacy(loaded_api):
    """[OP-PRED-PRIVACY] Before deadline hide others; after deadline full table."""
    client, sf, _ = loaded_api
    shutov = await api_login(client, "shutov")
    volchenko = await api_login(client, "volchenko")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)

    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(shutov),
        json={"predictions": [{"match_id": m, "score1": 2, "score2": 1} for m in mids]},
    )

    before = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(volchenko),
    )
    assert before.status_code == 200
    data = before.json()
    assert data["deadline_passed"] is False
    volchenko_id = await _user_id(sf, "volchenko")
    for entry in data["entries"]:
        if entry["user_id"] != volchenko_id:
            assert entry["predictions"] is None

    async with sf() as session:
        async with session.begin():
            round_ = await session.get(Round, rid)
            round_.deadline = datetime.now(timezone.utc) - timedelta(days=1)

    after = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(volchenko),
    )
    assert after.status_code == 200
    assert after.json()["deadline_passed"] is True
    for entry in after.json()["entries"]:
        if entry["submitted"]:
            assert entry["predictions"] is not None


@pytest.mark.asyncio
async def test_op_supervisor_pred_privacy(loaded_api):
    """[OP-PRED-PRIVACY-SUP] SUPERVISOR has same pre-deadline privacy as USER."""
    client, sf, _ = loaded_api
    shutov = await api_login(client, "shutov")
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)

    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(shutov),
        json={"predictions": [{"match_id": m, "score1": 3, "score2": 0} for m in mids]},
    )

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(sup),
    )
    assert resp.status_code == 200
    shutov_id = await _user_id(sf, "shutov")
    for entry in resp.json()["entries"]:
        if entry["user_id"] == shutov_id:
            assert entry["predictions"] is None


async def _user_id(sf, login: str) -> int:
    async with sf() as session:
        from database.models import User

        return await session.scalar(select(User.id).where(User.login == login))


@pytest.mark.asyncio
async def test_op_24h_rule(loaded_api):
    """[OP-24H-RULE] PATCH ACTIVE round deadline inside lockout window → 403 DEADLINE_CHANGE_CLOSED."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        from database.models import Round, RoundStatus

        round_ = await session.get(Round, rid)
        assert round_ is not None
        # Set round to ACTIVE with a deadline 10h from now so the lockout window is closed
        round_.status = RoundStatus.ACTIVE
        near_deadline = datetime.now(timezone.utc) + timedelta(hours=10)
        round_.deadline = near_deadline
        await session.commit()

    # Try to move deadline 2 hours back — still in future and before matches, but lockout blocks it
    new_deadline = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    resp = await client.patch(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}"),
        headers=h,
        json={"deadline": new_deadline},
    )
    assert resp.status_code == 403
    assert resp.json().get("code") == "DEADLINE_CHANGE_CLOSED"


@pytest.mark.asyncio
async def test_op_round_edit(loaded_api):
    """[OP-ROUND-EDIT] PATCH ACTIVE round match datetime before deadline → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(Match.round_id == rid).limit(1)
        )
        mid = match.id
        new_dt = (match.date_time + timedelta(hours=2)).isoformat()

    resp = await client.patch(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}"),
        headers=h,
        json={"matches": [{"match_id": mid, "date_time": new_dt}]},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_op_round_create(loaded_api):
    """[OP-ROUND-CREATE] POST admin round DRAFT with 8 matches → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    async with sf() as session:
        from database.models import Team

        teams = (
            await session.scalars(
                select(Team)
                .where(Team.contest_id == DEFAULT_CONTEST_ID)
                .order_by(Team.id)
                .limit(16)
            )
        ).all()
        team_ids = [t.id for t in teams]

    now = datetime.now(timezone.utc)
    matches = []
    for i in range(8):
        matches.append(
            {
                "team1_id": team_ids[i * 2],
                "team2_id": team_ids[i * 2 + 1],
                "date_time": (now + timedelta(days=30 + i)).isoformat(),
            }
        )
    deadline = (now + timedelta(days=28)).isoformat()
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/admin/rounds"),
        headers=h,
        json={"number": 99, "deadline": deadline, "matches": matches},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DRAFT"
    assert len(matches) == 8


@pytest.mark.asyncio
async def test_op_rounds_list(loaded_api):
    """[OP-ROUNDS-LIST] GET rounds public → includes round numbers."""
    client, sf, _ = loaded_api
    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, "/rounds"))
    assert resp.status_code == 200
    numbers = {r["number"] for r in resp.json()}
    assert 1 in numbers
    assert 10 in numbers


@pytest.mark.asyncio
async def test_op_recalc(loaded_api):
    """[OP-RECALC] POST admin/recalculate as ADMIN → 200; USER → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    user = await api_login(client, "shutov")

    ok = await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/admin/recalculate"),
        headers=auth_header(admin),
    )
    assert ok.status_code == 200

    denied = await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/admin/recalculate"),
        headers=auth_header(user),
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_setup_part_auth(empty_api):
    """[SETUP-PART-AUTH] invite → login → change-password → predictions OK."""
    client, sf, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Auth Flow", "total_teams": 16},
    )
    cid = created.json()["id"]

    from tests.api.conftest import _load_teams_csv

    teams = _load_teams_csv()[:16]
    tids = []
    for row in teams:
        t = await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )
        tids.append(t.json()["id"])

    invite = await client.post(
        contest_url(cid, "/participants"),
        headers=h,
        json={
            "email": "player@example.com",
            "first_name": "Play",
            "last_name": "Er",
            "login": "player_auth",
        },
    )
    data = invite.json()
    temp_pw = data["temp_password"]
    login = data["login"]

    token = await api_login(client, login, temp_pw)
    change = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(token),
        json={"old_password": temp_pw, "new_password": TEST_PASSWORD},
    )
    assert change.status_code == 200

    now = datetime.now(timezone.utc)
    matches = []
    for i in range(8):
        match_at = now + timedelta(days=30 + i)
        matches.append(
            {
                "team1_id": tids[i * 2],
                "team2_id": tids[i * 2 + 1],
                "date_time": match_at.isoformat(),
            }
        )
    earliest = now + timedelta(days=30)
    deadline = (earliest - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(cid, "/admin/rounds"),
        headers=h,
        json={"number": 1, "deadline": deadline, "matches": matches},
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    await client.post(contest_url(cid, f"/admin/rounds/{rid}/activate"), headers=h)

    user_token = await api_login(client, login)
    async with sf() as session:
        db_matches = (
            await session.scalars(select(Match).where(Match.round_id == rid).order_by(Match.id))
        ).all()
        mids = [m.id for m in db_matches]

    pred = await client.post(
        contest_url(cid, f"/rounds/{rid}/predictions"),
        headers=auth_header(user_token),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 0} for m in mids]},
    )
    assert pred.status_code == 200
