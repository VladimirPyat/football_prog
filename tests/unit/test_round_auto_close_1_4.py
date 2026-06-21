"""Unit tests for Stage 1.4 round auto-close and result guard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import ContestLifecycleStatus, Match, MatchStatus, Round, RoundStatus, Team
from services.contest_setup_service import create_contest, create_team
from services.match_service import set_result
from services.round_auto_close_service import auto_close_expired_rounds
from services.round_service import close_round


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.mark.asyncio
async def test_auto_close_expired_active_round(session: AsyncSession) -> None:
    contest = await create_contest(session, "Auto Close")
    contest.status = ContestLifecycleStatus.RUNNING
    t1 = await create_team(session, contest.id, "T1", "T1")
    t2 = await create_team(session, contest.id, "T2", "T2")
    past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=past_deadline,
        status=RoundStatus.ACTIVE,
        matches_count=1,
    )
    session.add(round_)
    await session.flush()
    session.add(
        Match(
            round_id=round_.id,
            team1_id=t1.id,
            team2_id=t2.id,
            date_time=past_deadline + timedelta(hours=2),
            status=MatchStatus.SCHEDULED,
        )
    )
    await session.commit()

    closed = await auto_close_expired_rounds(session, contest.id)
    await session.commit()
    assert closed == [round_.id]

    refreshed = await session.get(Round, round_.id)
    assert refreshed is not None
    assert refreshed.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_result_rejected_before_deadline_allowed_after_close(session: AsyncSession) -> None:
    contest = await create_contest(session, "Result Guard")
    contest.status = ContestLifecycleStatus.RUNNING
    t1 = await create_team(session, contest.id, "T1", "T1")
    t2 = await create_team(session, contest.id, "T2", "T2")
    past_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=past_deadline,
        status=RoundStatus.ACTIVE,
        matches_count=1,
    )
    session.add(round_)
    await session.flush()
    match = Match(
        round_id=round_.id,
        team1_id=t1.id,
        team2_id=t2.id,
        date_time=past_deadline + timedelta(hours=1),
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    await session.commit()

    future_round = Round(
        contest_id=contest.id,
        number=2,
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        status=RoundStatus.ACTIVE,
        matches_count=1,
    )
    session.add(future_round)
    await session.flush()
    future_match = Match(
        round_id=future_round.id,
        team1_id=t1.id,
        team2_id=t2.id,
        date_time=datetime.now(timezone.utc) + timedelta(days=2),
        status=MatchStatus.SCHEDULED,
    )
    session.add(future_match)
    await session.commit()

    with pytest.raises(ValueError, match="deadline"):
        await set_result(session, contest.id, future_match.id, 1, 0)

    await close_round(session, contest.id, round_.id)
    await session.commit()

    updated = await set_result(session, contest.id, match.id, 2, 1)
    assert updated.status == MatchStatus.FINISHED
