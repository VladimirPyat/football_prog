"""Stage 0 integration tests for prediction constraints not covered in unit suite."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import Contest, Match, MatchStatus, Prediction, Round, RoundStatus, Team, User, UserRole


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_match_context(session: AsyncSession) -> tuple[User, Round, Match]:
    contest = Contest(
        name="Constraints Test",
        is_locked=False,
        total_teams=2,
        matches_per_round=1,
        total_rounds=1,
        is_round_robin=False,
        rules_json={"constraints": {"score_validation_range": [0, 20]}},
    )
    session.add(contest)
    await session.flush()

    team1 = Team(contest_id=contest.id, name="Team A", short_name="TA")
    team2 = Team(contest_id=contest.id, name="Team B", short_name="TB")
    round_ = Round(
        contest_id=contest.id,
        number=1,
        deadline=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        status=RoundStatus.ACTIVE,
        matches_count=1,
    )
    session.add_all([team1, team2, round_])
    await session.flush()

    match = Match(
        round_id=round_.id,
        team1_id=team1.id,
        team2_id=team2.id,
        date_time=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
        status=MatchStatus.SCHEDULED,
    )
    user = User(
        login="player1",
        password_hash="hash",
        role=UserRole.USER,
        first_name="Test",
        last_name="User",
    )
    session.add_all([match, user])
    await session.flush()
    return user, round_, match


@pytest.mark.asyncio
async def test_prediction_score_zero_zero_is_valid_not_missing(session_factory):
    """[STAGE0-PRED-01] Zero is a valid predicted score; distinct from NULL / absent row."""
    async with session_factory() as session:
        async with session.begin():
            user, round_, match = await _seed_match_context(session)
            prediction = Prediction(
                user_id=user.id,
                round_id=round_.id,
                match_id=match.id,
                score1=0,
                score2=0,
            )
            session.add(prediction)
            await session.flush()

        assert prediction.score1 == 0
        assert prediction.score2 == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_score", [-1, 25])
async def test_prediction_invalid_score_raises_integrity_error(session_factory, invalid_score):
    """[STAGE0-PRED-02] Prediction CHECK constraints reject scores outside [0, 20]."""
    async with session_factory() as session:
        async with session.begin():
            user, round_, match = await _seed_match_context(session)
            session.add(
                Prediction(
                    user_id=user.id,
                    round_id=round_.id,
                    match_id=match.id,
                    score1=invalid_score,
                    score2=0,
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()


@pytest.mark.asyncio
async def test_missing_prediction_is_absence_of_row(session_factory):
    """[STAGE0-PRED-03] No prediction row means missing prediction (not score=0 sentinel)."""
    async with session_factory() as session:
        async with session.begin():
            user, round_, match = await _seed_match_context(session)

        result = await session.execute(
            select(Prediction).where(
                Prediction.user_id == user.id,
                Prediction.round_id == round_.id,
                Prediction.match_id == match.id,
            )
        )
        assert result.scalar_one_or_none() is None
