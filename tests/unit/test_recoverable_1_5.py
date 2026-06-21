"""Stage 1.5: recoverable fallback [REC-*]."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import (
    ContestLifecycleStatus,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
)
from services.contest_setup_service import create_contest, create_team
from services.leaderboard_service import _tiebreak_points
from services.round_auto_close_service import auto_close_expired_rounds
from services.scoring_persistence import _collect_round_data


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


class TestRecoverableFallbacks:
    """Recoverable paths: skip bad data, continue flow, log WARNING."""

    def test_rec_module_importable(self) -> None:
        """[REC-SMOKE] scoring persistence exposes collect with skip logic."""
        assert callable(_collect_round_data)

    @pytest.mark.asyncio
    async def test_rec_pred_null_skipped_with_warning(self, session: AsyncSession, caplog) -> None:
        """[REC-PRED-NULL] NULL prediction scores skipped; WARNING logged."""
        caplog.set_level(logging.WARNING)
        contest = await create_contest(session, "Null Pred")
        contest.status = ContestLifecycleStatus.RUNNING
        t1 = await create_team(session, contest.id, "Team A", "TA")
        t2 = await create_team(session, contest.id, "Team B", "TB")
        round_ = Round(
            contest_id=contest.id,
            number=1,
            deadline=datetime.now(timezone.utc) + timedelta(days=1),
            status=RoundStatus.CLOSED.value,
            matches_count=1,
        )
        session.add(round_)
        await session.flush()
        match = Match(
            round_id=round_.id,
            team1_id=t1.id,
            team2_id=t2.id,
            date_time=datetime.now(timezone.utc) + timedelta(days=2),
            status=MatchStatus.FINISHED,
            score1=1,
            score2=0,
        )
        session.add(match)
        await session.flush()
        session.add(
            Prediction(
                user_id=1,
                round_id=round_.id,
                match_id=match.id,
                score1=None,
                score2=None,
            )
        )
        session.add(
            Prediction(
                user_id=2,
                round_id=round_.id,
                match_id=match.id,
                score1=1,
                score2=0,
            )
        )
        await session.commit()

        results, predictions, _ = await _collect_round_data(session, round_.id, contest.id)
        assert len(results) == 1
        assert len(predictions) == 1
        assert any(r.levelname == "WARNING" for r in caplog.records)

    @pytest.mark.asyncio
    async def test_rec_autoclose_skip_already_closed(self, session: AsyncSession, caplog) -> None:
        """[REC-AUTOCLOSE-SKIP] auto-close on already CLOSED round → no exception."""
        caplog.set_level(logging.WARNING)
        contest = await create_contest(session, "Auto Skip")
        contest.status = ContestLifecycleStatus.RUNNING
        t1 = await create_team(session, contest.id, "T1", "T1")
        t2 = await create_team(session, contest.id, "T2", "T2")
        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        round_ = Round(
            contest_id=contest.id,
            number=1,
            deadline=past_deadline,
            status=RoundStatus.CLOSED.value,
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
        assert closed == []

    def test_rec_tiebreak_default_zero(self, caplog) -> None:
        """[REC-TIEBREAK-DEFAULT] missing participant override → 0 with WARNING."""
        caplog.set_level(logging.WARNING)
        points = _tiebreak_points(999, {}, context="leaderboard")
        assert points == 0
        assert any(r.levelname == "WARNING" for r in caplog.records)
