"""[LD-*] Loader integrity tests — contracted data mapped correctly into SQLite.

Tests verify counts by id-based SQL queries and spot-check key data points.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from database.models import Match, MatchStatus, Prediction, Round, Team, User
from scripts.load_test_data import run_load

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# [LD-COUNT]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ld_count_teams(loaded_db):
    """[LD-COUNT] Exactly 16 team rows after load."""
    sf, _, _ = loaded_db
    async with sf() as session:
        count = await session.scalar(select(func.count()).select_from(Team))
    assert count == 16, f"Expected 16 teams, got {count}"


@pytest.mark.asyncio
async def test_ld_count_users(loaded_db):
    """[LD-COUNT] Exactly 10 user rows after load."""
    sf, _, _ = loaded_db
    async with sf() as session:
        count = await session.scalar(select(func.count()).select_from(User))
    assert count == 10, f"Expected 10 users, got {count}"


@pytest.mark.asyncio
async def test_ld_count_rounds(loaded_db):
    """[LD-COUNT] Exactly 10 round rows after load."""
    sf, _, _ = loaded_db
    async with sf() as session:
        count = await session.scalar(select(func.count()).select_from(Round))
    assert count == 10, f"Expected 10 rounds, got {count}"


@pytest.mark.asyncio
async def test_ld_count_finished_matches(loaded_db):
    """[LD-COUNT] Exactly 72 FINISHED matches (9 rounds × 8)."""
    sf, _, _ = loaded_db
    async with sf() as session:
        count = await session.scalar(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.FINISHED)
        )
    assert count == 72, f"Expected 72 FINISHED matches, got {count}"


@pytest.mark.asyncio
async def test_ld_count_scheduled_matches(loaded_db):
    """[LD-COUNT] Exactly 8 SCHEDULED matches (round 10)."""
    sf, _, _ = loaded_db
    async with sf() as session:
        count = await session.scalar(
            select(func.count()).select_from(Match).where(Match.status == MatchStatus.SCHEDULED)
        )
    assert count == 8, f"Expected 8 SCHEDULED matches, got {count}"


# ---------------------------------------------------------------------------
# [LD-NULL]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ld_null_round10_scores_and_status(loaded_db):
    """[LD-NULL] Round 10 matches: score1 IS NULL, score2 IS NULL, status SCHEDULED."""
    sf, _, _ = loaded_db
    async with sf() as session:
        round_10 = await session.scalar(select(Round).where(Round.number == 10))
        assert round_10 is not None, "Round 10 not found"
        matches = (
            await session.scalars(select(Match).where(Match.round_id == round_10.id))
        ).all()

    assert len(matches) == 8, f"Expected 8 matches in round 10, got {len(matches)}"
    for m in matches:
        assert m.score1 is None, f"Match id={m.id}: expected score1=NULL, got {m.score1}"
        assert m.score2 is None, f"Match id={m.id}: expected score2=NULL, got {m.score2}"
        assert m.status == MatchStatus.SCHEDULED, (
            f"Match id={m.id}: expected SCHEDULED, got {m.status}"
        )


# ---------------------------------------------------------------------------
# [LD-ABSENCE]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ld_absence_serov_round4_zero_rows(loaded_db):
    """[LD-ABSENCE] serov has exactly 0 prediction rows in round 4."""
    sf, _, _ = loaded_db
    async with sf() as session:
        serov = await session.scalar(select(User).where(User.login == "serov"))
        assert serov is not None, "User 'serov' not found in DB"
        round_4 = await session.scalar(select(Round).where(Round.number == 4))
        assert round_4 is not None, "Round 4 not found in DB"
        pred_count = await session.scalar(
            select(func.count()).select_from(Prediction).where(
                Prediction.user_id == serov.id,
                Prediction.round_id == round_4.id,
            )
        )
    assert pred_count == 0, (
        f"Expected 0 predictions for serov/round4, got {pred_count}. "
        "Absence must be represented by no row, not a placeholder."
    )


@pytest.mark.asyncio
async def test_ld_absence_no_null_score_predictions(loaded_db):
    """[LD-ABSENCE] No prediction row has NULL score1 or score2 — absence = no row."""
    sf, _, _ = loaded_db
    async with sf() as session:
        null_count = await session.scalar(
            select(func.count()).select_from(Prediction).where(
                Prediction.score1.is_(None)
            )
        )
    assert null_count == 0, (
        f"Found {null_count} prediction(s) with NULL score1. "
        "All loaded predictions must have real integer scores."
    )


@pytest.mark.asyncio
async def test_ld_absence_no_zero_placeholder_for_serov_round4(loaded_db):
    """[LD-ABSENCE] No 0:0 placeholder row for serov/round4 — absence is represented by no row."""
    sf, _, _ = loaded_db
    async with sf() as session:
        serov = await session.scalar(select(User).where(User.login == "serov"))
        round_4 = await session.scalar(select(Round).where(Round.number == 4))
        placeholder_count = await session.scalar(
            select(func.count()).select_from(Prediction).where(
                Prediction.user_id == serov.id,
                Prediction.round_id == round_4.id,
                Prediction.score1 == 0,
                Prediction.score2 == 0,
            )
        )
    assert placeholder_count == 0, (
        f"Found {placeholder_count} 0:0 placeholder row(s) for serov/round4."
    )


# ---------------------------------------------------------------------------
# [LD-MAP]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ld_map_unique_short_names(loaded_db):
    """[LD-MAP] All team short_name values are unique."""
    sf, _, _ = loaded_db
    async with sf() as session:
        teams = (await session.scalars(select(Team))).all()
    short_names = [t.short_name for t in teams]
    duplicates = [s for s in short_names if short_names.count(s) > 1]
    assert len(duplicates) == 0, f"Duplicate short_names: {set(duplicates)}"


@pytest.mark.asyncio
async def test_ld_map_unique_logins(loaded_db):
    """[LD-MAP] All user login values are unique."""
    sf, _, _ = loaded_db
    async with sf() as session:
        users = (await session.scalars(select(User))).all()
    logins = [u.login for u in users]
    duplicates = [login for login in logins if logins.count(login) > 1]
    assert len(duplicates) == 0, f"Duplicate logins: {set(duplicates)}"


@pytest.mark.asyncio
async def test_ld_map_spot_check_din_vs_balt_round1(loaded_db):
    """[LD-MAP] Round 1 Дин vs Балт is found by short_name lookup and has score 1:1."""
    sf, _, _ = loaded_db
    async with sf() as session:
        round_1 = await session.scalar(select(Round).where(Round.number == 1))
        assert round_1 is not None, "Round 1 not found"

        din = await session.scalar(select(Team).where(Team.short_name == "Дин"))
        balt = await session.scalar(select(Team).where(Team.short_name == "Балт"))
        assert din is not None, "Team short_name='Дин' not found"
        assert balt is not None, "Team short_name='Балт' not found"

        match = await session.scalar(
            select(Match).where(
                Match.round_id == round_1.id,
                Match.team1_id == din.id,
                Match.team2_id == balt.id,
            )
        )
    assert match is not None, "Match Дин vs Балт in round 1 not found"
    assert match.score1 == 1, f"Expected score1=1, got {match.score1}"
    assert match.score2 == 1, f"Expected score2=1, got {match.score2}"
    assert match.status == MatchStatus.FINISHED


# ---------------------------------------------------------------------------
# [LD-IDEMPOTENT]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ld_idempotent_double_load(loaded_db):
    """[LD-IDEMPOTENT] Running loader twice with --reset yields identical row counts."""
    sf, _, db_url = loaded_db

    async with sf() as session:
        teams_before = await session.scalar(select(func.count()).select_from(Team))
        users_before = await session.scalar(select(func.count()).select_from(User))
        rounds_before = await session.scalar(select(func.count()).select_from(Round))
        matches_before = await session.scalar(select(func.count()).select_from(Match))
        preds_before = await session.scalar(select(func.count()).select_from(Prediction))

    await run_load(database_url=db_url, reset=True)

    async with sf() as session:
        teams_after = await session.scalar(select(func.count()).select_from(Team))
        users_after = await session.scalar(select(func.count()).select_from(User))
        rounds_after = await session.scalar(select(func.count()).select_from(Round))
        matches_after = await session.scalar(select(func.count()).select_from(Match))
        preds_after = await session.scalar(select(func.count()).select_from(Prediction))

    assert teams_after == teams_before, f"Teams changed: {teams_before} → {teams_after}"
    assert users_after == users_before, f"Users changed: {users_before} → {users_after}"
    assert rounds_after == rounds_before, f"Rounds changed: {rounds_before} → {rounds_after}"
    assert matches_after == matches_before, f"Matches changed: {matches_before} → {matches_after}"
    assert preds_after == preds_before, f"Predictions changed: {preds_before} → {preds_after}"
