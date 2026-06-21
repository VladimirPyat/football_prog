"""Batch prediction submission and visibility filter."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Contest, Match, Prediction, Round, RoundStatus, UserRole


async def _get_contest_for_round(session: AsyncSession, round_id: int) -> Contest:
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    contest = await session.get(Contest, round_.contest_id)
    if contest is None:
        raise ValueError(f"Contest {round_.contest_id} not found")
    return contest


async def submit_batch(
    session: AsyncSession,
    contest_id: int,
    user_id: int,
    round_id: int,
    items: list[tuple[int, int, int]],
) -> int:
    """Submit predictions for all matches in a round atomically."""
    contest = await _get_contest_for_round(session, round_id)
    if contest.id != contest_id:
        raise ValueError(f"Round {round_id} does not belong to contest {contest_id}")

    matches_per_round: int = contest.matches_per_round
    max_score: int = contest.rules_json["constraints"]["score_validation_range"][1]

    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")

    now = datetime.now(timezone.utc)
    deadline = round_.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if round_.status != RoundStatus.ACTIVE:
        raise PermissionError(
            f"Predictions not accepted: round {round_id} status is {round_.status} (must be ACTIVE)"
        )

    if now >= deadline:
        raise PermissionError(
            f"Deadline has passed for round {round_id}: {deadline}"
        )

    if len(items) != matches_per_round:
        raise ValueError(
            f"Expected exactly {matches_per_round} predictions, got {len(items)}"
        )

    round_matches = (
        await session.scalars(select(Match).where(Match.round_id == round_id))
    ).all()
    round_match_ids = {m.id for m in round_matches}
    submitted_match_ids = {match_id for (match_id, _, _) in items}

    if submitted_match_ids != round_match_ids:
        missing = round_match_ids - submitted_match_ids
        extra = submitted_match_ids - round_match_ids
        raise ValueError(
            f"Prediction match coverage mismatch. Missing: {missing}. Extra: {extra}."
        )

    for match_id, score1, score2 in items:
        if not (0 <= score1 <= max_score):
            raise ValueError(
                f"score1={score1} for match {match_id} out of range [0, {max_score}]"
            )
        if not (0 <= score2 <= max_score):
            raise ValueError(
                f"score2={score2} for match {match_id} out of range [0, {max_score}]"
            )

    await session.execute(
        delete(Prediction).where(
            Prediction.user_id == user_id, Prediction.round_id == round_id
        )
    )

    for match_id, score1, score2 in items:
        prediction = Prediction(
            user_id=user_id,
            round_id=round_id,
            match_id=match_id,
            score1=score1,
            score2=score2,
        )
        session.add(prediction)

    return len(items)


async def visible_predictions(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    viewer_role: str,
    viewer_id: int,
) -> list[dict]:
    """Return predictions filtered by deadline and viewer role."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    if round_.contest_id != contest_id:
        raise ValueError(f"Round {round_id} does not belong to contest {contest_id}")

    now = datetime.now(timezone.utc)
    deadline = round_.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    after_deadline = now >= deadline
    is_privileged = viewer_role in {UserRole.SUPERVISOR, UserRole.ADMIN}

    predictions = (
        await session.scalars(
            select(Prediction).where(Prediction.round_id == round_id)
        )
    ).all()

    result: list[dict] = []
    for pred in predictions:
        if after_deadline or is_privileged or pred.user_id == viewer_id:
            result.append(
                {
                    "user_id": pred.user_id,
                    "match_id": pred.match_id,
                    "score1": pred.score1,
                    "score2": pred.score2,
                    "submitted": True,
                }
            )
        else:
            result.append({"user_id": pred.user_id, "submitted": True})

    return result
