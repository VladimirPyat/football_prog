"""Stage 1.7 — invite accept on password change and prediction guard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from database.models import Match
from tests.api.conftest import (
    API_PREFIX,
    TEST_PASSWORD,
    api_login,
    auth_header,
    contest_url,
)


async def _setup_contest_with_invite(client):
    """Create contest, teams, and invited participant; return context dict."""
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Accept Flow", "total_teams": 16},
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
            "email": "accept@example.com",
            "first_name": "Accept",
            "last_name": "User",
            "login": "accept_user",
        },
    )
    data = invite.json()
    return {
        "client": client,
        "cid": cid,
        "sup_headers": h,
        "tids": tids,
        "login": data["login"],
        "temp_password": data["temp_password"],
        "user_id": data["user_id"],
    }


@pytest.mark.asyncio
async def test_accept_invite(empty_api):
    """[ACCEPT-INVITE] change-password flips participant status to ACCEPTED."""
    client, _, _ = empty_api
    ctx = await _setup_contest_with_invite(client)

    token = await api_login(client, ctx["login"], ctx["temp_password"])
    change = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(token),
        json={"old_password": ctx["temp_password"], "new_password": TEST_PASSWORD},
    )
    assert change.status_code == 200

    parts = await client.get(
        contest_url(ctx["cid"], "/participants"),
        headers=ctx["sup_headers"],
    )
    assert parts.status_code == 200
    invited = next(p for p in parts.json() if p["user_id"] == ctx["user_id"])
    assert invited["status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_accept_pred_guard(empty_api):
    """[ACCEPT-PRED-GUARD] PENDING invitee cannot submit predictions before accept."""
    client, sf, _ = empty_api
    ctx = await _setup_contest_with_invite(client)
    token = await api_login(client, ctx["login"], ctx["temp_password"])

    now = datetime.now(timezone.utc)
    matches = []
    for i in range(8):
        match_at = now + timedelta(days=30 + i)
        matches.append(
            {
                "team1_id": ctx["tids"][i * 2],
                "team2_id": ctx["tids"][i * 2 + 1],
                "date_time": match_at.isoformat(),
            }
        )
    earliest = now + timedelta(days=30)
    deadline = (earliest - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(ctx["cid"], "/admin/rounds"),
        headers=ctx["sup_headers"],
        json={"number": 1, "deadline": deadline, "matches": matches},
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    await client.post(
        contest_url(ctx["cid"], f"/admin/rounds/{rid}/activate"),
        headers=ctx["sup_headers"],
    )

    async with sf() as session:
        db_matches = (
            await session.scalars(select(Match).where(Match.round_id == rid).order_by(Match.id))
        ).all()
        mids = [m.id for m in db_matches]

    pred = await client.post(
        contest_url(ctx["cid"], f"/rounds/{rid}/predictions"),
        headers=auth_header(token),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 0} for m in mids]},
    )
    assert pred.status_code == 403
    assert pred.json()["code"] == "PARTICIPANT_NOT_ACCEPTED"


@pytest.mark.asyncio
async def test_accept_reg_predictions(empty_api):
    """[ACCEPT-REG] After change-password, predictions still succeed."""
    client, sf, _ = empty_api
    ctx = await _setup_contest_with_invite(client)

    token = await api_login(client, ctx["login"], ctx["temp_password"])
    change = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(token),
        json={"old_password": ctx["temp_password"], "new_password": TEST_PASSWORD},
    )
    assert change.status_code == 200

    now = datetime.now(timezone.utc)
    matches = []
    for i in range(8):
        match_at = now + timedelta(days=30 + i)
        matches.append(
            {
                "team1_id": ctx["tids"][i * 2],
                "team2_id": ctx["tids"][i * 2 + 1],
                "date_time": match_at.isoformat(),
            }
        )
    earliest = now + timedelta(days=30)
    deadline = (earliest - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(ctx["cid"], "/admin/rounds"),
        headers=ctx["sup_headers"],
        json={"number": 1, "deadline": deadline, "matches": matches},
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    await client.post(
        contest_url(ctx["cid"], f"/admin/rounds/{rid}/activate"),
        headers=ctx["sup_headers"],
    )

    user_token = await api_login(client, ctx["login"])
    async with sf() as session:
        db_matches = (
            await session.scalars(select(Match).where(Match.round_id == rid).order_by(Match.id))
        ).all()
        mids = [m.id for m in db_matches]

    pred = await client.post(
        contest_url(ctx["cid"], f"/rounds/{rid}/predictions"),
        headers=auth_header(user_token),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 0} for m in mids]},
    )
    assert pred.status_code == 200


@pytest.mark.asyncio
async def test_accept_me_contests(empty_api):
    """[ACCEPT-ME-CONTESTS] After change-password, /me/contests shows ACCEPTED."""
    client, _, _ = empty_api
    ctx = await _setup_contest_with_invite(client)

    token = await api_login(client, ctx["login"], ctx["temp_password"])
    change = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(token),
        json={"old_password": ctx["temp_password"], "new_password": TEST_PASSWORD},
    )
    assert change.status_code == 200

    user_token = await api_login(client, ctx["login"])
    resp = await client.get(f"{API_PREFIX}/me/contests", headers=auth_header(user_token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == ctx["cid"]
    assert body[0]["participant_status"] == "ACCEPTED"
