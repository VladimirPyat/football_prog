"""Contest lifecycle guards, status machine, and safe delete."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from config.settings import get_settings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    ContestDeleteDisabledError,
    ContestLockedError,
    ContestNotPausedError,
    ContestRuleError,
    GracePeriodError,
    IllegalTransitionError,
    NotFoundError,
    ValidationError,
)
from database.models import (
    Contest,
    ContestLifecycleStatus,
    ContestParticipant,
    ParticipantStatus,
    Round,
    RoundStatus,
    Team,
)
from services.contest_restore_service import save_restore_snapshot
from services.contest_teardown import reset_contest_to_draft

logger = logging.getLogger(__name__)

MIN_ACCEPTED_PARTICIPANTS_FOR_START = 2


async def validate_contest_start_readiness(
    session: AsyncSession, contest: Contest
) -> None:
    """Ensure teams and participants satisfy prerequisites before start."""
    team_count = await session.scalar(
        select(func.count()).select_from(Team).where(Team.contest_id == contest.id)
    )
    team_count = team_count or 0
    if team_count != contest.total_teams:
        raise ValidationError(
            f"Для запуска нужно добавить все команды: создано {team_count} "
            f"из {contest.total_teams}"
        )

    accepted_count = await session.scalar(
        select(func.count())
        .select_from(ContestParticipant)
        .where(
            ContestParticipant.contest_id == contest.id,
            ContestParticipant.status == ParticipantStatus.ACCEPTED,
        )
    )
    accepted_count = accepted_count or 0
    if accepted_count < MIN_ACCEPTED_PARTICIPANTS_FOR_START:
        raise ValidationError(
            f"Для запуска нужно минимум {MIN_ACCEPTED_PARTICIPANTS_FOR_START} "
            f"участника со статусом «Принято» (сейчас: {accepted_count})"
        )


def _ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """Attach UTC tzinfo if the datetime is naive (e.g. returned by SQLite)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def get_contest(
    session: AsyncSession, contest_id: int, *, include_deleted: bool = False
) -> Contest:
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise NotFoundError(f"Конкурс {contest_id} не найден")
    if contest.deleted_at is not None and not include_deleted:
        raise NotFoundError(f"Конкурс {contest_id} не найден")
    return contest


async def get_contest_settings(session: AsyncSession) -> Contest:
    """Legacy helper: return the default (first) contest."""
    contest = await session.scalar(select(Contest).order_by(Contest.id).limit(1))
    if contest is None:
        raise NotFoundError("Конкурс не найден в базе данных")
    return contest


