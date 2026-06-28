"""Stage 1.16 — per-round deadline auto-close."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import ContestLifecycleStatus, Match, MatchStatus, Round, RoundStatus, Team
from services.contest_setup_service import create_contest, create_team
from services.match_service import set_result
from services.prediction_service import submit_batch, visible_predictions
from services.round_auto_close_service import ensure_round_closed_if_expired
from services.scoring_persistence import calculate_round
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


@pytest_asyncio.fixture
async def unit_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


async def _seed_active_round(
    session: AsyncSession,
    *,
    deadline: datetime,
    status: RoundStatus = RoundStatus.ACTIVE,
) -> tuple[int, int, int]:
    contest = await create_contest(session, "Ensure Close")
    contest.status = ContestLifecycleStatus.RUNNING
    t1 = await create_team(session, contest.id, "T1", "T1")
    t2 = await create_team(session, contest.id, "T2", "T2")
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=deadline,
        status=status,
        matches_count=1,
    )
    session.add(round_)
    await session.flush()
    match = Match(
        round_id=round_.id,
        team1_id=t1.id,
        team2_id=t2.id,
        date_time=deadline + timedelta(hours=2),
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    await session.commit()
    return contest.id, round_.id, match.id


@pytest.mark.asyncio
async def test_ensure_close(unit_session: AsyncSession) -> None:
    """[ENSURE-CLOSE] ACTIVE, deadline 1h ago → ensure → CLOSED."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    _, round_id, _ = await _seed_active_round(unit_session, deadline=past)

    refreshed = await ensure_round_closed_if_expired(unit_session, round_id)
    await unit_session.commit()

    assert refreshed.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_ensure_idempotent(unit_session: AsyncSession) -> None:
    """[ENSURE-IDEM] Already CLOSED → no-op."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    _, round_id, _ = await _seed_active_round(
        unit_session, deadline=past, status=RoundStatus.CLOSED
    )

    refreshed = await ensure_round_closed_if_expired(unit_session, round_id)
    assert refreshed.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_ensure_future_deadline(unit_session: AsyncSession) -> None:
    """[ENSURE-FUTURE] ACTIVE, deadline +1h → unchanged."""
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    _, round_id, _ = await _seed_active_round(unit_session, deadline=future)

    refreshed = await ensure_round_closed_if_expired(unit_session, round_id)
    assert refreshed.status == RoundStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_result_auto_close(unit_session: AsyncSession) -> None:
    """[RESULT-AUTO-CLOSE] ACTIVE + past deadline → set_result succeeds inline."""
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    contest_id, _, match_id = await _seed_active_round(unit_session, deadline=past)

    updated = await set_result(unit_session, contest_id, match_id, 2, 1)
    await unit_session.commit()

    assert updated.status == MatchStatus.FINISHED
    round_ = await unit_session.get(Round, updated.round_id)
    assert round_ is not None
    assert round_.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_predict_block_after_deadline(unit_session: AsyncSession) -> None:
    """[PREDICT-BLOCK] After deadline → submit_batch rejected."""
    from core.exceptions import ContestRuleError

    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    contest_id, round_id, match_id = await _seed_active_round(unit_session, deadline=past)

    with pytest.raises(ContestRuleError):
        await submit_batch(
            unit_session,
            contest_id,
            user_id=1,
            round_id=round_id,
            items=[(match_id, 1, 0)],
        )


@pytest.mark.asyncio
async def test_predict_view_after_deadline(unit_session: AsyncSession) -> None:
    """[PREDICT-VIEW] After deadline → visible_predictions full table."""
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    contest_id, round_id, match_id = await _seed_active_round(unit_session, deadline=past)

    from database.models import Prediction, User, UserRole

    user = User(
        id=99,
        login="viewer",
        password_hash="x",
        first_name="V",
        last_name="U",
        role=UserRole.USER,
    )
    unit_session.add(user)
    unit_session.add(
        Prediction(
            user_id=99,
            round_id=round_id,
            match_id=match_id,
            score1=1,
            score2=0,
        )
    )
    await unit_session.commit()

    rows = await visible_predictions(
        unit_session, contest_id, round_id, UserRole.USER.value, viewer_id=98
    )
    assert len(rows) == 1
    assert rows[0]["match_id"] == match_id
    assert rows[0]["score1"] == 1


@pytest.mark.asyncio
async def test_shim_predict_after_deadline(loaded_api) -> None:
    """[SHIM-PREDICT] Legacy POST /rounds/{id}/predictions after deadline → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user = await api_login(client, "volchenko")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)

    async with sf() as session:
        async with session.begin():
            round_ = await session.get(Round, rid)
            round_.deadline = datetime.now(timezone.utc) - timedelta(hours=1)
            round_.status = RoundStatus.ACTIVE.value

    resp = await client.post(
        f"/api/v1/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_calc_after_deadline(unit_session: AsyncSession) -> None:
    """[CALC-AFTER-DEADLINE] ACTIVE + past deadline → calculate_round → CALCULATED."""
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    contest_id, round_id, match_id = await _seed_active_round(unit_session, deadline=past)

    await set_result(unit_session, contest_id, match_id, 1, 0)
    await unit_session.commit()

    count = await calculate_round(unit_session, round_id, contest_id)
    await unit_session.commit()

    assert count >= 0
    round_ = await unit_session.get(Round, round_id)
    assert round_ is not None
    assert round_.status == RoundStatus.CALCULATED.value


@pytest.mark.asyncio
async def test_result_auto_close_api(loaded_api) -> None:
    """[RESULT-AUTO-CLOSE] HTTP PUT result after deadline without manual close."""
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
            match = await session.scalar(
                select(Match).where(Match.round_id == rid).limit(1)
            )
            mid = match.id

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": 1, "score2": 0},
    )
    assert resp.status_code == 200, resp.text

    async with sf() as session:
        round_after = await session.get(Round, rid)
        assert round_after.status == RoundStatus.CLOSED.value
