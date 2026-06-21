"""Atomic round scoring: DB data → engine → Score rows."""

from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ContestRuleError, NotFoundError, ValidationError
from database.models import (
    Contest,
    ContestParticipant,
    Match,
    MatchStatus,
    Prediction,
    Round,
    RoundStatus,
    Score,
)
from scoring.rules import ScoringRules
from scoring.engine import score_round
from scoring.types import MatchResult, UserPrediction

logger = logging.getLogger(__name__)


async def _get_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise NotFoundError(f"Конкурс {contest_id} не найден")
    return contest


async def _collect_round_data(
    session: AsyncSession, round_id: int, contest_id: int
) -> tuple[list[MatchResult], list[UserPrediction], list[int]]:
    """Load scorable matches, predictions, and participant IDs for a round."""
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не найден в конкурсе {contest_id}")

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

    predictions: list[UserPrediction] = []
    skipped_null = 0
    for p in prediction_rows:
        if p.score1 is None or p.score2 is None:
            skipped_null += 1
            continue
        predictions.append(
            UserPrediction(
                user_id=p.user_id,
                match_id=p.match_id,
                score1=p.score1,
                score2=p.score2,
            )
        )
    if skipped_null:
        logger.warning(
            "scoring skipped %s predictions with NULL scores round_id=%s",
            skipped_null,
            round_id,
        )

    participant_ids = list(
        await session.scalars(
            select(ContestParticipant.user_id).where(
                ContestParticipant.contest_id == contest_id,
                ContestParticipant.status == "ACCEPTED",
            )
        )
    )

    logger.debug(
        "scoring data round_id=%s matches=%s predictions=%s participants=%s",
        round_id,
        len(results),
        len(predictions),
        len(participant_ids),
    )

    return results, predictions, participant_ids


async def _persist_scores(
    session: AsyncSession,
    round_id: int,
    user_scores: dict,
    rules: dict,
) -> int:
    """Upsert Score rows for all participants. Returns users_scored."""
    sr = ScoringRules(rules)

    for uid, user_score in user_scores.items():
        score_row = Score(
            user_id=uid,
            round_id=round_id,
            points_exact=(
                user_score.count_exact_high * sr.exact_high_score
                + user_score.count_exact * sr.exact_score
            ),
            points_diff=user_score.count_diff * sr.diff_plus_outcome,
            points_outcome=user_score.count_outcome * sr.outcome_only,
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


async def calculate_round(
    session: AsyncSession, round_id: int, contest_id: int
) -> int:
    """Compute and persist scores for a CLOSED round; transition it to CALCULATED."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise NotFoundError(f"Тур {round_id} не найден")
    if round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не принадлежит конкурсу {contest_id}")
    if RoundStatus(round_.status) != RoundStatus.CLOSED:
        raise ContestRuleError(
            f"Расчёт возможен только для закрытого тура (статус: {round_.status})",
            code="ROUND_NOT_CLOSED",
        )

    contest = await _get_contest(session, contest_id)
    results, predictions, participant_ids = await _collect_round_data(
        session, round_id, contest_id
    )
    user_scores = score_round(results, predictions, participant_ids, rules=contest.rules_json)

    count = await _persist_scores(session, round_id, user_scores, contest.rules_json)

    round_.status = RoundStatus.CALCULATED
    logger.info(
        "round calculated contest_id=%s round_id=%s users_scored=%s",
        contest_id,
        round_id,
        count,
    )
    return count


async def recalculate_round(
    session: AsyncSession, round_id: int, contest_id: int
) -> int:
    """Re-run scoring for a CALCULATED round."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise NotFoundError(f"Тур {round_id} не найден")
    if round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не принадлежит конкурсу {contest_id}")
    if RoundStatus(round_.status) != RoundStatus.CALCULATED:
        raise ValidationError(
            f"Пересчёт возможен только для рассчитанного тура (статус: {round_.status})"
        )

    await session.execute(delete(Score).where(Score.round_id == round_id))

    contest = await _get_contest(session, contest_id)
    results, predictions, participant_ids = await _collect_round_data(
        session, round_id, contest_id
    )
    user_scores = score_round(results, predictions, participant_ids, rules=contest.rules_json)

    count = await _persist_scores(session, round_id, user_scores, contest.rules_json)
    logger.info(
        "round recalculated contest_id=%s round_id=%s users_scored=%s",
        contest_id,
        round_id,
        count,
    )
    return count


async def recalculate_contest(session: AsyncSession, contest_id: int) -> int:
    """Recalculate all CALCULATED rounds in a contest."""
    rounds = (
        await session.scalars(
            select(Round).where(
                Round.contest_id == contest_id,
                Round.status == RoundStatus.CALCULATED,
            )
        )
    ).all()
    count = 0
    for round_ in rounds:
        await recalculate_round(session, round_.id, contest_id)
        count += 1
    return count
