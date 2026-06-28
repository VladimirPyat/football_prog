"""Contest discovery for enrolled users and anonymous visitors."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Contest, ContestLifecycleStatus, ContestParticipant
from schemas.contest import PublicContestOut, UserContestOut


async def list_user_contests(
    session: AsyncSession,
    *,
    user_id: int,
    role: str,
) -> list[UserContestOut]:
    """JOIN contests + contest_participants for user; order by contests.name."""
    rows = await session.execute(
        select(Contest, ContestParticipant.status)
        .join(ContestParticipant, ContestParticipant.contest_id == Contest.id)
        .where(ContestParticipant.user_id == user_id)
        .where(Contest.deleted_at.is_(None))
        .order_by(Contest.name)
    )
    return [
        UserContestOut(
            id=c.id,
            name=c.name,
            status=c.status,
            participant_status=part_status,
            role=role,
            slug=c.slug,
        )
        for c, part_status in rows.all()
    ]


async def list_public_contests(session: AsyncSession) -> list[PublicContestOut]:
    """contests WHERE status = RUNNING, order by name."""
    contests = await session.scalars(
        select(Contest)
        .where(Contest.status == ContestLifecycleStatus.RUNNING)
        .where(Contest.deleted_at.is_(None))
        .order_by(Contest.name)
    )
    return [PublicContestOut.model_validate(c) for c in contests]
