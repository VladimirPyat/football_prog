"""Unit tests for Stage 1.4 contest setup service."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import Contest, ContestLifecycleStatus, Team, User
from core.exceptions import ContestLockedError, ValidationError
from services.contest_setup_service import (
    add_participant,
    create_contest,
    create_team,
    list_participants,
    list_teams,
    update_contest,
    validate_contest_structure,
)
from services.round_service import transition_round
from database.models import Round, RoundStatus
from datetime import datetime, timedelta, timezone
from services.contest_lifecycle_service import ensure_running_on_first_activation


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
async def test_create_contest_draft_and_patch_rules(session: AsyncSession) -> None:
    contest = await create_contest(session, "Cup 2026", rules_from_defaults=True)
    await session.commit()
    assert contest.status == ContestLifecycleStatus.DRAFT
    assert contest.is_locked is False

    patched = await update_contest(
        session,
        contest.id,
        {
            "total_teams": 20,
            "matches_per_round": 10,
            "total_rounds": 38,
            "rules_json": contest.rules_json,
        },
    )
    await session.commit()
    assert patched.total_teams == 20


@pytest.mark.asyncio
async def test_create_teams_and_participants(session: AsyncSession) -> None:
    contest = await create_contest(session, "Setup Test")
    await session.flush()

    for i in range(16):
        await create_team(session, contest.id, f"Team {i}", f"T{i}")
    teams = await list_teams(session, contest.id)
    assert len(teams) == 16

    for i in range(10):
        invite = await add_participant(
            session,
            contest.id,
            email=f"user{i}@example.com",
            first_name=f"First{i}",
            last_name=f"Last{i}",
        )
        assert invite["temp_password"]
        user = await session.get(User, invite["user_id"])
        assert user is not None
        assert user.is_temp_password is True

    participants = await list_participants(session, contest.id)
    assert len(participants) == 10


@pytest.mark.asyncio
async def test_locked_contest_blocks_setup_mutations(session: AsyncSession) -> None:
    contest = await create_contest(session, "Lock Test")
    await create_team(session, contest.id, "A", "A")
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        status=RoundStatus.DRAFT,
        matches_count=0,
    )
    session.add(round_)
    await session.flush()
    await transition_round(session, round_.id, RoundStatus.ACTIVE)
    await ensure_running_on_first_activation(session, contest.id)
    await session.commit()

    with pytest.raises(ContestLockedError):
        await update_contest(session, contest.id, {"name": "Nope"})
    with pytest.raises(ContestLockedError):
        await create_team(session, contest.id, "Extra", "E")


def test_validate_contest_structure_round_robin_odd_teams() -> None:
    with pytest.raises(ValidationError, match="чётное"):
        validate_contest_structure(
            total_teams=15,
            matches_per_round=7,
            total_rounds=28,
            is_round_robin=True,
        )


def test_validate_contest_structure_round_robin_valid() -> None:
    validate_contest_structure(
        total_teams=16,
        matches_per_round=8,
        total_rounds=30,
        is_round_robin=True,
    )


def test_validate_contest_structure_arbitrary_odd_teams() -> None:
    validate_contest_structure(
        total_teams=15,
        matches_per_round=7,
        total_rounds=10,
        is_round_robin=False,
    )


@pytest.mark.asyncio
async def test_update_contest_rejects_odd_round_robin(session: AsyncSession) -> None:
    contest = await create_contest(session, "Odd RR")
    await session.flush()

    with pytest.raises(ValidationError, match="чётное"):
        await update_contest(
            session,
            contest.id,
            {
                "total_teams": 15,
                "matches_per_round": 7,
                "total_rounds": 28,
                "is_round_robin": True,
            },
        )
