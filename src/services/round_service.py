"""Round status machine, deadline management, close, and free tour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    ContestRuleError,
    IllegalTransitionError,
    NotFoundError,
    ValidationError,
)
from database.models import Contest, Match, MatchStatus, Round, RoundStatus

_VALID_TRANSITIONS: dict[RoundStatus, set[RoundStatus]] = {
    RoundStatus.DRAFT: {RoundStatus.ACTIVE},
    RoundStatus.ACTIVE: {RoundStatus.CLOSED},
    RoundStatus.CLOSED: {RoundStatus.CALCULATED},
    RoundStatus.CALCULATED: {RoundStatus.PUBLISHED},
    RoundStatus.PUBLISHED: set(),
}


async def _get_round(session: AsyncSession, round_id: int) -> Round:
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise NotFoundError(f"Тур {round_id} не найден")
    return round_


async def _get_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise NotFoundError(f"Конкурс {contest_id} не найден")
    return contest


async def _earliest_match_dt(session: AsyncSession, round_id: int) -> datetime:
    matches = (await session.scalars(select(Match).where(Match.round_id == round_id))).all()
    if not matches:
        raise NotFoundError(f"Матчи для тура {round_id} не найдены")
    return min(m.date_time for m in matches)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def validate_round_deadline_placement(
    deadline: datetime,
    earliest_match: datetime,
    *,
    now: datetime | None = None,
) -> None:
    """Deadline must be in the future and strictly before the first match kickoff."""
    deadline = _ensure_utc(deadline)
    earliest_match = _ensure_utc(earliest_match)
    now = _ensure_utc(now or datetime.now(UTC))

    if deadline >= earliest_match:
        raise ValidationError("Дедлайн должен быть раньше первого матча тура")
    if deadline <= now:
        raise ValidationError("Дедлайн должен быть в будущем")


def assert_deadline_change_allowed(
    current_deadline: datetime,
    deadline_rule_hours: int,
    *,
    now: datetime | None = None,
) -> None:
    """24h rule: supervisor may change deadline only while now <= current_deadline - N hours."""
    current_deadline = _ensure_utc(current_deadline)
    now = _ensure_utc(now or datetime.now(UTC))
    change_cutoff = current_deadline - timedelta(hours=deadline_rule_hours)
    if now > change_cutoff:
        raise ContestRuleError(
            "Окно изменения дедлайна закрыто",
            code="DEADLINE_CHANGE_CLOSED",
        )


async def transition_round(
    session: AsyncSession, round_id: int, target_status: RoundStatus
) -> Round:
    """Apply a status transition to the round."""
    round_ = await _get_round(session, round_id)
    current = RoundStatus(round_.status)
    allowed = _VALID_TRANSITIONS.get(current, set())

    if target_status not in allowed:
        raise IllegalTransitionError(
            f"Недопустимый переход статуса тура: {current} → {target_status}"
        )

    if target_status == RoundStatus.ACTIVE:
        contest = await _get_contest(session, round_.contest_id)
        contest.is_locked = True

    round_.status = target_status
    return round_


async def set_deadline(
    session: AsyncSession, round_id: int, new_deadline: datetime
) -> Round:
    """Update the round deadline, enforcing 24h lockout and placement rules.

    New policy (2026-06-27):
    - 24h rule applies to CHANGING the deadline, not to match kickoff distance.
    - Lockout: supervisor may change deadline only while now <= current_deadline - rule_hours.
    - Placement: new_deadline must be: now < new_deadline < earliest_match.
    """
    if new_deadline.tzinfo is None:
        raise ValidationError("Дедлайн должен содержать информацию о часовом поясе")

    round_ = await _get_round(session, round_id)
    contest = await _get_contest(session, round_.contest_id)
    deadline_rule_hours: int = contest.rules_json["contest_structure"]["deadline_rule_hours"]

    earliest = await _earliest_match_dt(session, round_id)
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=UTC)

    now = datetime.now(UTC)

    if RoundStatus(round_.status) == RoundStatus.ACTIVE:
        assert_deadline_change_allowed(round_.deadline, deadline_rule_hours, now=now)

    validate_round_deadline_placement(new_deadline, earliest, now=now)

    round_.deadline = new_deadline
    return round_


async def close_round(session: AsyncSession, contest_id: int, round_id: int) -> Round:
    """Transition ACTIVE → CLOSED when now >= deadline."""
    round_ = await _get_round(session, round_id)
    if round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не принадлежит конкурсу {contest_id}")
    if round_.status == RoundStatus.CLOSED.value:
        return round_

    if round_.status != RoundStatus.ACTIVE.value:
        raise ContestRuleError(
            f"Закрыть можно только активный тур (текущий статус: {round_.status})",
            code="ROUND_NOT_ACTIVE",
        )

    deadline = round_.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if now < deadline:
        raise ValidationError("Дедлайн тура ещё не наступил")

    return await transition_round(session, round_id, RoundStatus.CLOSED)


async def create_free_tour(
    session: AsyncSession,
    contest_id: int,
    matches: list[dict],
    deadline: datetime,
) -> Round:
    """Move POSTPONED matches into a new DRAFT round."""
    if deadline.tzinfo is None:
        raise ValidationError("Дедлайн должен содержать информацию о часовом поясе")

    contest = await _get_contest(session, contest_id)
    max_number = await session.scalar(
        select(func.max(Round.number)).where(Round.contest_id == contest_id)
    )
    new_number = (max_number or 0) + 1

    new_round = Round(
        contest_id=contest_id,
        number=new_number,
        deadline=deadline,
        status=RoundStatus.DRAFT,
        matches_count=len(matches),
    )
    session.add(new_round)
    await session.flush()

    source_round_counts: dict[int, int] = {}

    for item in matches:
        match_id = item["match_id"]
        new_date_time = item["new_date_time"]
        if new_date_time.tzinfo is None:
            new_date_time = new_date_time.replace(tzinfo=UTC)

        match = await session.get(Match, match_id)
        if match is None:
            raise NotFoundError(f"Матч {match_id} не найден")

        source_round = await session.get(Round, match.round_id)
        if source_round is None or source_round.contest_id != contest_id:
            raise NotFoundError(f"Матч {match_id} не принадлежит конкурсу {contest_id}")
        if match.status != MatchStatus.POSTPONED.value:
            raise ValidationError(
                f"Матч {match_id} должен быть в статусе POSTPONED (текущий: {match.status})"
            )

        source_round_counts[match.round_id] = source_round_counts.get(match.round_id, 0) + 1
        match.round_id = new_round.id
        match.date_time = new_date_time
        match.status = MatchStatus.SCHEDULED

    for source_round_id, moved_count in source_round_counts.items():
        source_round = await session.get(Round, source_round_id)
        if source_round is not None:
            source_round.matches_count = max(0, source_round.matches_count - moved_count)

    contest.total_rounds = max(contest.total_rounds, new_number)
    return new_round
