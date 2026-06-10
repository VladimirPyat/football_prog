"""Atomic round scoring: DB data → engine → Score rows."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    ContestSettings,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
    Score,
    User,
)
from scoring.rules import ScoringRules
from scoring.engine import score_round
from scoring.types import MatchResult, UserPrediction


async def _get_settings(session: AsyncSession) -> ContestSettings:
    settings = await session.scalar(select(ContestSettings).limit(1))
    if settings is None:
        raise ValueError("Contest settings not found in database")
    return settings


async def _collect_round_data(
    session: AsyncSession, round_id: int
) -> tuple[list[MatchResult], list[UserPrediction], list[int]]:
    """Load scorable matches, predictions, and participant IDs for a round."""
    # Only FINISHED matches with non-NULL scores are scorable; VOID/SCHEDULED/POSTPONED/CANCELED excluded.
    matches_rows = (
        await session.scalars(
            select(Match).where(
                Match.round_id == round_id,
                Match.status == MatchStatus.FINISHED,
                Match.score1.is_not(None),
                Match.score2.is_not(None),
            )
        )
    ).all()

    results = [
        MatchResult(
            match_id=m.id,
            score1=m.score1,
            score2=m.score2,
            is_scorable=True,
        )
        for m in matches_rows
    ]

    prediction_rows = (
        await session.scalars(select(Prediction).where(Prediction.round_id == round_id))
    ).all()

    predictions = [
        UserPrediction(
            user_id=p.user_id,
            match_id=p.match_id,
            score1=p.score1,  # type: ignore[arg-type]  # never NULL via submit_batch
            score2=p.score2,  # type: ignore[arg-type]
        )
        for p in prediction_rows
        if p.score1 is not None and p.score2 is not None
    ]

    user_ids = list(
        await session.scalars(select(User.id))
    )

    return results, predictions, user_ids


async def _persist_scores(
    session: AsyncSession,
    round_id: int,
    user_scores: dict,
    rules: dict,
) -> int:
    """Upsert Score rows for all participants. Returns users_scored."""
    sr = ScoringRules(rules)

    for uid, user_score in user_scores.items():
        points_exact = (
            user_score.count_exact_high * sr.exact_high_score
            + user_score.count_exact * sr.exact_score
        )
        points_diff = user_score.count_diff * sr.diff_plus_outcome
        points_outcome = user_score.count_outcome * sr.outcome_only

        score_row = Score(
            user_id=uid,
            round_id=round_id,
            points_exact=points_exact,
            points_diff=points_diff,
            points_outcome=points_outcome,
            bonus1=user_score.bonus1,
            bonus2=user_score.bonus2,
            bonus3=user_score.bonus3,
            total_without_bonus3=user_score.total_without_bonus3,
            total_with_bonus3=user_score.total_with_bonus3,
            correct_outcomes=user_score.correct_outcomes,
            count_exact_high=user_score.count_exact_high,
            count_exact=user_score.count_exact,
            count_diff=user_score.count_diff,
            count_outcome=user_score.count_outcome,
        )
        session.add(score_row)

    return len(user_scores)


async def calculate_round(session: AsyncSession, round_id: int) -> int:
    """Compute and persist scores for a CLOSED round; transition it to CALCULATED.

    Returns the number of users scored.
    Raises ValueError if the round is not in CLOSED status.
    Caller is responsible for wrapping in a transaction.
    """
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    if round_.status != RoundStatus.CLOSED:
        raise ValueError(
            f"calculate_round requires CLOSED status, got {round_.status} for round {round_id}"
        )

    settings = await _get_settings(session)
    results, predictions, participant_ids = await _collect_round_data(session, round_id)
    user_scores = score_round(results, predictions, participant_ids, rules=settings.rules_json)

    count = await _persist_scores(session, round_id, user_scores, settings.rules_json)

    round_.status = RoundStatus.CALCULATED
    return count


async def recalculate_round(session: AsyncSession, round_id: int) -> int:
    """Re-run scoring for a CALCULATED round (e.g. after a VOID result change).

    Deletes existing Score rows for the round and recomputes from current match data.
    Returns the number of users scored.
    Caller is responsible for wrapping in a transaction.
    """
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    if round_.status != RoundStatus.CALCULATED:
        raise ValueError(
            f"recalculate_round requires CALCULATED status, got {round_.status} for round {round_id}"
        )

    # Remove existing scores atomically before reinserting.
    await session.execute(delete(Score).where(Score.round_id == round_id))

    settings = await _get_settings(session)
    results, predictions, participant_ids = await _collect_round_data(session, round_id)
    user_scores = score_round(results, predictions, participant_ids, rules=settings.rules_json)

    count = await _persist_scores(session, round_id, user_scores, settings.rules_json)
    # Round stays CALCULATED — no status transition on recalculation.
    return count
