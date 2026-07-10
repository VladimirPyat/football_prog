"""Stage 1.14 — dev fixture finalize script tests."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.api.reference_compare import (  # noqa: E402
    build_score_lookup,
    compare_scores_to_expected,
    load_expected_scores,
)

from database.models import (  # noqa: E402
    ContestParticipant,
    Match,
    MatchStatus,
    ParticipantStatus,
    Round,
    Score,
    User,
)


def _run_with_db(db_url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": db_url}
    subprocess.run(
        ["uv", "run", "python", "src/scripts/load_test_data.py", "--reset", "--database-url", db_url],
        cwd=PROJECT_ROOT,
        check=True,
        env=env,
    )
    subprocess.run(
        ["uv", "run", "python", "src/scripts/bootstrap_users.py", "--database-url", db_url],
        cwd=PROJECT_ROOT,
        check=True,
        env=env,
    )
    if args:
        subprocess.run(
            ["uv", "run", "python", "src/scripts/dev_setup.py", *args],
            cwd=PROJECT_ROOT,
            check=True,
            env=env,
        )


@pytest.fixture
def isolated_db(tmp_path: Path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/fixture_1_14.db"
    engine = create_async_engine(db_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    yield db_url, sf, engine
    asyncio.run(engine.dispose())


@pytest.fixture
def manual_fixture_db(isolated_db) -> str:
    db_url, _, _ = isolated_db
    _run_with_db(db_url)
    env = {**os.environ, "DATABASE_URL": db_url}
    subprocess.run(
        ["uv", "run", "python", "src/scripts/dev_setup.py", "--ensure-running-only"],
        cwd=PROJECT_ROOT,
        check=True,
        env=env,
    )
    return db_url


@pytest.fixture
def e2e_fixture_db(isolated_db) -> str:
    db_url, _, _ = isolated_db
    _run_with_db(db_url, "--ensure-running-only", "--e2e")
    return db_url


@pytest.fixture
def e2e_with_published_fixture_db(isolated_db) -> str:
    db_url, _, _ = isolated_db
    _run_with_db(db_url, "--ensure-running-only", "--e2e-with-published")
    return db_url


async def _fixture_rows(sf: async_sessionmaker[AsyncSession]) -> list[dict]:
    async with sf() as session:
        result = await session.execute(
            text(
                """
                SELECT r.number, r.status,
                       (SELECT COUNT(*) FROM scores s WHERE s.round_id = r.id) AS score_rows,
                       (SELECT COUNT(*) FROM matches m WHERE m.round_id = r.id) AS match_rows
                FROM rounds r
                WHERE r.contest_id = 1
                ORDER BY r.number
                """
            )
        )
        return [dict(row._mapping) for row in result]


@pytest.mark.asyncio
async def test_script_finalize_profile_manual(
    manual_fixture_db: str,
    isolated_db: tuple[str, async_sessionmaker[AsyncSession]],
) -> None:
    _, sf, _ = isolated_db
    rows = await _fixture_rows(sf)
    by_num = {r["number"]: r for r in rows}

    for n in range(1, 10):
        assert by_num[n]["status"] == "PUBLISHED"
        assert by_num[n]["score_rows"] == 10

    assert by_num[10]["status"] == "CALCULATED"
    assert by_num[10]["score_rows"] == 10
    assert by_num[11]["status"] == "CLOSED"
    assert by_num[11]["score_rows"] == 0


@pytest.mark.asyncio
async def test_fixture_scores_1_9_match_expected(
    manual_fixture_db: str,
    isolated_db: tuple[str, async_sessionmaker[AsyncSession]],
) -> None:
    _, sf, _ = isolated_db
    expected = [row for row in load_expected_scores() if int(row["round_number"]) <= 9]
    login_to_id, round_num_to_id, score_map = await build_score_lookup(sf, 1)
    matched, mismatches = compare_scores_to_expected(
        expected, login_to_id, round_num_to_id, score_map
    )
    assert not mismatches, mismatches[:5]
    assert matched == 90


@pytest.mark.asyncio
async def test_script_finalize_idempotent(
    manual_fixture_db: str,
    isolated_db: tuple[str, async_sessionmaker[AsyncSession]],
) -> None:
    db_url, sf, _ = isolated_db
    env = {**os.environ, "DATABASE_URL": db_url}
    subprocess.run(
        ["uv", "run", "python", "src/scripts/dev_setup.py", "--finalize-fixture-only"],
        cwd=PROJECT_ROOT,
        check=True,
        env=env,
    )
    async with sf() as session:
        total = await session.scalar(
            select(func.count())
            .select_from(Score)
            .join(Round, Score.round_id == Round.id)
            .where(Round.contest_id == 1)
        )
        assert total == 100


@pytest.mark.asyncio
async def test_script_finalize_profile_e2e(
    e2e_fixture_db: str,
    isolated_db: tuple[str, async_sessionmaker[AsyncSession]],
) -> None:
    _, sf, _ = isolated_db
    async with sf() as session:
        round_10 = await session.scalar(
            select(Round).where(Round.contest_id == 1, Round.number == 10)
        )
        assert round_10 is not None
        assert round_10.status == "ACTIVE"
        assert round_10.deadline.replace(tzinfo=UTC) > datetime.now(UTC)
        score_count = await session.scalar(
            select(func.count()).select_from(Score).where(Score.round_id == round_10.id)
        )
        assert score_count == 0
        round_11 = await session.scalar(
            select(Round).where(Round.contest_id == 1, Round.number == 11)
        )
        assert round_11 is None


@pytest.mark.asyncio
async def test_script_finalize_profile_e2e_with_published(
    e2e_with_published_fixture_db: str,
    isolated_db: tuple[str, async_sessionmaker[AsyncSession]],
) -> None:
    _, sf, _ = isolated_db
    rows = await _fixture_rows(sf)
    by_num = {r["number"]: r for r in rows}

    for n in range(1, 10):
        assert by_num[n]["status"] == "PUBLISHED"
        assert by_num[n]["score_rows"] == 10

    assert by_num[10]["status"] == "ACTIVE"
    assert by_num[10]["score_rows"] == 0
    assert by_num[11]["status"] == "CLOSED"
    assert by_num[11]["score_rows"] == 0

    async with sf() as session:
        round_10 = await session.scalar(
            select(Round).where(Round.contest_id == 1, Round.number == 10)
        )
        assert round_10 is not None
        assert round_10.deadline.replace(tzinfo=UTC) > datetime.now(UTC)

        demo_user = await session.scalar(select(User).where(User.login == "shutov"))
        assert demo_user is not None
        part = await session.scalar(
            select(ContestParticipant).where(
                ContestParticipant.contest_id == 1,
                ContestParticipant.user_id == demo_user.id,
            )
        )
        assert part is not None
        assert part.status == ParticipantStatus.ACCEPTED.value


@pytest.mark.asyncio
async def test_fixture_11_deadline_and_matches(
    manual_fixture_db: str,
    isolated_db: tuple[str, async_sessionmaker[AsyncSession]],
) -> None:
    _, sf, _ = isolated_db
    async with sf() as session:
        round_11 = await session.scalar(
            select(Round).where(Round.contest_id == 1, Round.number == 11)
        )
        assert round_11 is not None
        assert round_11.deadline.replace(tzinfo=UTC) < datetime.now(UTC)
        matches = (
            await session.scalars(select(Match).where(Match.round_id == round_11.id))
        ).all()
        assert len(matches) == 8
        for m in matches:
            assert m.status == MatchStatus.SCHEDULED.value
            assert m.score1 is None and m.score2 is None
