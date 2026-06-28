"""Detect whether round bonuses must wait for postponed matches."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Match, MatchStatus

_TERMINAL_EXCLUDED = frozenset(
    {
        MatchStatus.CANCELED.value,
        MatchStatus.VOID.value,
    }
)

_PENDING_STATUSES = frozenset(
    {
        MatchStatus.POSTPONED.value,
        MatchStatus.SCHEDULED.value,
    }
)

BONUSES_PENDING_MESSAGE = (
    "Бонусы тура будут рассчитаны после сыгранных перенесённых матчей. "
    "Основные очки по завершённым матчам уже учтены."
)


async def origin_round_bonuses_pending(
    session: AsyncSession, origin_round_id: int
) -> tuple[bool, str | None]:
    """True when logical tour still has matches that block bonus settlement."""
    rows = (
        await session.execute(
            select(Match.status).where(
                or_(
                    Match.round_id == origin_round_id,
                    Match.origin_round_id == origin_round_id,
                )
            )
        )
    ).all()

    if not rows:
        return False, None

    for (status,) in rows:
        if status in _PENDING_STATUSES:
            return True, BONUSES_PENDING_MESSAGE

    return False, None
