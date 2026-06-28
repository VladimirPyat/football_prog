"""Tests for postponed-match bonus pending detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import Match, MatchStatus, Round, RoundStatus
from services.contest_setup_service import create_contest, create_team
from services.round_scoring_pending import origin_round_bonuses_pending


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


async def _add_match(
    session: AsyncSession,
    *,
    round_id: int,
    team1_id: int,
    team2_id: int,
    status: MatchStatus,
    origin_round_id: int | None = None,
) -> None:
    session.add(
        Match(
            round_id=round_id,
            origin_round_id=origin_round_id,
            team1_id=team1_id,
            team2_id=team2_id,
            date_time=datetime.now(UTC) + timedelta(days=1),
            status=status.value,
            score1=1 if status == MatchStatus.FINISHED else None,
            score2=0 if status == MatchStatus.FINISHED else None,
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_bonuses_pending_when_postponed_in_origin(session: AsyncSession) -> None:
    contest = await create_contest(session, "Pending Origin")
    t1 = await create_team(session, contest.id, "A", "A")
    t2 = await create_team(session, contest.id, "B", "B")
    t3 = await create_team(session, contest.id, "C", "C")
    t4 = await create_team(session, contest.id, "D", "D")
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=datetime.now(UTC) + timedelta(days=7),
        status=RoundStatus.CLOSED,
        matches_count=2,
    )
    session.add(round_)
    await session.flush()

    await _add_match(
        session, round_id=round_.id, team1_id=t1.id, team2_id=t2.id, status=MatchStatus.FINISHED
    )
    await _add_match(
        session, round_id=round_.id, team1_id=t3.id, team2_id=t4.id, status=MatchStatus.POSTPONED
    )

    pending, message = await origin_round_bonuses_pending(session, round_.id)
    assert pending is True
    assert message is not None


@pytest.mark.asyncio
async def test_bonuses_not_pending_when_canceled_only(session: AsyncSession) -> None:
    contest = await create_contest(session, "Canceled Only")
    t1 = await create_team(session, contest.id, "A", "A")
    t2 = await create_team(session, contest.id, "B", "B")
    t3 = await create_team(session, contest.id, "C", "C")
    t4 = await create_team(session, contest.id, "D", "D")
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=datetime.now(UTC) + timedelta(days=7),
        status=RoundStatus.CALCULATED,
        matches_count=2,
    )
    session.add(round_)
    await session.flush()

    await _add_match(
        session, round_id=round_.id, team1_id=t1.id, team2_id=t2.id, status=MatchStatus.FINISHED
    )
    await _add_match(
        session, round_id=round_.id, team1_id=t3.id, team2_id=t4.id, status=MatchStatus.CANCELED
    )

    pending, _ = await origin_round_bonuses_pending(session, round_.id)
    assert pending is False


@pytest.mark.asyncio
async def test_bonuses_pending_for_moved_match_in_supplementary(session: AsyncSession) -> None:
    contest = await create_contest(session, "Supplementary")
    t1 = await create_team(session, contest.id, "A", "A")
    t2 = await create_team(session, contest.id, "B", "B")
    t3 = await create_team(session, contest.id, "C", "C")
    t4 = await create_team(session, contest.id, "D", "D")
    origin = Round(
        contest_id=contest.id,
        number=1,
        deadline=datetime.now(UTC) + timedelta(days=7),
        status=RoundStatus.CALCULATED,
        matches_count=2,
    )
    supplementary = Round(
        contest_id=contest.id,
        number=2,
        deadline=datetime.now(UTC) + timedelta(days=14),
        status=RoundStatus.DRAFT,
        matches_count=1,
        kind="SUPPLEMENTARY",
        supplementary_index=1,
    )
    session.add(origin)
    session.add(supplementary)
    await session.flush()

    await _add_match(
        session, round_id=origin.id, team1_id=t1.id, team2_id=t2.id, status=MatchStatus.FINISHED
    )
    await _add_match(
        session,
        round_id=supplementary.id,
        origin_round_id=origin.id,
        team1_id=t3.id,
        team2_id=t4.id,
        status=MatchStatus.SCHEDULED,
    )

    pending, _ = await origin_round_bonuses_pending(session, origin.id)
    assert pending is True
