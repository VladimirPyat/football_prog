"""Sync auto-close hook for expired ACTIVE rounds."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Round, RoundStatus
from services.round_service import transition_round


async def auto_close_expired_rounds(session: AsyncSession, contest_id: int) -> list[int]:
    """ACTIVE rounds with deadline <= now(UTC) → CLOSED. Returns closed round ids."""
    now = datetime.now(timezone.utc)
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
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= now:
            await transition_round(session, round_.id, RoundStatus.CLOSED)
            closed_ids.append(round_.id)

    return closed_ids
