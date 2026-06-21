"""Unit tests for Stage 1.4 multi-contest isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import ContestParticipant, ParticipantStatus, Round, RoundStatus, Team, User, UserRole
from services.contest_lifecycle_service import update_exceptional_tiebreak
from services.contest_setup_service import create_contest, create_team


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
async def test_two_contests_isolated_teams_and_rounds(session: AsyncSession) -> None:
    c1 = await create_contest(session, "Contest One")
    c2 = await create_contest(session, "Contest Two")
    await create_team(session, c1.id, "Alpha", "A")
    await create_team(session, c2.id, "Beta", "B")

    r1 = Round(
        contest_id=c1.id,
        number=1,
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        status=RoundStatus.DRAFT,
        matches_count=0,
    )
    r2 = Round(
        contest_id=c2.id,
        number=1,
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        status=RoundStatus.DRAFT,
        matches_count=0,
    )
    session.add_all([r1, r2])
    await session.commit()

    c1_teams = (await session.scalars(select(Team).where(Team.contest_id == c1.id))).all()
    c2_teams = (await session.scalars(select(Team).where(Team.contest_id == c2.id))).all()
    assert len(c1_teams) == 1
    assert len(c2_teams) == 1
    assert c1_teams[0].name == "Alpha"
    assert c2_teams[0].name == "Beta"

    c1_rounds = (await session.scalars(select(Round).where(Round.contest_id == c1.id))).all()
    c2_rounds = (await session.scalars(select(Round).where(Round.contest_id == c2.id))).all()
    assert len(c1_rounds) == 1
    assert len(c2_rounds) == 1
    assert c1_rounds[0].id != c2_rounds[0].id


@pytest.mark.asyncio
async def test_same_user_different_exceptional_points_per_contest(session: AsyncSession) -> None:
    c1 = await create_contest(session, "C1")
    c2 = await create_contest(session, "C2")
    user = User(
        login="shared",
        password_hash="h",
        role=UserRole.USER,
        first_name="Shared",
        last_name="User",
        is_temp_password=False,
    )
    session.add(user)
    await session.flush()
    session.add_all(
        [
            ContestParticipant(
                contest_id=c1.id,
                user_id=user.id,
                status=ParticipantStatus.ACCEPTED,
            ),
            ContestParticipant(
                contest_id=c2.id,
                user_id=user.id,
                status=ParticipantStatus.ACCEPTED,
            ),
        ]
    )
    await session.commit()

    await update_exceptional_tiebreak(session, c1.id, user.id, 3)
    await update_exceptional_tiebreak(session, c2.id, user.id, 7)
    await session.commit()

    p1 = await session.get(ContestParticipant, (c1.id, user.id))
    p2 = await session.get(ContestParticipant, (c2.id, user.id))
    assert p1 is not None and p1.exceptional_tiebreak_points == 3
    assert p2 is not None and p2.exceptional_tiebreak_points == 7
