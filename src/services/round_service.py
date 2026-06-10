"""Round status machine and deadline management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContestSettings, Match, Round, RoundStatus

# Valid one-step transitions in the round lifecycle.
_VALID_TRANSITIONS: dict[RoundStatus, set[RoundStatus]] = {
    RoundStatus.DRAFT: {RoundStatus.ACTIVE},
    RoundStatus.ACTIVE: {RoundStatus.CLOSED},
    RoundStatus.CLOSED: {RoundStatus.CALCULATED},
    RoundStatus.CALCULATED: {RoundStatus.PUBLISHED},
    RoundStatus.PUBLISHED: set(),
}


async def _get_round(session: AsyncSession, round_id: int) -> Round:
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    return round_


async def _get_settings(session: AsyncSession) -> ContestSettings:
    settings = await session.scalar(select(ContestSettings).limit(1))
    if settings is None:
        raise ValueError("Contest settings not found in database")
    return settings


async def _earliest_match_dt(session: AsyncSession, round_id: int) -> datetime:
    matches = (await session.scalars(select(Match).where(Match.round_id == round_id))).all()
    if not matches:
        raise ValueError(f"No matches found for round {round_id}")
    return min(m.date_time for m in matches)


async def transition_round(
    session: AsyncSession, round_id: int, target_status: RoundStatus
) -> Round:
    """Apply a status transition to the round.

    Raises ValueError on illegal transitions.
    Locking contest_settings when transitioning to ACTIVE.
    Caller is responsible for wrapping in a transaction.
    """
    round_ = await _get_round(session, round_id)
    current = RoundStatus(round_.status)
    allowed = _VALID_TRANSITIONS.get(current, set())

    if target_status not in allowed:
        raise ValueError(
            f"Illegal round status transition: {current} → {target_status}. "
            f"Allowed from {current}: {allowed or 'none'}"
        )

    if target_status == RoundStatus.ACTIVE:
        # Lock contest settings when a round is first activated.
        settings = await _get_settings(session)
        settings.is_locked = True

    round_.status = target_status
    return round_


async def set_deadline(
    session: AsyncSession, round_id: int, new_deadline: datetime
) -> Round:
    """Update the round deadline, enforcing the deadline_rule_hours constraint.

    Raises ValueError if:
    - new_deadline >= earliest_match_datetime − deadline_rule_hours
    - The change window has already closed (now > cutoff)

    All datetimes must be timezone-aware.
    """
    if new_deadline.tzinfo is None:
        raise ValueError("new_deadline must be timezone-aware")

    round_ = await _get_round(session, round_id)
    settings = await _get_settings(session)
    deadline_rule_hours: int = settings.rules_json["contest_structure"]["deadline_rule_hours"]

    earliest = await _earliest_match_dt(session, round_id)
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=timezone.utc)

    cutoff = earliest - timedelta(hours=deadline_rule_hours)
    now = datetime.now(timezone.utc)

    if now > cutoff:
        raise ValueError(
            f"Deadline change window has closed: now ({now}) > cutoff ({cutoff}). "
            "No more changes allowed."
        )

    if new_deadline >= cutoff:
        raise ValueError(
            f"New deadline ({new_deadline}) must be strictly before "
            f"earliest_match − {deadline_rule_hours}h = {cutoff}"
        )

    round_.deadline = new_deadline
    return round_
