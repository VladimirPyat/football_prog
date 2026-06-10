"""Match result entry and status management."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContestSettings, Match, MatchStatus, Round, RoundStatus


async def _get_match(session: AsyncSession, match_id: int) -> Match:
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    return match


async def _get_settings(session: AsyncSession) -> ContestSettings:
    settings = await session.scalar(select(ContestSettings).limit(1))
    if settings is None:
        raise ValueError("Contest settings not found in database")
    return settings


def _validate_score(value: int, max_value: int, label: str) -> None:
    if not (0 <= value <= max_value):
        raise ValueError(f"{label} score {value} out of valid range [0, {max_value}]")


async def set_result(
    session: AsyncSession, match_id: int, score1: int, score2: int
) -> Match:
    """Record a final result for a match and mark it FINISHED.

    Validates both scores against the contest max_score_value.
    Caller is responsible for wrapping in a transaction.
    """
    match = await _get_match(session, match_id)
    settings = await _get_settings(session)
    max_score: int = settings.rules_json["constraints"]["score_validation_range"][1]

    _validate_score(score1, max_score, "score1")
    _validate_score(score2, max_score, "score2")

    match.score1 = score1
    match.score2 = score2
    match.status = MatchStatus.FINISHED
    return match


async def change_status(
    session: AsyncSession, match_id: int, new_status: MatchStatus
) -> Match:
    """Change a match status to VOID, POSTPONED, or CANCELED.

    If the match's round is CALCULATED and the new status is VOID,
    triggers a round recalculation atomically within the same session.
    Caller is responsible for wrapping in a transaction.
    """
    # Import here to avoid circular import at module level.
    from services.scoring_persistence import recalculate_round  # noqa: PLC0415

    allowed_targets = {MatchStatus.VOID, MatchStatus.POSTPONED, MatchStatus.CANCELED}
    if new_status not in allowed_targets:
        raise ValueError(
            f"change_status only accepts {allowed_targets}, got {new_status}"
        )

    match = await _get_match(session, match_id)
    match.status = new_status

    if new_status == MatchStatus.VOID:
        round_ = await session.get(Round, match.round_id)
        if round_ is not None and round_.status == RoundStatus.CALCULATED:
            await recalculate_round(session, match.round_id)

    return match
