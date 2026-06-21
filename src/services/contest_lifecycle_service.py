"""Contest lifecycle guards, status machine, and safe delete."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.models import Contest, ContestLifecycleStatus, Round, RoundStatus
from services.contest_teardown import reset_contest_to_draft


def _ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """Attach UTC tzinfo if the datetime is naive (e.g. returned by SQLite)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ContestLockedError(Exception):
    """Raised when contest is locked and mutation is forbidden."""


class GracePeriodError(Exception):
    """Raised when delete grace period has not elapsed since pause."""


class IllegalTransitionError(Exception):
    """Raised on invalid contest status transition."""


class ContestNotPausedError(Exception):
    """Raised when an operation requires PAUSED status."""


class ContestDeleteDisabledError(Exception):
    """Raised when contest delete is disabled in settings."""


async def get_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise ValueError(f"Contest {contest_id} not found")
    return contest


async def get_contest_settings(session: AsyncSession) -> Contest:
    """Legacy helper: return the default (first) contest."""
    contest = await session.scalar(select(Contest).order_by(Contest.id).limit(1))
    if contest is None:
        raise ValueError("Contest not found in database")
    return contest


async def require_unlocked(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.is_locked:
        raise ContestLockedError(
            "Contest is locked — no structural or rule changes allowed"
        )
    return contest


async def assert_contest_running(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status in {ContestLifecycleStatus.PAUSED, ContestLifecycleStatus.FINISHED}:
        raise PermissionError(
            f"Contest is {contest.status} — mutating operations are blocked"
        )
    return contest


async def ensure_running_on_first_activation(
    session: AsyncSession, contest_id: int
) -> Contest:
    """After first round activation: DRAFT → RUNNING (is_locked set by round_service)."""
    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.DRAFT:
        contest.status = ContestLifecycleStatus.RUNNING
    return contest


async def pause_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status != ContestLifecycleStatus.RUNNING:
        raise IllegalTransitionError(
            f"Cannot pause contest from status {contest.status} (must be RUNNING)"
        )
    contest.status = ContestLifecycleStatus.PAUSED
    contest.paused_at = datetime.now(timezone.utc)
    return contest


async def resume_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status != ContestLifecycleStatus.PAUSED:
        raise IllegalTransitionError(
            f"Cannot resume contest from status {contest.status} (must be PAUSED)"
        )
    contest.status = ContestLifecycleStatus.RUNNING
    contest.paused_at = None
    return contest


async def finish_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.FINISHED:
        return contest
    if contest.status not in {ContestLifecycleStatus.RUNNING, ContestLifecycleStatus.PAUSED}:
        raise IllegalTransitionError(
            f"Cannot finish contest from status {contest.status} "
            "(must be RUNNING or PAUSED)"
        )
    now = datetime.now(timezone.utc)
    contest.status = ContestLifecycleStatus.FINISHED
    contest.finished_at = now

    active_rounds = (
        await session.scalars(
            select(Round).where(
                Round.contest_id == contest_id,
                Round.status == RoundStatus.ACTIVE.value,
            )
        )
    ).all()
    for round_ in active_rounds:
        round_.status = RoundStatus.CLOSED.value

    return contest


def compute_deletable_at(paused_at: datetime | None) -> datetime | None:
    paused_at = _ensure_utc_aware(paused_at)
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


async def assert_deletable(
    session: AsyncSession, contest_id: int, *, instant: bool = False
) -> Contest:
    app_settings = get_settings()
    if not app_settings.contest_delete_enabled:
        raise ContestDeleteDisabledError("Contest delete is disabled")

    contest = await get_contest(session, contest_id)
    if contest.status != ContestLifecycleStatus.PAUSED:
        raise ContestNotPausedError(
            f"Contest must be PAUSED to delete (current status: {contest.status})"
        )

    if instant or app_settings.contest_allow_instant_delete:
        return contest

    paused_at = _ensure_utc_aware(contest.paused_at)
    if paused_at is None:
        raise GracePeriodError("Pause timestamp missing — cannot verify grace period")

    deletable_at = compute_deletable_at(paused_at)
    if deletable_at is None or datetime.now(timezone.utc) < deletable_at:
        remaining = seconds_until_deletable(paused_at)
        raise GracePeriodError(
            f"Grace period not elapsed — {remaining}s remaining until deletable"
        )
    return contest


async def delete_contest_data(
    session: AsyncSession, contest_id: int, *, keep_admin_users: bool = True
) -> Contest:
    """FK-safe wipe and reset contest to DRAFT."""
    return await reset_contest_to_draft(session, contest_id)


async def update_exceptional_tiebreak(
    session: AsyncSession, contest_id: int, user_id: int, points: int
) -> int:
    """Set exceptional_tiebreak_points for a contest participant (allowed when locked)."""
    from database.models import ContestParticipant  # noqa: PLC0415

    if points < 0:
        raise ValueError("exceptional_tiebreak_points must be >= 0")

    participant = await session.get(ContestParticipant, (contest_id, user_id))
    if participant is None:
        raise ValueError(f"Participant user {user_id} not found in contest {contest_id}")

    participant.exceptional_tiebreak_points = points
    return points
