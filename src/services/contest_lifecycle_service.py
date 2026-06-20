"""Contest lifecycle guards, status machine, and safe delete."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.models import ContestLifecycleStatus, ContestSettings, Round, RoundStatus
from services.contest_teardown import reseed_contest_settings, wipe_contest_data


class ContestLockedError(Exception):
    """Raised when contest_settings is locked and mutation is forbidden."""


class GracePeriodError(Exception):
    """Raised when delete grace period has not elapsed since pause."""


class IllegalTransitionError(Exception):
    """Raised on invalid contest status transition."""


class ContestNotPausedError(Exception):
    """Raised when an operation requires PAUSED status."""


class ContestDeleteDisabledError(Exception):
    """Raised when contest delete is disabled in settings."""


async def get_contest_settings(session: AsyncSession) -> ContestSettings:
    settings = await session.scalar(select(ContestSettings).limit(1))
    if settings is None:
        raise ValueError("Contest settings not found in database")
    return settings


async def require_unlocked(session: AsyncSession) -> ContestSettings:
    settings = await get_contest_settings(session)
    if settings.is_locked:
        raise ContestLockedError("Contest settings are locked — no structural or rule changes allowed")
    return settings


async def assert_contest_running(session: AsyncSession) -> ContestSettings:
    settings = await get_contest_settings(session)
    if settings.status in {ContestLifecycleStatus.PAUSED, ContestLifecycleStatus.FINISHED}:
        raise PermissionError(
            f"Contest is {settings.status} — mutating operations are blocked"
        )
    return settings


async def ensure_running_on_first_activation(session: AsyncSession) -> ContestSettings:
    """After first round activation: DRAFT → RUNNING (is_locked already set by round_service)."""
    settings = await get_contest_settings(session)
    if settings.status == ContestLifecycleStatus.DRAFT:
        settings.status = ContestLifecycleStatus.RUNNING
    return settings


async def pause_contest(session: AsyncSession) -> ContestSettings:
    settings = await get_contest_settings(session)
    if settings.status != ContestLifecycleStatus.RUNNING:
        raise IllegalTransitionError(
            f"Cannot pause contest from status {settings.status} (must be RUNNING)"
        )
    settings.status = ContestLifecycleStatus.PAUSED
    settings.paused_at = datetime.now(timezone.utc)
    return settings


async def resume_contest(session: AsyncSession) -> ContestSettings:
    settings = await get_contest_settings(session)
    if settings.status != ContestLifecycleStatus.PAUSED:
        raise IllegalTransitionError(
            f"Cannot resume contest from status {settings.status} (must be PAUSED)"
        )
    settings.status = ContestLifecycleStatus.RUNNING
    settings.paused_at = None
    return settings


async def finish_contest(session: AsyncSession) -> ContestSettings:
    settings = await get_contest_settings(session)
    if settings.status == ContestLifecycleStatus.FINISHED:
        return settings
    if settings.status not in {ContestLifecycleStatus.RUNNING, ContestLifecycleStatus.PAUSED}:
        raise IllegalTransitionError(
            f"Cannot finish contest from status {settings.status} "
            "(must be RUNNING or PAUSED)"
        )
    now = datetime.now(timezone.utc)
    settings.status = ContestLifecycleStatus.FINISHED
    settings.finished_at = now

    active_rounds = (
        await session.scalars(
            select(Round).where(Round.status == RoundStatus.ACTIVE.value)
        )
    ).all()
    for round_ in active_rounds:
        round_.status = RoundStatus.CLOSED.value

    return settings


def compute_deletable_at(paused_at: datetime | None) -> datetime | None:
    if paused_at is None:
        return None
    grace = get_settings().contest_delete_grace_seconds
    return paused_at + timedelta(seconds=grace)


def seconds_until_deletable(paused_at: datetime | None) -> int | None:
    deletable_at = compute_deletable_at(paused_at)
    if deletable_at is None:
        return None
    remaining = (deletable_at - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(remaining))


async def assert_deletable(session: AsyncSession, *, instant: bool = False) -> ContestSettings:
    app_settings = get_settings()
    if not app_settings.contest_delete_enabled:
        raise ContestDeleteDisabledError("Contest delete is disabled")

    settings = await get_contest_settings(session)
    if settings.status != ContestLifecycleStatus.PAUSED:
        raise ContestNotPausedError(
            f"Contest must be PAUSED to delete (current status: {settings.status})"
        )

    if instant or app_settings.contest_allow_instant_delete:
        return settings

    if settings.paused_at is None:
        raise GracePeriodError("Pause timestamp missing — cannot verify grace period")

    deletable_at = compute_deletable_at(settings.paused_at)
    if deletable_at is None or datetime.now(timezone.utc) < deletable_at:
        remaining = seconds_until_deletable(settings.paused_at)
        raise GracePeriodError(
            f"Grace period not elapsed — {remaining}s remaining until deletable"
        )
    return settings


async def delete_contest_data(
    session: AsyncSession, *, keep_admin_users: bool = True
) -> ContestSettings:
    """FK-safe wipe and re-seed contest_settings to DRAFT."""
    await wipe_contest_data(session, keep_admin_users=keep_admin_users)
    return await reseed_contest_settings(session)


async def update_exceptional_tiebreak(
    session: AsyncSession, user_id: int, points: int
) -> int:
    """Set exceptional_tiebreak_points for a user (allowed even when locked)."""
    from database.models import User  # noqa: PLC0415

    if points < 0:
        raise ValueError("exceptional_tiebreak_points must be >= 0")

    user = await session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    user.exceptional_tiebreak_points = points
    return points
