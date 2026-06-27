"""Stage 2.3.2 — edit match result on CALCULATED tour ([API-RESULT-CALCULATED])."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Match, MatchStatus, Round, RoundStatus, Score
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round_id,
)


@pytest.mark.asyncio
async def test_api_result_closed_put(loaded_api):
    """[API-RESULT-CALCULATED] CLOSED round → PUT result → 200, FINISHED."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 9, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        assert round_.status == RoundStatus.CLOSED.value
        match = await session.scalar(
            select(Match).where(
                Match.round_id == rid, Match.status == MatchStatus.FINISHED
            ).limit(1)
        )
        assert match is not None
        mid = match.id

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": 2, "score2": 1},
    )
    assert resp.status_code == 200

    async with sf() as session:
        updated = await session.get(Match, mid)
        assert updated is not None
        assert updated.status == MatchStatus.FINISHED.value
        assert updated.score1 == 2
        assert updated.score2 == 1


@pytest.mark.asyncio
async def test_api_result_calculated_recalc(loaded_api):
    """[API-RESULT-CALCULATED] CALCULATED → PUT changed scores → scores + staff LB update."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)

    calc = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    assert calc.status_code == 200
    assert calc.json()["status"] == RoundStatus.CALCULATED.value

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(
                Match.round_id == rid, Match.status == MatchStatus.FINISHED
            ).limit(1)
        )
        assert match is not None
        mid = match.id
        scores_before = {
            s.user_id: s.total_with_bonus3
            for s in (await session.scalars(select(Score).where(Score.round_id == rid))).all()
        }

    lb_before = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"),
        headers=h,
    )
    assert lb_before.status_code == 200
    lb_map_before = {
        row["user_id"]: row["total_with_bonus3"]
        for row in lb_before.json()["leaderboard"]
    }

    new_score1, new_score2 = 5, 0
    if match.score1 == new_score1 and match.score2 == new_score2:
        new_score1, new_score2 = 0, 5

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": new_score1, "score2": new_score2},
    )
    assert resp.status_code == 200

    async with sf() as session:
        updated = await session.get(Match, mid)
        assert updated is not None
        assert updated.score1 == new_score1
        assert updated.score2 == new_score2
        scores_after = {
            s.user_id: s.total_with_bonus3
            for s in (await session.scalars(select(Score).where(Score.round_id == rid))).all()
        }

    assert scores_before != scores_after, "scores table should reflect recalculation"

    lb_after = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"),
        headers=h,
    )
    assert lb_after.status_code == 200
    lb_map_after = {
        row["user_id"]: row["total_with_bonus3"]
        for row in lb_after.json()["leaderboard"]
    }
    assert lb_map_before != lb_map_after, "staff LB preview should reflect score change"


@pytest.mark.asyncio
async def test_api_result_published_rejected(loaded_api):
    """[API-RESULT-CALCULATED] PUBLISHED → PUT result → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 2, DEFAULT_CONTEST_ID)

    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    pub = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=h,
    )
    assert pub.status_code == 200
    assert pub.json()["status"] == RoundStatus.PUBLISHED.value

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(
                Match.round_id == rid, Match.status == MatchStatus.FINISHED
            ).limit(1)
        )
        assert match is not None
        mid = match.id

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": 1, "score2": 0},
    )
    assert resp.status_code == 403
    assert resp.json().get("code") == "ROUND_NOT_CLOSED"


@pytest.mark.asyncio
async def test_api_result_calculated_then_publish(loaded_api):
    """[API-RESULT-CALCULATED] CALCULATED → PUT → publish still works → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 3, DEFAULT_CONTEST_ID)

    calc = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    assert calc.status_code == 200

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(
                Match.round_id == rid, Match.status == MatchStatus.FINISHED
            ).limit(1)
        )
        assert match is not None
        mid = match.id

    put = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": 3, "score2": 2},
    )
    assert put.status_code == 200

    pub = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=h,
    )
    assert pub.status_code == 200
    assert pub.json()["status"] == RoundStatus.PUBLISHED.value
