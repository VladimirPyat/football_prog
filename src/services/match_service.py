"""Match result entry and status management."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Contest, Match, MatchStatus, Round, RoundStatus
from services.contest_lifecycle_service import assert_contest_running


async def _get_match(session: AsyncSession, match_id: int) -> Match:
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")
    return match


async def _get_contest_for_round(session: AsyncSession, round_id: int) -> Contest:
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    contest = await session.get(Contest, round_.contest_id)
    if contest is None:
        raise ValueError(f"Contest {round_.contest_id} not found")
    return contest


def _validate_score(value: int, max_value: int, label: str) -> None:
    if not (0 <= value <= max_value):
        raise ValueError(f"{label} score {value} out of valid range [0, {max_value}]")


async def set_result(
    session: AsyncSession,
    contest_id: int,
    match_id: int,
    score1: int,
    score2: int,
) -> Match:
    """Record a final result for a match and mark it FINISHED."""
    match = await _get_match(session, match_id)
    round_ = await session.get(Round, match.round_id)
    if round_ is None:
        raise ValueError(f"Round for match {match_id} not found")
    if round_.contest_id != contest_id:
        raise ValueError(f"Match {match_id} does not belong to contest {contest_id}")

    now = datetime.now(timezone.utc)
    deadline = round_.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if now < deadline:
        raise ValueError("Results allowed only after round deadline")
    if RoundStatus(round_.status) != RoundStatus.CLOSED:
        raise ValueError("Round must be CLOSED before entering results")

    await assert_contest_running(session, contest_id)

    contest = await _get_contest_for_round(session, match.round_id)
    max_score: int = contest.rules_json["constraints"]["score_validation_range"][1]

    _validate_score(score1, max_score, "score1")
    _validate_score(score2, max_score, "score2")

    match.score1 = score1
    match.score2 = score2
    match.status = MatchStatus.FINISHED
    return match


async def change_status(
    session: AsyncSession, contest_id: int, match_id: int, new_status: MatchStatus
) -> Match:
    """Change a match status to VOID, POSTPONED, or CANCELED."""
    from services.scoring_persistence import recalculate_round  # noqa: PLC0415

    allowed_targets = {MatchStatus.VOID, MatchStatus.POSTPONED, MatchStatus.CANCELED}
    if new_status not in allowed_targets:
        raise ValueError(
            f"change_status only accepts {allowed_targets}, got {new_status}"
        )

    match = await _get_match(session, match_id)
    round_ = await session.get(Round, match.round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise ValueError(f"Match {match_id} does not belong to contest {contest_id}")

    match.status = new_status

    if new_status == MatchStatus.VOID and round_.status == RoundStatus.CALCULATED:
        await recalculate_round(session, round_id=round_.id, contest_id=contest_id)

    return match
