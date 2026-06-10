"""[DL-*], [ST-*], [BT-*] Tests for deadlines, status transitions, and batch submission.

Uses synthetic in-memory SQLite — no CSVs needed.
All match datetimes are set in 2030 so that the 24h-cutoff window is always open
(tests run in 2026, so now < cutoff is guaranteed).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from database.models import (
    ContestSettings,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
    Team,
    User,
    UserRole,
)
from services.prediction_service import submit_batch
from services.round_service import set_deadline, transition_round

# First match starts 2030-01-05 15:00 UTC — far in the future.
_FUTURE_MATCH_DT = datetime(2030, 1, 5, 15, 0, tzinfo=timezone.utc)
_DEADLINE_RULE_HOURS = 24
_CUTOFF_DT = _FUTURE_MATCH_DT - timedelta(hours=_DEADLINE_RULE_HOURS)

_RULES_JSON = {
    "contest_structure": {
        "deadline_rule_hours": _DEADLINE_RULE_HOURS,
        "matches_per_round": 8,
        "total_teams": 16,
        "total_rounds": 10,
        "is_round_robin": True,
    },
    "constraints": {"score_validation_range": [0, 20], "allow_partial_prediction_save": False},
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
            "bonus_2_thresholds": [],
            "bonus_3_rank_points": {"1st": 12, "2nd": 8, "3rd": 4},
            "bonus_3_base_threshold_extra": 50,
            "bonus_3_extra_points": 4,
        },
    },
    "tiebreakers": {"priority_order": ["total_points DESC"]},
}


async def _create_synthetic_round(
    session,
    round_status: RoundStatus = RoundStatus.DRAFT,
    deadline: datetime | None = None,
    first_match_dt: datetime = _FUTURE_MATCH_DT,
    n_matches: int = 8,
) -> tuple[ContestSettings, Round, list[Match], User]:
    """Create ContestSettings + Round + N matches + one User in the given session.

    Caller must wrap this in session.begin().
    """
    if deadline is None:
        deadline = first_match_dt - timedelta(days=3)

    settings = ContestSettings(
        is_locked=False,
        total_teams=16,
        matches_per_round=n_matches,
        total_rounds=10,
        is_round_robin=True,
        rules_json=_RULES_JSON,
    )
    session.add(settings)
    await session.flush()

    round_ = Round(number=1, deadline=deadline, status=round_status, matches_count=n_matches)
    session.add(round_)
    await session.flush()

    # Create 2*n_matches unique teams so each match has a distinct pair.
    teams: list[Team] = []
    for i in range(n_matches * 2):
        t = Team(name=f"Synthetic Team {i:02d}", short_name=f"ST{i:02d}")
        session.add(t)
        teams.append(t)
    await session.flush()

    matches: list[Match] = []
    for i in range(n_matches):
        m = Match(
            round_id=round_.id,
            team1_id=teams[i * 2].id,
            team2_id=teams[i * 2 + 1].id,
            date_time=first_match_dt + timedelta(hours=i),
            score1=None,
            score2=None,
            status=MatchStatus.SCHEDULED,
        )
        session.add(m)
        matches.append(m)
    await session.flush()

    user = User(
        login="synthetic_player",
        password_hash="placeholder",
        role=UserRole.USER,
        first_name="Synthetic",
        last_name="Player",
    )
    session.add(user)
    await session.flush()

    return settings, round_, matches, user


# ---------------------------------------------------------------------------
# [DL-24H-FAIL]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dl_24h_fail_at_exact_cutoff(minimal_db):
    """[DL-24H-FAIL] Deadline == (first_match − 24h) must be rejected with ValueError."""
    sf = minimal_db
    async with sf() as session:
        async with session.begin():
            _, round_, _, _ = await _create_synthetic_round(session)
            round_id = round_.id

    with pytest.raises(ValueError):
        async with sf() as session:
            async with session.begin():
                await set_deadline(session, round_id, _CUTOFF_DT)


@pytest.mark.asyncio
async def test_dl_24h_fail_within_23h_of_match(minimal_db):
    """[DL-24H-FAIL] Deadline == (first_match − 23h) must also be rejected."""
    sf = minimal_db
    async with sf() as session:
        async with session.begin():
            _, round_, _, _ = await _create_synthetic_round(session)
            round_id = round_.id

    with pytest.raises(ValueError):
        async with sf() as session:
            async with session.begin():
                await set_deadline(
                    session, round_id, _FUTURE_MATCH_DT - timedelta(hours=23)
                )


# ---------------------------------------------------------------------------
# [DL-24H-OK]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dl_24h_ok_three_days_before(minimal_db):
    """[DL-24H-OK] Deadline == (first_match − 3 days) must be accepted without error."""
    sf = minimal_db
    new_deadline = _FUTURE_MATCH_DT - timedelta(days=3)

    async with sf() as session:
        async with session.begin():
            _, round_, _, _ = await _create_synthetic_round(session)
            round_id = round_.id

    async with sf() as session:
        async with session.begin():
            await set_deadline(session, round_id, new_deadline)

    async with sf() as session:
        updated_round = await session.get(Round, round_id)
    assert updated_round is not None
    # SQLite strips timezone info on round-trip; normalise both sides to naive UTC for comparison.
    actual_dt = updated_round.deadline
    if actual_dt.tzinfo is None:
        actual_dt = actual_dt.replace(tzinfo=timezone.utc)
    assert actual_dt == new_deadline, (
        f"Expected deadline {new_deadline}, got {updated_round.deadline}"
    )


# ---------------------------------------------------------------------------
# [ST-ILLEGAL]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_st_illegal_published_to_active(minimal_db):
    """[ST-ILLEGAL] PUBLISHED → ACTIVE must raise ValueError."""
    sf = minimal_db
    async with sf() as session:
        async with session.begin():
            settings, round_, _, _ = await _create_synthetic_round(
                session, round_status=RoundStatus.PUBLISHED
            )
            settings.is_locked = True
            round_id = round_.id

    async with sf() as session:
        async with session.begin():
            with pytest.raises(ValueError, match="Illegal round status transition"):
                await transition_round(session, round_id, RoundStatus.ACTIVE)


@pytest.mark.asyncio
async def test_st_illegal_draft_to_calculated(minimal_db):
    """[ST-ILLEGAL] DRAFT → CALCULATED must raise ValueError."""
    sf = minimal_db
    async with sf() as session:
        async with session.begin():
            _, round_, _, _ = await _create_synthetic_round(
                session, round_status=RoundStatus.DRAFT
            )
            round_id = round_.id

    async with sf() as session:
        async with session.begin():
            with pytest.raises(ValueError, match="Illegal round status transition"):
                await transition_round(session, round_id, RoundStatus.CALCULATED)


# ---------------------------------------------------------------------------
# [ST-LOCK]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_st_lock_draft_to_active_sets_is_locked(minimal_db):
    """[ST-LOCK] Transitioning DRAFT → ACTIVE sets contest_settings.is_locked = True."""
    sf = minimal_db
    async with sf() as session:
        async with session.begin():
            settings, round_, _, _ = await _create_synthetic_round(
                session, round_status=RoundStatus.DRAFT
            )
            round_id = round_.id
        assert settings.is_locked is False, "Precondition: is_locked must be False initially"

    async with sf() as session:
        async with session.begin():
            await transition_round(session, round_id, RoundStatus.ACTIVE)

    async with sf() as session:
        cs = await session.scalar(select(ContestSettings).limit(1))
    assert cs is not None
    assert cs.is_locked is True, (
        f"Expected is_locked=True after DRAFT→ACTIVE, got {cs.is_locked}"
    )


# ---------------------------------------------------------------------------
# [BT-PARTIAL]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bt_partial_7_of_8_rejected(minimal_db):
    """[BT-PARTIAL] Submitting 7/8 predictions raises ValueError; DB count stays 0."""
    sf = minimal_db
    active_deadline = _FUTURE_MATCH_DT - timedelta(days=3)

    async with sf() as session:
        async with session.begin():
            _, round_, matches, user = await _create_synthetic_round(
                session,
                round_status=RoundStatus.ACTIVE,
                deadline=active_deadline,
            )
            round_id = round_.id
            user_id = user.id
            match_ids = [m.id for m in matches]

    partial_items = [(match_ids[i], 1, 0) for i in range(7)]  # 7 out of 8

    async with sf() as session:
        async with session.begin():
            with pytest.raises(ValueError):
                await submit_batch(session, user_id, round_id, partial_items)

    async with sf() as session:
        count = await session.scalar(
            select(func.count()).select_from(Prediction).where(
                Prediction.user_id == user_id,
                Prediction.round_id == round_id,
            )
        )
    assert count == 0, f"Expected 0 predictions after partial submit failure, got {count}"


# ---------------------------------------------------------------------------
# [BT-FULL]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bt_full_8_of_8_saved_atomically(minimal_db):
    """[BT-FULL] 8/8 predictions saved atomically, count=8."""
    sf = minimal_db
    active_deadline = _FUTURE_MATCH_DT - timedelta(days=3)

    async with sf() as session:
        async with session.begin():
            _, round_, matches, user = await _create_synthetic_round(
                session,
                round_status=RoundStatus.ACTIVE,
                deadline=active_deadline,
            )
            round_id = round_.id
            user_id = user.id
            match_ids = [m.id for m in matches]

    items = [(match_ids[i], 1, 0) for i in range(8)]

    async with sf() as session:
        async with session.begin():
            saved = await submit_batch(session, user_id, round_id, items)
    assert saved == 8

    async with sf() as session:
        count = await session.scalar(
            select(func.count()).select_from(Prediction).where(
                Prediction.user_id == user_id,
                Prediction.round_id == round_id,
            )
        )
    assert count == 8, f"Expected 8 predictions after first submit, got {count}"


@pytest.mark.asyncio
async def test_bt_full_resubmit_replaces_batch(minimal_db):
    """[BT-FULL] Re-submitting same batch replaces old predictions (count=8, not 16)."""
    sf = minimal_db
    active_deadline = _FUTURE_MATCH_DT - timedelta(days=3)

    async with sf() as session:
        async with session.begin():
            _, round_, matches, user = await _create_synthetic_round(
                session,
                round_status=RoundStatus.ACTIVE,
                deadline=active_deadline,
            )
            round_id = round_.id
            user_id = user.id
            match_ids = [m.id for m in matches]

    items = [(match_ids[i], 1, 0) for i in range(8)]

    async with sf() as session:
        async with session.begin():
            await submit_batch(session, user_id, round_id, items)

    async with sf() as session:
        async with session.begin():
            saved2 = await submit_batch(session, user_id, round_id, items)
    assert saved2 == 8

    async with sf() as session:
        count = await session.scalar(
            select(func.count()).select_from(Prediction).where(
                Prediction.user_id == user_id,
                Prediction.round_id == round_id,
            )
        )
    assert count == 8, (
        f"Expected 8 predictions after re-submit (replacement), got {count}. "
        "Batch must replace, not accumulate."
    )


# ---------------------------------------------------------------------------
# [BT-ZERO]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bt_zero_score_stored_as_real_value(minimal_db):
    """[BT-ZERO] score1=0, score2=0 is accepted and stored as real values (not absence)."""
    sf = minimal_db
    active_deadline = _FUTURE_MATCH_DT - timedelta(days=3)

    async with sf() as session:
        async with session.begin():
            _, round_, matches, user = await _create_synthetic_round(
                session,
                round_status=RoundStatus.ACTIVE,
                deadline=active_deadline,
            )
            round_id = round_.id
            user_id = user.id
            match_ids = [m.id for m in matches]

    items = [(match_ids[i], 0, 0) for i in range(8)]

    async with sf() as session:
        async with session.begin():
            saved = await submit_batch(session, user_id, round_id, items)
    assert saved == 8

    async with sf() as session:
        preds = (
            await session.scalars(
                select(Prediction).where(
                    Prediction.user_id == user_id,
                    Prediction.round_id == round_id,
                )
            )
        ).all()

    assert len(preds) == 8, f"Expected 8 predictions for 0:0 batch, got {len(preds)}"
    for p in preds:
        assert p.score1 == 0, f"Prediction id={p.id}: score1={p.score1} (expected 0)"
        assert p.score2 == 0, f"Prediction id={p.id}: score2={p.score2} (expected 0)"
        assert p.score1 is not None, "score1 must be integer 0, not NULL"
        assert p.score2 is not None, "score2 must be integer 0, not NULL"


# ---------------------------------------------------------------------------
# [BT-DEADLINE]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bt_deadline_past_deadline_raises_permission_error(minimal_db):
    """[BT-DEADLINE] submit_batch to ACTIVE round with past deadline raises PermissionError."""
    sf = minimal_db
    past_deadline = datetime(2020, 1, 1, tzinfo=timezone.utc)

    async with sf() as session:
        async with session.begin():
            _, round_, matches, user = await _create_synthetic_round(
                session,
                round_status=RoundStatus.ACTIVE,
                deadline=past_deadline,
            )
            round_id = round_.id
            user_id = user.id
            match_ids = [m.id for m in matches]

    items = [(match_ids[i], 1, 0) for i in range(8)]

    async with sf() as session:
        async with session.begin():
            with pytest.raises(PermissionError):
                await submit_batch(session, user_id, round_id, items)


@pytest.mark.asyncio
async def test_bt_deadline_non_active_round_raises_permission_error(minimal_db):
    """[BT-DEADLINE] submit_batch to a DRAFT round raises PermissionError regardless of deadline."""
    sf = minimal_db
    future_deadline = _FUTURE_MATCH_DT - timedelta(days=3)

    async with sf() as session:
        async with session.begin():
            _, round_, matches, user = await _create_synthetic_round(
                session,
                round_status=RoundStatus.DRAFT,
                deadline=future_deadline,
            )
            round_id = round_.id
            user_id = user.id
            match_ids = [m.id for m in matches]

    items = [(match_ids[i], 1, 0) for i in range(8)]

    async with sf() as session:
        async with session.begin():
            with pytest.raises(PermissionError):
                await submit_batch(session, user_id, round_id, items)
