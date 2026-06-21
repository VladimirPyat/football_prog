"""Contest participant lifecycle helpers."""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContestParticipant, ParticipantStatus


async def accept_pending_participations(session: AsyncSession, user_id: int) -> int:
    """Flip all PENDING contest_participants rows to ACCEPTED for user. Returns rows updated."""
    result = await session.execute(
        update(ContestParticipant)
        .where(
            ContestParticipant.user_id == user_id,
            ContestParticipant.status == ParticipantStatus.PENDING,
        )
        .values(status=ParticipantStatus.ACCEPTED)
    )
    return result.rowcount or 0
