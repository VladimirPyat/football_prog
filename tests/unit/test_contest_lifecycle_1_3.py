"""Unit tests for Stage 1.3 contest lifecycle service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import Settings, get_settings
from database.base import Base
from database.models import ContestLifecycleStatus, ContestSettings, Round, RoundStatus, User, UserRole
from services.contest_lifecycle_service import (
    ContestLockedError,
    GracePeriodError,
    IllegalTransitionError,
    assert_contest_running,
    assert_deletable,
    delete_contest_data,
    finish_contest,
    pause_contest,
    require_unlocked,
    resume_contest,
    update_exceptional_tiebreak,
)

TEST_RULES = {
    "scoring_rules": {"base_points": {}, "bonuses": {}},
    "tiebreakers": {},
    "constraints": {"score_validation_range": [0, 20]},
    "contest_structure": {"deadline_rule_hours": 24},
}


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        settings = ContestSettings(
            is_locked=False,
            status=ContestLifecycleStatus.DRAFT,
            total_teams=16,
            matches_per_round=8,
            total_rounds=30,
            is_round_robin=True,
            rules_json=TEST_RULES,
        )
        sess.add(settings)
        await sess.commit()
        yield sess

    await engine.dispose()


@pytest.mark.asyncio
async def test_require_unlocked_when_locked(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.is_locked = True
    await session.commit()

    with pytest.raises(ContestLockedError):
        await require_unlocked(session)


@pytest.mark.asyncio
async def test_require_unlocked_when_unlocked(session: AsyncSession) -> None:
    result = await require_unlocked(session)
    assert result.is_locked is False


@pytest.mark.asyncio
async def test_assert_contest_running_blocks_paused(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.status = ContestLifecycleStatus.PAUSED
    await session.commit()

    with pytest.raises(PermissionError):
        await assert_contest_running(session)


@pytest.mark.asyncio
async def test_pause_resume_happy_path(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.status = ContestLifecycleStatus.RUNNING
    await session.commit()

    paused = await pause_contest(session)
    assert paused.status == ContestLifecycleStatus.PAUSED
    assert paused.paused_at is not None

    resumed = await resume_contest(session)
    assert resumed.status == ContestLifecycleStatus.RUNNING
    assert resumed.paused_at is None


@pytest.mark.asyncio
async def test_illegal_draft_to_finish(session: AsyncSession) -> None:
    with pytest.raises(IllegalTransitionError):
        await finish_contest(session)


@pytest.mark.asyncio
async def test_finish_from_running(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.status = ContestLifecycleStatus.RUNNING
    round_ = Round(
        number=1,
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        status=RoundStatus.ACTIVE,
        matches_count=8,
    )
    session.add(round_)
    await session.flush()
    round_id = round_.id
    await session.commit()

    finished = await finish_contest(session)
    assert finished.status == ContestLifecycleStatus.FINISHED
    assert finished.finished_at is not None
    await session.commit()

    round_in_db = await session.get(Round, round_id)
    assert round_in_db is not None
    assert round_in_db.status == RoundStatus.CLOSED.value


@pytest.mark.asyncio
async def test_finish_idempotent(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.status = ContestLifecycleStatus.FINISHED
    settings.finished_at = datetime.now(timezone.utc)
    await session.commit()

    result = await finish_contest(session)
    assert result.status == ContestLifecycleStatus.FINISHED


@pytest.mark.asyncio
async def test_delete_wrong_confirm_rejected_by_api_layer() -> None:
    with pytest.raises(Exception):
        from schemas.contest import ContestDeleteConfirmRequest  # noqa: PLC0415

        ContestDeleteConfirmRequest(confirm="NOPE")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_delete_grace_period(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.status = ContestLifecycleStatus.PAUSED
    settings.paused_at = datetime.now(timezone.utc)
    await session.commit()

    test_settings = Settings(contest_allow_instant_delete=False, contest_delete_grace_seconds=3600)
    with patch("services.contest_lifecycle_service.get_settings", return_value=test_settings):
        with pytest.raises(GracePeriodError):
            await assert_deletable(session)


@pytest.mark.asyncio
async def test_delete_instant_allowed(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.status = ContestLifecycleStatus.PAUSED
    settings.paused_at = datetime.now(timezone.utc)
    await session.commit()

    test_settings = Settings(contest_allow_instant_delete=True)
    with patch("services.contest_lifecycle_service.get_settings", return_value=test_settings):
        result = await assert_deletable(session)
        assert result.status == ContestLifecycleStatus.PAUSED


@pytest.mark.asyncio
async def test_exceptional_tiebreak_when_locked(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.is_locked = True
    user = User(
        login="u1",
        password_hash="h",
        role=UserRole.USER,
        first_name="T",
        last_name="U",
        is_temp_password=False,
    )
    session.add(user)
    await session.flush()
    user_id = user.id
    await session.commit()

    points = await update_exceptional_tiebreak(session, user_id, 5)
    assert points == 5
    await session.commit()
    refreshed = await session.get(User, user_id)
    assert refreshed is not None
    assert refreshed.exceptional_tiebreak_points == 5


@pytest.mark.asyncio
async def test_delete_contest_data_resets_to_draft(session: AsyncSession) -> None:
    settings = await session.get(ContestSettings, 1)
    settings.is_locked = True
    settings.status = ContestLifecycleStatus.PAUSED
    await session.commit()

    test_settings = Settings(
        contest_defaults_path=get_settings().contest_defaults_path,
        contest_allow_instant_delete=True,
    )
    with patch("services.contest_teardown.get_settings", return_value=test_settings):
        new_settings = await delete_contest_data(session)

    assert new_settings.status == ContestLifecycleStatus.DRAFT
    assert new_settings.is_locked is False
