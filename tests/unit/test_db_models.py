import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import (
    Contest,
    ContestLifecycleStatus,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
    Team,
    User,
    UserRole,
)


async def _create_contest(session: AsyncSession) -> Contest:
    contest = Contest(
        name="Test",
        is_locked=False,
        status=ContestLifecycleStatus.DRAFT,
        total_teams=16,
        matches_per_round=8,
        total_rounds=1,
        is_round_robin=False,
        rules_json={
            "scoring_rules": {},
            "tiebreakers": {},
            "constraints": {"score_validation_range": [0, 20]},
            "contest_structure": {"deadline_rule_hours": 24},
        },
    )
    session.add(contest)
    await session.flush()
    return contest


async def _create_team(session: AsyncSession, contest_id: int, name: str, short_name: str) -> Team:
    team = Team(contest_id=contest_id, name=name, short_name=short_name)
    session.add(team)
    await session.flush()
    return team


async def _create_round(session: AsyncSession, contest_id: int) -> Round:
    round_ = Round(
        contest_id=contest_id,
        number=1,
        deadline=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        status=RoundStatus.ACTIVE,
    )
    session.add(round_)
    await session.flush()
    return round_


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _create_user(session: AsyncSession, login: str = "player1") -> User:
    user = User(
        login=login,
        password_hash="hash",
        role=UserRole.USER,
        first_name="Test",
        last_name="User",
    )
    session.add(user)
    await session.flush()
    return user


async def _create_match(
    session: AsyncSession,
    round_: Round,
    team1: Team,
    team2: Team,
    *,
    score1: int | None = None,
    score2: int | None = None,
) -> Match:
    match = Match(
        round_id=round_.id,
        team1_id=team1.id,
        team2_id=team2.id,
        date_time=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
        score1=score1,
        score2=score2,
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    await session.flush()
    return match


@pytest.mark.asyncio
async def test_match_score_zero_zero_succeeds(session_factory):
    async with session_factory() as session:
        async with session.begin():
            contest = await _create_contest(session)
            team1 = await _create_team(session, contest.id, "Team A", "TA")
            team2 = await _create_team(session, contest.id, "Team B", "TB")
            round_ = await _create_round(session, contest.id)
            match = await _create_match(session, round_, team1, team2, score1=0, score2=0)

        assert match.score1 == 0
        assert match.score2 == 0


@pytest.mark.asyncio
async def test_match_score_null_null_succeeds(session_factory):
    async with session_factory() as session:
        async with session.begin():
            contest = await _create_contest(session)
            team1 = await _create_team(session, contest.id, "Team A", "TA")
            team2 = await _create_team(session, contest.id, "Team B", "TB")
            round_ = await _create_round(session, contest.id)
            match = await _create_match(session, round_, team1, team2, score1=None, score2=None)

        assert match.score1 is None
        assert match.score2 is None


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_score", [-1, 25])
async def test_match_invalid_score_raises_integrity_error(session_factory, invalid_score):
    async with session_factory() as session:
        async with session.begin():
            contest = await _create_contest(session)
            team1 = await _create_team(session, contest.id, "Team A", "TA")
            team2 = await _create_team(session, contest.id, "Team B", "TB")
            round_ = await _create_round(session, contest.id)
            session.add(
                Match(
                    round_id=round_.id,
                    team1_id=team1.id,
                    team2_id=team2.id,
                    date_time=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
                    score1=invalid_score,
                    score2=0,
                    status=MatchStatus.SCHEDULED,
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()


@pytest.mark.asyncio
async def test_match_same_team_raises_integrity_error(session_factory):
    async with session_factory() as session:
        async with session.begin():
            contest = await _create_contest(session)
            team = await _create_team(session, contest.id, "Team A", "TA")
            round_ = await _create_round(session, contest.id)
            session.add(
                Match(
                    round_id=round_.id,
                    team1_id=team.id,
                    team2_id=team.id,
                    date_time=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
                    status=MatchStatus.SCHEDULED,
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()


@pytest.mark.asyncio
async def test_duplicate_prediction_raises_integrity_error(session_factory):
    async with session_factory() as session:
        async with session.begin():
            contest = await _create_contest(session)
            team1 = await _create_team(session, contest.id, "Team A", "TA")
            team2 = await _create_team(session, contest.id, "Team B", "TB")
            round_ = await _create_round(session, contest.id)
            match = await _create_match(session, round_, team1, team2)
            user = await _create_user(session)

            session.add(
                Prediction(
                    user_id=user.id,
                    round_id=round_.id,
                    match_id=match.id,
                    score1=1,
                    score2=0,
                )
            )
            await session.flush()

            session.add(
                Prediction(
                    user_id=user.id,
                    round_id=round_.id,
                    match_id=match.id,
                    score1=2,
                    score2=1,
                )
            )
            with pytest.raises(IntegrityError):
                await session.flush()


@pytest.mark.asyncio
async def test_prediction_null_scores_succeeds(session_factory):
    async with session_factory() as session:
        async with session.begin():
            contest = await _create_contest(session)
            team1 = await _create_team(session, contest.id, "Team A", "TA")
            team2 = await _create_team(session, contest.id, "Team B", "TB")
            round_ = await _create_round(session, contest.id)
            match = await _create_match(session, round_, team1, team2)
            user = await _create_user(session)

            prediction = Prediction(
                user_id=user.id,
                round_id=round_.id,
                match_id=match.id,
                score1=None,
                score2=None,
            )
            session.add(prediction)
            await session.flush()

        assert prediction.score1 is None
        assert prediction.score2 is None
