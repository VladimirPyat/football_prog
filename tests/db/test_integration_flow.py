"""Stage 0 integration flow tests — full lifecycle, batch uniqueness, DBeaver smoke data."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from database.base import Base
from database.models import (
    Contest,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
    Team,
    User,
    UserRole,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTEST_DEFAULTS_PATH = PROJECT_ROOT / "docs" / "test_data" / "config" / "contest_defaults.json"


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _load_contest_defaults() -> dict:
    with CONTEST_DEFAULTS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _build_rules_json(data: dict) -> dict:
    return {
        "scoring_rules": data["scoring_rules"],
        "tiebreakers": data["tiebreakers"],
        "constraints": data["constraints"],
        "contest_structure": data["contest_structure"],
    }


async def _seed_contest(session: AsyncSession) -> Contest:
    data = _load_contest_defaults()
    structure = data["contest_structure"]
    contest = Contest(
        name="Default",
        is_locked=False,
        total_teams=structure["total_teams"],
        matches_per_round=structure["matches_per_round"],
        total_rounds=structure["total_rounds"],
        is_round_robin=structure["is_round_robin"],
        rules_json=_build_rules_json(data),
    )
    session.add(contest)
    await session.flush()
    return contest


async def _create_teams(session: AsyncSession, contest_id: int, count: int) -> list[Team]:
    teams = [
        Team(contest_id=contest_id, name=f"Team_{index:02d}", short_name=f"T{index:02d}")
        for index in range(1, count + 1)
    ]
    session.add_all(teams)
    await session.flush()
    return teams


async def _create_user(
    session: AsyncSession,
    *,
    login: str,
    first_name: str,
    last_name: str,
) -> User:
    user = User(
        login=login,
        password_hash="hash",
        role=UserRole.USER,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_if01_full_round_lifecycle(session_factory):
    """[IF-01] Seed contest → round → 8 matches → 3×8 predictions → 2 FINISHED → JOIN."""
    base_time = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        async with session.begin():
            contest = await _seed_contest(session)

            round_ = Round(
                contest_id=contest.id,
                number=1,
                deadline=base_time - timedelta(days=1),
                status=RoundStatus.ACTIVE,
                matches_count=8,
            )
            session.add(round_)
            await session.flush()

            teams = await _create_teams(session, contest.id, 16)
            matches: list[Match] = []
            for index in range(8):
                match = Match(
                    round_id=round_.id,
                    team1_id=teams[index * 2].id,
                    team2_id=teams[index * 2 + 1].id,
                    date_time=base_time + timedelta(hours=index),
                    score1=None,
                    score2=None,
                    status=MatchStatus.SCHEDULED,
                )
                matches.append(match)
            session.add_all(matches)
            await session.flush()

            users = [
                await _create_user(session, login="volchenko", first_name="Alex", last_name="Volchenko"),
                await _create_user(session, login="ivanov", first_name="Ivan", last_name="Ivanov"),
                await _create_user(session, login="petrov", first_name="Petr", last_name="Petrov"),
            ]

            predictions: list[Prediction] = []
            for user in users:
                for match_index, match in enumerate(matches):
                    predictions.append(
                        Prediction(
                            user_id=user.id,
                            round_id=round_.id,
                            match_id=match.id,
                            score1=match_index % 3,
                            score2=(match_index + 1) % 3,
                        )
                    )
            session.add_all(predictions)
            await session.flush()

            matches[0].status = MatchStatus.FINISHED
            matches[0].score1 = 2
            matches[0].score2 = 1
            matches[1].status = MatchStatus.FINISHED
            matches[1].score1 = 0
            matches[1].score2 = 0

        join_rows = await session.execute(
            select(User.id, Prediction.id, Match.id, Match.score1, Match.score2, Match.status)
            .join(Prediction, Prediction.user_id == User.id)
            .join(Match, Match.id == Prediction.match_id)
            .where(Prediction.round_id == round_.id)
        )
        rows = join_rows.all()

        assert len(rows) == 24

        scheduled_null_scores = [
            row for row in rows if row.status == MatchStatus.SCHEDULED.value
        ]
        assert len(scheduled_null_scores) == 18
        assert all(row.score1 is None and row.score2 is None for row in scheduled_null_scores)

        finished_rows = [row for row in rows if row.status == MatchStatus.FINISHED.value]
        assert len(finished_rows) == 6
        finished_by_match = {row[2]: (row[3], row[4]) for row in finished_rows}
        assert finished_by_match[matches[0].id] == (2, 1)
        assert finished_by_match[matches[1].id] == (0, 0)


@pytest.mark.asyncio
async def test_if02_batch_prediction_uniqueness(session_factory):
    """[IF-02] Full prediction set for volchenko; duplicate (user, round, match) fails."""
    base_time = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        async with session.begin():
            contest = await _seed_contest(session)

            round_ = Round(
                contest_id=contest.id,
                number=1,
                deadline=base_time - timedelta(days=1),
                status=RoundStatus.ACTIVE,
                matches_count=8,
            )
            session.add(round_)
            await session.flush()

            teams = await _create_teams(session, contest.id, 16)
            matches = [
                Match(
                    round_id=round_.id,
                    team1_id=teams[index * 2].id,
                    team2_id=teams[index * 2 + 1].id,
                    date_time=base_time + timedelta(hours=index),
                    score1=None,
                    score2=None,
                    status=MatchStatus.SCHEDULED,
                )
                for index in range(8)
            ]
            session.add_all(matches)
            await session.flush()

            user = await _create_user(
                session,
                login="volchenko",
                first_name="Alex",
                last_name="Volchenko",
            )

            session.add_all(
                Prediction(
                    user_id=user.id,
                    round_id=round_.id,
                    match_id=match.id,
                    score1=1,
                    score2=0,
                )
                for match in matches
            )
            await session.flush()

            duplicate = Prediction(
                user_id=user.id,
                round_id=round_.id,
                match_id=matches[0].id,
                score1=2,
                score2=1,
            )
            session.add(duplicate)
            with pytest.raises(IntegrityError):
                await session.flush()


@pytest.mark.asyncio
async def test_if03_dbeaver_visual_verification_data(session_factory, capsys):
    """[IF-03] Minimal labeled chain for manual DBeaver lookup; log all inserted IDs."""
    base_time = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)
    dbeaver_name = "DBeaver_Check_Stage0"

    async with session_factory() as session:
        async with session.begin():
            contest = Contest(
                name=dbeaver_name,
                is_locked=False,
                total_teams=2,
                matches_per_round=1,
                total_rounds=1,
                is_round_robin=False,
                rules_json={
                    "dbeaver_check_name": dbeaver_name,
                    "purpose": "manual DBeaver smoke verification",
                },
            )
            session.add(contest)
            await session.flush()

            home = Team(contest_id=contest.id, name="Test_Home", short_name="TH")
            away = Team(contest_id=contest.id, name="Test_Away", short_name="TA")
            session.add_all([home, away])
            await session.flush()

            round_ = Round(
                contest_id=contest.id,
                number=99,
                deadline=base_time - timedelta(days=1),
                status=RoundStatus.ACTIVE,
                matches_count=1,
            )
            session.add(round_)
            await session.flush()

            match = Match(
                round_id=round_.id,
                team1_id=home.id,
                team2_id=away.id,
                date_time=base_time,
                score1=None,
                score2=None,
                status=MatchStatus.SCHEDULED,
            )
            session.add(match)
            await session.flush()

            user = User(
                login="dbeaver_test_user",
                password_hash="hash",
                role=UserRole.USER,
                first_name="DBeaver",
                last_name="Tester",
            )
            session.add(user)
            await session.flush()

            prediction = Prediction(
                user_id=user.id,
                round_id=round_.id,
                match_id=match.id,
                score1=0,
                score2=0,
            )
            session.add(prediction)
            await session.flush()

            ids = {
                "contest_settings_id": contest.id,
                "team_home_id": home.id,
                "team_away_id": away.id,
                "round_id": round_.id,
                "match_id": match.id,
                "user_id": user.id,
                "prediction_id": prediction.id,
                "dbeaver_check_name": dbeaver_name,
            }

        print(
            "[IF-03] DBeaver smoke test IDs: "
            + ", ".join(f"{key}={value}" for key, value in ids.items())
        )

        captured = capsys.readouterr()
        assert "contest_settings_id=" in captured.out
        assert f"match_id={match.id}" in captured.out
        assert f"prediction_id={prediction.id}" in captured.out
        assert prediction.score1 == 0
        assert prediction.score2 == 0
        assert match.score1 is None
        assert match.score2 is None
