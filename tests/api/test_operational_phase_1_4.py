"""[OP-*] Stage 1.4 operational phase — contest-scoped HTTP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from database.models import ContestLifecycleStatus, Match, Round, RoundStatus, User
from tests.api.conftest import (
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
async def test_op_activate_locks_contest(loaded_api):
    """[OP-ACTIVATE] first activate → is_locked=true, RUNNING."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    detail = await client.get(
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=auth_header(sup),
    )
    assert detail.status_code == 200
    data = detail.json()
    assert data["is_locked"] is True
    assert data["status"] == ContestLifecycleStatus.RUNNING.value


@pytest.mark.asyncio
async def test_op_pred_full_batch(loaded_api):
    """[OP-PRED] batch predictions ACTIVE round before deadline → 200."""
    client, sf, _ = loaded_api
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 200
    assert resp.json()["saved_count"] == 8


@pytest.mark.asyncio
async def test_op_pred_partial_rejected(loaded_api):
    """[OP-PRED] partial batch → 400."""
    client, sf, _ = loaded_api
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={
            "predictions": [
                {"match_id": m, "score1": 1, "score2": 0} for m in mids[:7]
            ]
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_op_pred_deadline(loaded_api):
    """[OP-PRED-DEADLINE] after deadline → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user = await api_login(client, "volchenko")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)

    async with sf() as session:
        async with session.begin():
            from database.models import Round

            round_ = await session.get(Round, rid)
            round_.deadline = datetime.now(timezone.utc) - timedelta(hours=1)

    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_op_autoclose(loaded_api):
    """[OP-AUTOCLOSE] ACTIVE round past deadline → CLOSED after committing request."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    async with sf() as session:
        async with session.begin():
            round_ = await session.scalar(
                select(Round).where(
                    Round.contest_id == DEFAULT_CONTEST_ID, Round.number == 10
                )
            )
            round_.deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
            round_.status = RoundStatus.ACTIVE.value
            rid = round_.id

    # Auto-close runs in ContestContext; needs a committing route to persist.
    r1 = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    calc = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{r1}/calculate"),
        headers=h,
    )
    assert calc.status_code == 200, calc.text

    async with sf() as session:
        round_after = await session.get(Round, rid)
        assert round_after.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_op_close_after_deadline(loaded_api):
    """[OP-CLOSE] POST close when deadline passed → CLOSED."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    async with sf() as session:
        async with session.begin():
            round_ = await session.scalar(
                select(Round).where(
                    Round.contest_id == DEFAULT_CONTEST_ID, Round.number == 10
                )
            )
            round_.deadline = datetime.now(timezone.utc) - timedelta(hours=1)
            round_.status = RoundStatus.ACTIVE.value
            rid = round_.id

    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/close"),
        headers=h,
    )
    assert resp.status_code == 200, resp.text

    async with sf() as session:
        round_after = await session.get(Round, rid)
        assert round_after.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_op_close_early(loaded_api):
    """[OP-CLOSE-EARLY] close before deadline → 400."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/close"),
        headers=auth_header(sup),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_op_result_guard(loaded_api):
    """[OP-RESULT-GUARD] PUT result before deadline → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    async with sf() as session:
        match = await session.scalar(
            select(Match).where(Match.round_id == rid).limit(1)
        )
        mid = match.id

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=auth_header(sup),
        json={"score1": 1, "score2": 0},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_op_result_ok(loaded_api):
    """[OP-RESULT-OK] after close + deadline → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(
                Match.round_id == rid, Match.status == "FINISHED"
            ).limit(1)
        )
        mid = match.id

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": match.score1, "score2": match.score2},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_op_calc_closed(loaded_api):
    """[OP-CALC] calculate CLOSED round → CALCULATED."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=auth_header(sup),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == RoundStatus.CALCULATED.value


@pytest.mark.asyncio
async def test_op_calc_active_rejected(loaded_api):
    """[OP-CALC-ACTIVE] calculate on ACTIVE → 400."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=auth_header(sup),
    )
    assert resp.status_code in (400, 403)


@pytest.mark.asyncio
async def test_op_publish(loaded_api):
    """[OP-PUBLISH] CALCULATED → PUBLISHED."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == RoundStatus.PUBLISHED.value


@pytest.mark.asyncio
async def test_op_void_recalc(loaded_api):
    """[OP-VOID] VOID → recalc; leaderboard updated."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    before = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    total_before = sum(r["total_with_bonus3"] for r in before.json()["leaderboard"])

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(Match.round_id == rid, Match.status == "FINISHED").limit(1)
        )
        mid = match.id

    await client.patch(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/status"),
        headers=h,
        json={"status": "VOID"},
    )
    after = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    total_after = sum(r["total_with_bonus3"] for r in after.json()["leaderboard"])
    assert total_after <= total_before


@pytest.mark.asyncio
async def test_op_pause_resume(loaded_api):
    """[OP-PAUSE] pause blocks predictions; resume restores."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    user = await api_login(client, "shutov")
    h_admin = auth_header(admin)
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)

    await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=h_admin)
    blocked = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert blocked.status_code == 403

    await client.post(contest_url(DEFAULT_CONTEST_ID, "/resume"), headers=h_admin)
    ok = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 1} for m in mids]},
    )
    assert ok.status_code == 200