async def require_unlocked(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.is_locked:
        raise ContestLockedError(
            "Конкурс заблокирован — изменение правил и структуры запрещено"
        )
    return contest


async def assert_contest_running(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.PAUSED:
        raise ContestRuleError(
            "Конкурс приостановлен — операция недоступна",
            code="CONTEST_NOT_RUNNING",
        )
    if contest.status == ContestLifecycleStatus.FINISHED:
        raise ContestRuleError(
            "Конкурс завершён — операция недоступна",
            code="CONTEST_NOT_RUNNING",
        )
    return contest


async def purge_before_first_activation(session: AsyncSession, contest_id: int) -> int:
    """Remove unconfirmed participants while contest is still unlocked (before first activate)."""
    from services.contest_setup_service import purge_unconfirmed_participants  # noqa: PLC0415

    contest = await get_contest(session, contest_id)
    if contest.status != ContestLifecycleStatus.DRAFT:
        return 0
    return await purge_unconfirmed_participants(session, contest_id)


async def ensure_running_on_first_activation(
    session: AsyncSession, contest_id: int
) -> Contest:
    """After first round activation: DRAFT → RUNNING (is_locked set by round_service)."""
    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.DRAFT:
        contest.status = ContestLifecycleStatus.RUNNING
        logger.info("contest running on first activation contest_id=%s", contest_id)
    return contest


async def start_contest(session: AsyncSession, contest_id: int) -> Contest:
    """DRAFT → RUNNING + lock; purge unconfirmed participants."""
    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.RUNNING and contest.is_locked:
        return contest
    if contest.status == ContestLifecycleStatus.DRAFT and contest.is_locked:
        logger.warning(
            "contest inconsistent state DRAFT+locked; fixing forward to RUNNING contest_id=%s",
            contest_id,
        )
        await validate_contest_start_readiness(session, contest)
        await purge_before_first_activation(session, contest_id)
        contest.status = ContestLifecycleStatus.RUNNING
        logger.info("contest started (fix-forward) contest_id=%s", contest_id)
        return contest
    if contest.status != ContestLifecycleStatus.DRAFT:
        raise IllegalTransitionError(
            f"Недопустимый переход статуса: {contest.status} → RUNNING (требуется DRAFT)"
        )
    await validate_contest_start_readiness(session, contest)
    await purge_before_first_activation(session, contest_id)
    contest.is_locked = True
    contest.status = ContestLifecycleStatus.RUNNING
    logger.info("contest started contest_id=%s", contest_id)
    return contest


async def pause_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status != ContestLifecycleStatus.RUNNING:
        raise IllegalTransitionError(
            f"Недопустимый переход статуса: {contest.status} → PAUSED (требуется RUNNING)"
        )
    contest.status = ContestLifecycleStatus.PAUSED
    contest.paused_at = datetime.now(UTC)
    logger.info("contest paused contest_id=%s", contest_id)
    return contest


async def resume_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status != ContestLifecycleStatus.PAUSED:
        raise IllegalTransitionError(
            f"Недопустимый переход статуса: {contest.status} → RUNNING (требуется PAUSED)"
        )
    contest.status = ContestLifecycleStatus.RUNNING
    contest.paused_at = None
    logger.info("contest resumed contest_id=%s", contest_id)
    return contest


async def finish_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.FINISHED:
        return contest
    if contest.status not in {ContestLifecycleStatus.RUNNING, ContestLifecycleStatus.PAUSED}:
        raise IllegalTransitionError(
            f"Недопустимый переход статуса: {contest.status} → FINISHED "
            "(требуется RUNNING или PAUSED)"
        )
    now = datetime.now(UTC)
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

    logger.info("contest finished contest_id=%s", contest_id)
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
    remaining = (deletable_at - datetime.now(UTC)).total_seconds()
    return max(0, int(remaining))


async def assert_deletable(
    session: AsyncSession,
    contest_id: int,
    *,
    instant: bool = False,
    allow_draft: bool = False,
) -> Contest:
    app_settings = get_settings()
    if not app_settings.contest_delete_enabled:
        raise ContestDeleteDisabledError("Удаление конкурса отключено в настройках")

    contest = await get_contest(session, contest_id)
    if contest.status == ContestLifecycleStatus.DRAFT:
        if allow_draft:
            return contest
        raise ContestNotPausedError(
            f"Для удаления конкурс должен быть на паузе (текущий статус: {contest.status})"
        )
    if contest.status != ContestLifecycleStatus.PAUSED:
        raise ContestNotPausedError(
            f"Для удаления конкурс должен быть на паузе (текущий статус: {contest.status})"
        )

    if instant or app_settings.contest_allow_instant_delete:
        return contest

    paused_at = _ensure_utc_aware(contest.paused_at)
    if paused_at is None:
        raise GracePeriodError(
            "Не зафиксировано время паузы — невозможно проверить период ожидания"
        )

    deletable_at = compute_deletable_at(paused_at)
    if deletable_at is None or datetime.now(UTC) < deletable_at:
        remaining = seconds_until_deletable(paused_at)
        raise GracePeriodError(
            f"Период ожидания после паузы ещё не истёк — осталось {remaining} с"
        )
    return contest


async def delete_contest_data(
    session: AsyncSession,
    contest_id: int,
    *,
    keep_admin_users: bool = True,
    deleted_by_user_id: int | None = None,
) -> Contest:
    """Soft-delete: snapshot, wipe operational data, set deleted_at (hidden from lists)."""
    del keep_admin_users
    contest = await get_contest(session, contest_id, include_deleted=True)
    if contest.deleted_at is not None:
        raise ValidationError("Конкурс уже удалён")

    await save_restore_snapshot(session, contest_id, deleted_by_user_id=deleted_by_user_id)
    contest = await reset_contest_to_draft(session, contest_id)
    contest.deleted_at = datetime.now(UTC)
    logger.info("contest soft-deleted contest_id=%s", contest_id)
    return contest


async def update_exceptional_tiebreak(
    session: AsyncSession, contest_id: int, user_id: int, points: int
) -> int:
    """Set exceptional_tiebreak_points for a contest participant (allowed when locked)."""
    from database.models import ContestParticipant  # noqa: PLC0415

    if points < 0:
        raise ValidationError("Очки исключительного тай-брейка должны быть >= 0")

    participant = await session.get(ContestParticipant, (contest_id, user_id))
    if participant is None:
        raise NotFoundError(
            f"Участник {user_id} не найден в конкурсе {contest_id}"
        )

    participant.exceptional_tiebreak_points = points
    return points
