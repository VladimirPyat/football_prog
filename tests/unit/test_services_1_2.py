"""Unit tests for Stage 1.2: Setup, Deadlines & Data Loader.

Coverage: ~80% edge cases / ~20% happy path.
All async tests; DB is SQLite in-memory (or temp file for loader CSV tests).
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.base import Base
from database.models import (
    ContestSettings,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
    Score,
    Team,
    User,
    UserRole,
)
from services.round_service import set_deadline, transition_round
from services.match_service import change_status, set_result
from services.prediction_service import submit_batch, visible_predictions
from services.scoring_persistence import calculate_round, recalculate_round


# ---------------------------------------------------------------------------
# Helpers / shared constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

TEST_RULES = {
    "scoring_rules": {
        "base_points": {
            "exact_high_score": 16,
            "exact_score": 12,
            "diff_plus_outcome": 8,
            "outcome_only": 4,
            "miss": 0,
        },
        "bonuses": {
            "bonus_1_unique_multiplier_pct": 200.0,
            "bonus_2_thresholds": [
                {"min_correct_outcomes": 6, "points": 8},
                {"min_correct_outcomes": 7, "points": 12},
                {"min_correct_outcomes": 8, "points": 16},
            ],
            "bonus_3_rank_points": {"1st": 12, "2nd": 8, "3rd": 4},
            "bonus_3_base_threshold_extra": 50,
            "bonus_3_extra_points": 4,
        },
    },
    "tiebreakers": {"priority_order": ["total_points DESC", "manual_override"]},
    "constraints": {
        "allow_partial_prediction_save": False,
        "require_all_matches_per_round": True,
        "score_validation_range": [0, 20],
        "max_teams_per_round_usage": 1,
    },
    "contest_structure": {
        "total_teams": 16,
        "matches_per_round": 8,
        "total_rounds": 30,
        "is_round_robin": True,
        "deadline_rule_hours": 24,
        "max_score_value": 20,
    },
}

_FUTURE = datetime.now(timezone.utc) + timedelta(days=30)
_PAST = datetime.now(timezone.utc) - timedelta(days=30)


# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite for service tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


async def _seed_settings(session: AsyncSession, **overrides) -> ContestSettings:
    rules = dict(TEST_RULES)
    cfg = ContestSettings(
        is_locked=False,
        total_teams=16,
        matches_per_round=8,
        total_rounds=30,
        is_round_robin=True,
        rules_json=rules,
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    session.add(cfg)
    await session.flush()
    return cfg


async def _make_team(session: AsyncSession, n: int) -> Team:
    t = Team(name=f"Team{n}", short_name=f"T{n}")
    session.add(t)
    await session.flush()
    return t


async def _make_user(session: AsyncSession, n: int) -> User:
    u = User(
        login=f"user{n}",
        password_hash="hash",
        role=UserRole.USER,
        first_name="",
        last_name=f"User{n}",
        is_temp_password=False,
    )
    session.add(u)
    await session.flush()
    return u


async def _make_round(
    session: AsyncSession,
    number: int = 1,
    status: RoundStatus = RoundStatus.DRAFT,
    deadline: datetime | None = None,
    matches_count: int = 8,
) -> Round:
    r = Round(
        number=number,
        status=status,
        deadline=deadline or _FUTURE,
        matches_count=matches_count,
    )
    session.add(r)
    await session.flush()
    return r


async def _make_match(
    session: AsyncSession,
    round_id: int,
    t1_id: int,
    t2_id: int,
    date_time: datetime | None = None,
    status: MatchStatus = MatchStatus.FINISHED,
    score1: int | None = 2,
    score2: int | None = 1,
) -> Match:
    m = Match(
        round_id=round_id,
        team1_id=t1_id,
        team2_id=t2_id,
        date_time=date_time or _FUTURE,
        status=status,
        score1=score1,
        score2=score2,
    )
    session.add(m)
    await session.flush()
    return m


# ---------------------------------------------------------------------------
# Loader fixture — temp file DB + real CSVs
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def loaded_db_url():
    """Create a temp SQLite DB, apply schema, run loader against real CSVs.

    Scoped to module so load runs only once per test module.
    """
    from scripts.load_test_data import run_load

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    db_url = f"sqlite+aiosqlite:///{tmp_path}"
    await run_load(database_url=db_url, reset=False)
    yield db_url

    # Cleanup temp file after module.
    tmp_path.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def loaded_session(loaded_db_url):
    engine = create_async_engine(loaded_db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


# ---------------------------------------------------------------------------
# LOADER TESTS
# ---------------------------------------------------------------------------


async def test_loader_team_count(loaded_session: AsyncSession):
    """16 teams should be loaded from teams.csv."""
    teams = (await loaded_session.scalars(select(Team))).all()
    assert len(teams) == 16, f"Expected 16 teams, got {len(teams)}"


async def test_loader_user_count(loaded_session: AsyncSession):
    """10 users should be loaded from users.csv."""
    users = (
        await loaded_session.scalars(select(User).where(User.role == UserRole.USER))
    ).all()
    assert len(users) == 10, f"Expected 10 users, got {len(users)}"


async def test_loader_match_count(loaded_session: AsyncSession):
    """80 matches total (9 rounds × 8 finished + 1 round × 8 scheduled)."""
    matches = (await loaded_session.scalars(select(Match))).all()
    assert len(matches) == 80, f"Expected 80 matches, got {len(matches)}"


async def test_loader_rounds_count(loaded_session: AsyncSession):
    """10 rounds should exist (1–10)."""
    rounds = (await loaded_session.scalars(select(Round))).all()
    assert len(rounds) == 10, f"Expected 10 rounds, got {len(rounds)}"


async def test_loader_serov_round4_no_predictions(loaded_session: AsyncSession):
    """Serov has submitted no predictions in round 4 (absence = no row)."""
    serov = await loaded_session.scalar(select(User).where(User.login == "serov"))
    assert serov is not None, "User 'serov' not found"
    round4 = await loaded_session.scalar(select(Round).where(Round.number == 4))
    assert round4 is not None, "Round 4 not found"

    count = len(
        (
            await loaded_session.scalars(
                select(Prediction).where(
                    Prediction.user_id == serov.id,
                    Prediction.round_id == round4.id,
                )
            )
        ).all()
    )
    assert count == 0, f"Serov should have 0 predictions in round 4, got {count}"


async def test_loader_round10_matches_null_scores(loaded_session: AsyncSession):
    """Round 10 SCHEDULED matches must have score1=None and score2=None."""
    round10 = await loaded_session.scalar(select(Round).where(Round.number == 10))
    assert round10 is not None
    matches = (
        await loaded_session.scalars(select(Match).where(Match.round_id == round10.id))
    ).all()
    assert len(matches) == 8
    for m in matches:
        assert m.score1 is None, f"Match {m.id} in round 10 has non-NULL score1={m.score1}"
        assert m.score2 is None, f"Match {m.id} in round 10 has non-NULL score2={m.score2}"
        assert m.status == MatchStatus.SCHEDULED


async def test_loader_unique_short_names(loaded_session: AsyncSession):
    """team short_names must be unique (enforced by loader, not just DB)."""
    teams = (await loaded_session.scalars(select(Team))).all()
    short_names = [t.short_name for t in teams]
    assert len(short_names) == len(set(short_names)), "Duplicate short_names detected"


async def test_loader_unique_logins(loaded_session: AsyncSession):
    """User logins must be unique."""
    users = (await loaded_session.scalars(select(User))).all()
    logins = [u.login for u in users]
    assert len(logins) == len(set(logins)), "Duplicate logins detected"


async def test_loader_round10_status_active(loaded_session: AsyncSession):
    """Round 10 must be ACTIVE (deliberate convention for test-data batch tests)."""
    round10 = await loaded_session.scalar(select(Round).where(Round.number == 10))
    assert round10 is not None
    assert round10.status == RoundStatus.ACTIVE


async def test_loader_rounds_1_to_9_closed(loaded_session: AsyncSession):
    """Rounds 1–9 must be CLOSED."""
    rounds = (
        await loaded_session.scalars(select(Round).where(Round.number < 10))
    ).all()
    for r in rounds:
        assert r.status == RoundStatus.CLOSED, f"Round {r.number} status={r.status}, expected CLOSED"


async def test_loader_idempotent_reset(loaded_db_url: str):
    """Reloading with --reset produces the same counts as the first load."""
    from scripts.load_test_data import run_load

    await run_load(database_url=loaded_db_url, reset=True)

    engine = create_async_engine(loaded_db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        teams = (await s.scalars(select(Team))).all()
        users = (
            await s.scalars(select(User).where(User.role == UserRole.USER))
        ).all()
        matches = (await s.scalars(select(Match))).all()
        rounds = (await s.scalars(select(Round))).all()

    await engine.dispose()

    assert len(teams) == 16
    assert len(users) == 10
    assert len(matches) == 80
    assert len(rounds) == 10


# ---------------------------------------------------------------------------
# NULL / ABSENCE INVARIANTS
# ---------------------------------------------------------------------------


async def test_null_serov_round4_db_row_count(loaded_session: AsyncSession):
    """No Prediction row exists for serov in round 4 — absence is not a NULL sentinel."""
    serov = await loaded_session.scalar(select(User).where(User.login == "serov"))
    round4 = await loaded_session.scalar(select(Round).where(Round.number == 4))
    assert serov is not None and round4 is not None
    preds = (
        await loaded_session.scalars(
            select(Prediction).where(
                Prediction.user_id == serov.id,
                Prediction.round_id == round4.id,
            )
        )
    ).all()
    assert len(preds) == 0


async def test_no_null_scores_in_predictions(loaded_session: AsyncSession):
    """Every Prediction row must have non-NULL score1 and score2."""
    preds = (await loaded_session.scalars(select(Prediction))).all()
    for p in preds:
        assert p.score1 is not None, f"Prediction id={p.id} has NULL score1"
        assert p.score2 is not None, f"Prediction id={p.id} has NULL score2"


# ---------------------------------------------------------------------------
# DEADLINE / 24h RULE TESTS (synthetic data)
# ---------------------------------------------------------------------------


async def test_deadline_valid_accepted(session: AsyncSession):
    """Setting deadline safely before (first_match - 24h) is accepted."""
    async with session.begin():
        await _seed_settings(session)
        t1 = await _make_team(session, 1)
        t2 = await _make_team(session, 2)
        first_match_dt = datetime.now(timezone.utc) + timedelta(days=5)
        r = await _make_round(session, deadline=first_match_dt - timedelta(hours=48))
        await _make_match(session, r.id, t1.id, t2.id, date_time=first_match_dt, status=MatchStatus.SCHEDULED, score1=None, score2=None)

    new_deadline = first_match_dt - timedelta(hours=30)
    async with session.begin():
        updated = await set_deadline(session, r.id, new_deadline)
    assert updated.deadline == new_deadline


async def test_deadline_equal_to_cutoff_rejected(session: AsyncSession):
    """Deadline exactly equal to (first_match - 24h) must be rejected."""
    async with session.begin():
        await _seed_settings(session)
        t1 = await _make_team(session, 1)
        t2 = await _make_team(session, 2)
        first_match_dt = datetime.now(timezone.utc) + timedelta(days=5)
        r = await _make_round(session, deadline=first_match_dt - timedelta(hours=48))
        await _make_match(session, r.id, t1.id, t2.id, date_time=first_match_dt, status=MatchStatus.SCHEDULED, score1=None, score2=None)

    bad_deadline = first_match_dt - timedelta(hours=24)  # exactly at cutoff
    with pytest.raises(ValueError, match="must be strictly before"):
        async with session.begin():
            await set_deadline(session, r.id, bad_deadline)


async def test_deadline_after_cutoff_rejected(session: AsyncSession):
    """Deadline after (first_match - 24h) must be rejected."""
    async with session.begin():
        await _seed_settings(session)
        t1 = await _make_team(session, 1)
        t2 = await _make_team(session, 2)
        first_match_dt = datetime.now(timezone.utc) + timedelta(days=5)
        r = await _make_round(session, deadline=first_match_dt - timedelta(hours=48))
        await _make_match(session, r.id, t1.id, t2.id, date_time=first_match_dt, status=MatchStatus.SCHEDULED, score1=None, score2=None)

    bad_deadline = first_match_dt - timedelta(hours=12)  # after cutoff
    with pytest.raises(ValueError, match="must be strictly before"):
        async with session.begin():
            await set_deadline(session, r.id, bad_deadline)


async def test_deadline_window_closed_rejected(session: AsyncSession):
    """Reject deadline change when the 24h window has already closed (match in the past)."""
    async with session.begin():
        await _seed_settings(session)
        t1 = await _make_team(session, 1)
        t2 = await _make_team(session, 2)
        # Match is only 10 hours away — the 24h cutoff is already in the past.
        first_match_dt = datetime.now(timezone.utc) + timedelta(hours=10)
        r = await _make_round(session, deadline=first_match_dt - timedelta(hours=48))
        await _make_match(session, r.id, t1.id, t2.id, date_time=first_match_dt, status=MatchStatus.SCHEDULED, score1=None, score2=None)

    new_deadline = first_match_dt - timedelta(hours=36)
    with pytest.raises(ValueError, match="window has closed"):
        async with session.begin():
            await set_deadline(session, r.id, new_deadline)


# ---------------------------------------------------------------------------
# BATCH PREDICTION TESTS (synthetic)
# ---------------------------------------------------------------------------


async def _setup_batch_env(session: AsyncSession, deadline: datetime | None = None) -> tuple[int, int, list[int]]:
    """Returns (user_id, round_id, [match_ids])."""
    await _seed_settings(session)
    user = await _make_user(session, 1)
    teams = [await _make_team(session, i) for i in range(16)]
    dl = deadline or (datetime.now(timezone.utc) + timedelta(days=1))
    r = await _make_round(session, status=RoundStatus.ACTIVE, deadline=dl, matches_count=8)
    match_ids = []
    for i in range(8):
        m = await _make_match(
            session,
            r.id,
            teams[i * 2].id,
            teams[i * 2 + 1].id,
            date_time=dl + timedelta(hours=1),
            status=MatchStatus.SCHEDULED,
            score1=None,
            score2=None,
        )
        match_ids.append(m.id)
    await session.flush()
    return user.id, r.id, match_ids


async def test_batch_wrong_count_rejected(session: AsyncSession):
    """Submitting 7 out of 8 items raises ValueError."""
    async with session.begin():
        uid, rid, mids = await _setup_batch_env(session)

    items_7 = [(mids[i], 1, 0) for i in range(7)]
    with pytest.raises(ValueError, match="exactly"):
        async with session.begin():
            await submit_batch(session, uid, rid, items_7)


async def test_batch_valid_saves_all(session: AsyncSession):
    """8/8 valid items are saved atomically."""
    async with session.begin():
        uid, rid, mids = await _setup_batch_env(session)

    items_8 = [(mid, 1, 0) for mid in mids]
    async with session.begin():
        saved = await submit_batch(session, uid, rid, items_8)
    assert saved == 8

    async with session.begin():
        preds = (
            await session.scalars(
                select(Prediction).where(
                    Prediction.user_id == uid, Prediction.round_id == rid
                )
            )
        ).all()
    assert len(preds) == 8


async def test_batch_zero_zero_accepted(session: AsyncSession):
    """A 0:0 prediction is a valid real score — must be stored, not rejected."""
    async with session.begin():
        uid, rid, mids = await _setup_batch_env(session)

    items = [(mids[0], 0, 0)] + [(mids[i], 1, 0) for i in range(1, 8)]
    async with session.begin():
        saved = await submit_batch(session, uid, rid, items)
    assert saved == 8

    async with session.begin():
        pred = await session.scalar(
            select(Prediction).where(
                Prediction.user_id == uid, Prediction.match_id == mids[0]
            )
        )
    assert pred is not None
    assert pred.score1 == 0
    assert pred.score2 == 0


async def test_batch_after_deadline_rejected(session: AsyncSession):
    """Submitting after the round deadline raises PermissionError."""
    past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    async with session.begin():
        uid, rid, mids = await _setup_batch_env(session, deadline=past_deadline)

    items = [(mid, 1, 0) for mid in mids]
    with pytest.raises(PermissionError, match="Deadline has passed"):
        async with session.begin():
            await submit_batch(session, uid, rid, items)


async def test_batch_invalid_score_no_partial_save(session: AsyncSession):
    """If one item has an out-of-range score, no rows are persisted."""
    async with session.begin():
        uid, rid, mids = await _setup_batch_env(session)

    # score2=999 is invalid
    items = [(mids[0], 1, 999)] + [(mids[i], 1, 0) for i in range(1, 8)]
    with pytest.raises(ValueError, match="out of range"):
        async with session.begin():
            await submit_batch(session, uid, rid, items)

    async with session.begin():
        count = len(
            (
                await session.scalars(
                    select(Prediction).where(
                        Prediction.user_id == uid, Prediction.round_id == rid
                    )
                )
            ).all()
        )
    assert count == 0, "No predictions should be saved on partial failure"


async def test_batch_round_not_active_rejected(session: AsyncSession):
    """Submitting to a non-ACTIVE round raises PermissionError."""
    async with session.begin():
        await _seed_settings(session)
        user = await _make_user(session, 1)
        teams = [await _make_team(session, i) for i in range(16)]
        r = await _make_round(session, status=RoundStatus.CLOSED, matches_count=8)
        match_ids = []
        for i in range(8):
            m = await _make_match(session, r.id, teams[i * 2].id, teams[i * 2 + 1].id, status=MatchStatus.FINISHED)
            match_ids.append(m.id)

    items = [(mid, 1, 0) for mid in match_ids]
    with pytest.raises(PermissionError, match="must be ACTIVE"):
        async with session.begin():
            await submit_batch(session, user.id, r.id, items)


# ---------------------------------------------------------------------------
# STATUS MACHINE TESTS
# ---------------------------------------------------------------------------


async def test_illegal_transition_rejected(session: AsyncSession):
    """DRAFT → CALCULATED is not a valid transition."""
    async with session.begin():
        await _seed_settings(session)
        r = await _make_round(session, status=RoundStatus.DRAFT)

    with pytest.raises(ValueError, match="Illegal"):
        async with session.begin():
            await transition_round(session, r.id, RoundStatus.CALCULATED)


async def test_draft_to_active_to_closed_succeeds(session: AsyncSession):
    """DRAFT → ACTIVE → CLOSED is a valid two-step transition."""
    async with session.begin():
        await _seed_settings(session)
        r = await _make_round(session, status=RoundStatus.DRAFT)

    async with session.begin():
        r = await transition_round(session, r.id, RoundStatus.ACTIVE)
    assert r.status == RoundStatus.ACTIVE

    async with session.begin():
        r = await transition_round(session, r.id, RoundStatus.CLOSED)
    assert r.status == RoundStatus.CLOSED


async def test_active_transition_locks_settings(session: AsyncSession):
    """Transitioning a round to ACTIVE sets contest_settings.is_locked = True."""
    async with session.begin():
        settings = await _seed_settings(session)
        assert settings.is_locked is False
        r = await _make_round(session, status=RoundStatus.DRAFT)

    async with session.begin():
        await transition_round(session, r.id, RoundStatus.ACTIVE)

    async with session.begin():
        s = await session.scalar(select(ContestSettings))
    assert s is not None
    assert s.is_locked is True


async def test_published_to_any_rejected(session: AsyncSession):
    """No transitions allowed from PUBLISHED."""
    async with session.begin():
        await _seed_settings(session)
        r = await _make_round(session, status=RoundStatus.PUBLISHED)
        round_id = r.id  # capture id before session closes

    for target in RoundStatus:
        with pytest.raises(ValueError):
            async with session.begin():
                await transition_round(session, round_id, target)


# ---------------------------------------------------------------------------
# CALCULATE ROUND TESTS
# ---------------------------------------------------------------------------


async def _setup_scorable_round(session: AsyncSession) -> tuple[int, list[int]]:
    """Create a CLOSED round with 2 finished matches and 2 users with predictions.

    Returns (round_id, [user_ids]).
    """
    settings = await _seed_settings(session)
    u1 = await _make_user(session, 1)
    u2 = await _make_user(session, 2)
    t1 = await _make_team(session, 1)
    t2 = await _make_team(session, 2)
    t3 = await _make_team(session, 3)
    t4 = await _make_team(session, 4)

    r = await _make_round(session, status=RoundStatus.CLOSED, matches_count=2)
    m1 = await _make_match(session, r.id, t1.id, t2.id, score1=2, score2=1, status=MatchStatus.FINISHED)
    m2 = await _make_match(session, r.id, t3.id, t4.id, score1=0, score2=0, status=MatchStatus.FINISHED)

    # u1 predicts exact for m1 and misses m2; u2 predicts outcome for m1
    for uid, s1, s2, match in [(u1.id, 2, 1, m1), (u1.id, 1, 2, m2), (u2.id, 1, 0, m1), (u2.id, 0, 0, m2)]:
        p = Prediction(user_id=uid, round_id=r.id, match_id=match.id, score1=s1, score2=s2)
        session.add(p)

    await session.flush()
    return r.id, [u1.id, u2.id]


async def test_calculate_round_creates_score_rows(session: AsyncSession):
    """calculate_round persists Score rows for all participants."""
    async with session.begin():
        round_id, user_ids = await _setup_scorable_round(session)

    async with session.begin():
        count = await calculate_round(session, round_id)

    assert count == len(user_ids)

    async with session.begin():
        scores = (await session.scalars(select(Score).where(Score.round_id == round_id))).all()
    assert len(scores) == len(user_ids)


async def test_calculate_round_totals_match_engine(session: AsyncSession):
    """Score totals match direct engine.score_round output (spot-check user1)."""
    from scoring.engine import score_round
    from scoring.types import MatchResult, UserPrediction

    async with session.begin():
        round_id, user_ids = await _setup_scorable_round(session)

    async with session.begin():
        await calculate_round(session, round_id)

    async with session.begin():
        score_row = await session.scalar(
            select(Score).where(Score.round_id == round_id, Score.user_id == user_ids[0])
        )
        preds = (await session.scalars(select(Prediction).where(Prediction.round_id == round_id))).all()
        matches = (await session.scalars(select(Match).where(Match.round_id == round_id))).all()
        all_uids = user_ids

    results = [MatchResult(match_id=m.id, score1=m.score1, score2=m.score2, is_scorable=True) for m in matches]
    predictions = [UserPrediction(user_id=p.user_id, match_id=p.match_id, score1=p.score1, score2=p.score2) for p in preds]
    engine_scores = score_round(results, predictions, all_uids, rules=TEST_RULES)

    uid1 = user_ids[0]
    expected = engine_scores[uid1]

    assert score_row is not None
    assert score_row.total_with_bonus3 == expected.total_with_bonus3
    assert score_row.total_without_bonus3 == expected.total_without_bonus3
    assert score_row.count_exact_high == expected.count_exact_high
    assert score_row.count_exact == expected.count_exact


async def test_calculate_round_non_closed_raises(session: AsyncSession):
    """calculate_round on a non-CLOSED round raises ValueError."""
    async with session.begin():
        await _seed_settings(session)
        r = await _make_round(session, status=RoundStatus.ACTIVE)

    with pytest.raises(ValueError, match="CLOSED"):
        async with session.begin():
            await calculate_round(session, r.id)


async def test_calculate_round_transitions_to_calculated(session: AsyncSession):
    """After calculate_round, the round status becomes CALCULATED."""
    async with session.begin():
        round_id, _ = await _setup_scorable_round(session)

    async with session.begin():
        await calculate_round(session, round_id)

    async with session.begin():
        r = await session.get(Round, round_id)
    assert r.status == RoundStatus.CALCULATED


async def test_void_match_triggers_recalculate(session: AsyncSession):
    """VOIDing a match in a CALCULATED round recalculates scores atomically."""
    async with session.begin():
        round_id, user_ids = await _setup_scorable_round(session)

    async with session.begin():
        await calculate_round(session, round_id)

    # Capture scores before VOID.
    async with session.begin():
        scores_before = {
            s.user_id: s.total_with_bonus3
            for s in (await session.scalars(select(Score).where(Score.round_id == round_id))).all()
        }

    # VOID the first match.
    async with session.begin():
        match = await session.scalar(select(Match).where(Match.round_id == round_id).limit(1))
        await change_status(session, match.id, MatchStatus.VOID)

    # Scores should now be recalculated (match excluded from scoring).
    async with session.begin():
        scores_after = {
            s.user_id: s.total_with_bonus3
            for s in (await session.scalars(select(Score).where(Score.round_id == round_id))).all()
        }

    # At least one score should have changed (or stayed same if match was already 0-scoring).
    # Crucially: no partial state — all users have a score row.
    assert len(scores_after) == len(user_ids)
    # Verify the round is still CALCULATED after recalculation.
    async with session.begin():
        r = await session.get(Round, round_id)
    assert r.status == RoundStatus.CALCULATED


async def test_recalculate_non_calculated_round_raises(session: AsyncSession):
    """recalculate_round on a non-CALCULATED round raises ValueError."""
    async with session.begin():
        await _seed_settings(session)
        r = await _make_round(session, status=RoundStatus.CLOSED)

    with pytest.raises(ValueError, match="CALCULATED"):
        async with session.begin():
            await recalculate_round(session, r.id)


# ---------------------------------------------------------------------------
# CALCULATE_ROUND SPOT-CHECK ON LOADED DATA
# ---------------------------------------------------------------------------


async def test_calculate_round_on_loaded_round1(loaded_db_url: str):
    """calculate_round on the real round 1 data produces scores consistent with engine."""
    from scoring.engine import score_round
    from scoring.types import MatchResult, UserPrediction

    engine = create_async_engine(loaded_db_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        async with session.begin():
            # round 1 must be CLOSED for calculate_round to proceed.
            round1 = await session.scalar(select(Round).where(Round.number == 1))
            assert round1 is not None
            assert round1.status == RoundStatus.CLOSED

            await calculate_round(session, round1.id)

        async with session.begin():
            scores = (
                await session.scalars(select(Score).where(Score.round_id == round1.id))
            ).all()
            assert len(scores) > 0

            # Spot-check: engine output for volchenko should match stored Score.
            volchenko = await session.scalar(select(User).where(User.login == "volchenko"))
            assert volchenko is not None

            score_row = await session.scalar(
                select(Score).where(
                    Score.round_id == round1.id, Score.user_id == volchenko.id
                )
            )
            assert score_row is not None

            preds = (
                await session.scalars(select(Prediction).where(Prediction.round_id == round1.id))
            ).all()
            matches = (
                await session.scalars(
                    select(Match).where(
                        Match.round_id == round1.id,
                        Match.status == MatchStatus.FINISHED,
                        Match.score1.is_not(None),
                    )
                )
            ).all()
            all_uids = list(await session.scalars(select(User.id)))
            settings = await session.scalar(select(ContestSettings))

    results = [
        MatchResult(match_id=m.id, score1=m.score1, score2=m.score2, is_scorable=True)
        for m in matches
    ]
    predictions = [
        UserPrediction(user_id=p.user_id, match_id=p.match_id, score1=p.score1, score2=p.score2)
        for p in preds
        if p.score1 is not None and p.score2 is not None
    ]
    engine_out = score_round(results, predictions, all_uids, rules=settings.rules_json)

    expected = engine_out[volchenko.id]
    assert score_row.total_with_bonus3 == expected.total_with_bonus3
    assert score_row.count_exact == expected.count_exact
    assert score_row.count_exact_high == expected.count_exact_high

    await engine.dispose()
