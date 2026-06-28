"""Sync auto-close hook for expired ACTIVE rounds."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppError, NotFoundError
from database.models import Round, RoundStatus
from services.round_service import close_round, transition_round

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def _close_active_if_deadline_passed(
    session: AsyncSession,
    round_: Round,
    *,
    now: datetime,
) -> Round:
    """Transition ACTIVE → CLOSED when deadline <= now. Returns refreshed round."""
    deadline = _ensure_utc(round_.deadline)
    if now < deadline:
        return round_

    try:
        return await close_round(session, round_.contest_id, round_.id)
    except AppError as exc:
        logger.warning(
            "auto_close skip round_id=%s contest_id=%s reason=%s",
            round_.id,
            round_.contest_id,
            exc.message,
        )
        try:
            return await transition_round(session, round_.id, RoundStatus.CLOSED)
        except AppError as inner:
            logger.warning(
                "auto_close transition skip round_id=%s reason=%s",
                round_.id,
                inner.message,
            )
            return round_


async def ensure_round_closed_if_expired(
    session: AsyncSession,
    round_id: int,
    *,
    now: datetime | None = None,
) -> Round:
    """If round is ACTIVE and deadline <= now(UTC), transition to CLOSED. Idempotent."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise NotFoundError(f"Тур {round_id} не найден")

    if round_.status != RoundStatus.ACTIVE.value:
        return round_

    closed = await _close_active_if_deadline_passed(
        session, round_, now=_ensure_utc(now or datetime.now(UTC))
    )
    if closed.status != round_.status:
        logger.debug(
            "ensure_round_closed round_id=%s contest_id=%s",
            round_id,
            round_.contest_id,
        )
    return closed


async def auto_close_expired_rounds(session: AsyncSession, contest_id: int) -> list[int]:
    """ACTIVE rounds with deadline <= now(UTC) → CLOSED. Returns closed round ids."""
    now = datetime.now(UTC)
    active_rounds = (
        await session.scalars(
            select(Round).where(
                Round.contest_id == contest_id,
                Round.status == RoundStatus.ACTIVE.value,
            )
        )
    ).all()

    closed_ids: list[int] = []
    for round_ in active_rounds:
        before = round_.status
        refreshed = await ensure_round_closed_if_expired(session, round_.id, now=now)
        if before == RoundStatus.ACTIVE.value and refreshed.status == RoundStatus.CLOSED.value:
            closed_ids.append(refreshed.id)

    return closed_ids
