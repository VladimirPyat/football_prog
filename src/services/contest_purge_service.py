"""Hard-delete soft-deleted contests past retention window."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from config.settings import get_settings
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Contest, ContestRestoreSnapshot

logger = logging.getLogger(__name__)


async def list_purge_candidates(
    session: AsyncSession,
    *,
    before: datetime | None = None,
    include_all_deleted: bool = False,
) -> list[Contest]:
    """Contests with deleted_at set that are eligible for hard delete."""
    settings = get_settings()
    q = select(Contest).where(Contest.deleted_at.is_not(None))
    if not include_all_deleted:
        cutoff = before
        if cutoff is None:
            cutoff = datetime.now(UTC) - timedelta(seconds=settings.contest_purge_retention_seconds)
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=UTC)
        q = q.where(Contest.deleted_at <= cutoff)
    return list(await session.scalars(q.order_by(Contest.deleted_at)))


async def hard_delete_contest(session: AsyncSession, contest_id: int) -> bool:
    """Remove contest row and restore snapshot. Returns False if not soft-deleted."""
    contest = await session.get(Contest, contest_id)
    if contest is None or contest.deleted_at is None:
        return False

    await session.execute(
        delete(ContestRestoreSnapshot).where(ContestRestoreSnapshot.contest_id == contest_id)
    )
    await session.delete(contest)
    logger.info("contest hard-deleted contest_id=%s", contest_id)
    return True


async def purge_deleted_contests(
    session: AsyncSession,
    *,
    before: datetime | None = None,
    include_all_deleted: bool = False,
    dry_run: bool = False,
) -> list[int]:
    """Hard-delete eligible soft-deleted contests. Returns purged contest ids."""
    candidates = await list_purge_candidates(
        session, before=before, include_all_deleted=include_all_deleted
    )
    if dry_run:
        return [c.id for c in candidates]

    purged: list[int] = []
    for contest in candidates:
        if await hard_delete_contest(session, contest.id):
            purged.append(contest.id)
    return purged
