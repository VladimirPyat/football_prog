"""Sync auto-close hook for expired ACTIVE rounds."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AppError
from database.models import Round, RoundStatus
from services.round_service import close_round, transition_round

logger = logging.getLogger(__name__)


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
        deadline = round_.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        if deadline <= now:
            try:
                await close_round(session, contest_id, round_.id)
            except AppError as exc:
                logger.warning(
                    "auto_close skip round_id=%s contest_id=%s reason=%s",
                    round_.id,
                    contest_id,
                    exc.message,
                )
                try:
                    await transition_round(session, round_.id, RoundStatus.CLOSED)
                except AppError as inner:
                    logger.warning(
                        "auto_close transition skip round_id=%s reason=%s",
                        round_.id,
                        inner.message,
                    )
                    continue
            closed_ids.append(round_.id)
            logger.debug(
                "auto_close closed round_id=%s contest_id=%s",
                round_.id,
                contest_id,
            )

    return closed_ids
