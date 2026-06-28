"""Admin round management endpoints (legacy 1.3 shims)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select

from api.deps import DbSession, RoleChecker, resolve_default_contest_id
from core.exceptions import NotFoundError, ValidationError
from database.models import Contest, Match, MatchStatus, Round, RoundStatus, UserRole
from schemas.admin import CreateRoundRequest, RoundActionResponse, UpdateRoundRequest
from services.contest_lifecycle_service import (
    assert_contest_running,
    ensure_running_on_first_activation,
    purge_before_first_activation,
)
from services.round_service import (
    close_round,
    get_deadline_min_before_match_minutes,
    set_deadline,
    transition_round,
    validate_round_deadline_placement,
)
from services.scoring_persistence import calculate_round

router = APIRouter(prefix="/admin/rounds", tags=["legacy (deprecated)", "admin (supervisor)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))


@router.post("", dependencies=[_supervisor], deprecated=True)
async def create_round(body: CreateRoundRequest, session: DbSession) -> dict:
    """Создать тур. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise NotFoundError(f"Конкурс {contest_id} не найден")

    if len(body.matches) > contest.matches_per_round:
        raise ValidationError(
            f"Слишком много матчей: максимум {contest.matches_per_round}"
        )

    team_ids_in_round: set[int] = set()
    for m in body.matches:
        if m.team1_id == m.team2_id:
            raise ValidationError("Команды home и away должны различаться")
        if m.team1_id in team_ids_in_round or m.team2_id in team_ids_in_round:
            raise ValidationError("Команда не может играть дважды в одном туре")
        team_ids_in_round.add(m.team1_id)
        team_ids_in_round.add(m.team2_id)

    deadline_rule = contest.rules_json["contest_structure"]["deadline_rule_hours"]
    earliest = min(m.date_time for m in body.matches)
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=UTC)
    dl = body.deadline if body.deadline.tzinfo else body.deadline.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    for m in body.matches:
        dt_check = m.date_time if m.date_time.tzinfo else m.date_time.replace(tzinfo=UTC)
        if dt_check < now:
            raise ValidationError("Дата матча не может быть в прошлом")
    _ = deadline_rule  # rule_hours retained for future warnings; placement rule does not use it
    validate_round_deadline_placement(
        dl,
        earliest,
        now=now,
        min_before_match_minutes=get_deadline_min_before_match_minutes(contest.rules_json),
    )

    existing = await session.scalar(
        select(Round).where(Round.contest_id == contest_id, Round.number == body.number)
    )
    if existing:
        raise ValidationError(f"Тур с номером {body.number} уже существует")

    round_ = Round(
        contest_id=contest_id,
        number=body.number,
        deadline=dl,
        status=RoundStatus.DRAFT,
        matches_count=len(body.matches),
    )
    session.add(round_)
    await session.flush()

    for m in body.matches:
        dt = m.date_time if m.date_time.tzinfo else m.date_time.replace(tzinfo=UTC)
        session.add(
            Match(
                round_id=round_.id,
                team1_id=m.team1_id,
                team2_id=m.team2_id,
                date_time=dt,
                status=MatchStatus.SCHEDULED,
            )
        )

    await session.commit()
    return {"round_id": round_.id, "status": round_.status}


@router.patch("/{round_id}", dependencies=[_supervisor], deprecated=True)
async def update_round(round_id: int, body: UpdateRoundRequest, session: DbSession) -> dict:
    """Обновить тур. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не найден")
    if round_.status not in {RoundStatus.DRAFT, RoundStatus.ACTIVE}:
        raise ValidationError("Редактировать можно только тур в статусе Черновик или Активен")

    now = datetime.now(UTC)

    if body.deadline is not None:
        await set_deadline(session, round_id, body.deadline)

    if body.matches:
        deadline_passed = False
        if round_.status == RoundStatus.ACTIVE:
            current_deadline = round_.deadline
            if current_deadline.tzinfo is None:
                current_deadline = current_deadline.replace(tzinfo=UTC)
            deadline_passed = now >= current_deadline

        for item in body.matches:
            if item.match_id is None:
                continue
            match = await session.get(Match, item.match_id)
            if match is None or match.round_id != round_id:
                raise NotFoundError(f"Матч {item.match_id} не найден")
            if deadline_passed and (item.team1_id is not None or item.team2_id is not None):
                raise ValidationError("После дедлайна нельзя менять состав матчей")
            if item.team1_id is not None:
                match.team1_id = item.team1_id
            if item.team2_id is not None:
                match.team2_id = item.team2_id
            if item.date_time is not None:
                match.date_time = item.date_time
            if item.status is not None:
                match.status = item.status

    await session.commit()
    return {"success": True}


@router.post("/{round_id}/activate", dependencies=[_supervisor], deprecated=True)
async def activate_round(round_id: int, session: DbSession) -> dict:
    """Активировать тур. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    # No-op when contest already RUNNING (purge runs on POST /start or legacy first activate).
    await purge_before_first_activation(session, contest_id)
    round_ = await transition_round(session, round_id, RoundStatus.ACTIVE)
    await ensure_running_on_first_activation(session, contest_id)
    await session.commit()
    return {"success": True, "status": round_.status}


@router.post("/{round_id}/close", dependencies=[_supervisor], deprecated=True)
async def close_round_endpoint(round_id: int, session: DbSession) -> dict:
    """Закрыть тур. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    round_ = await close_round(session, contest_id, round_id)
    await session.commit()
    return {"round_id": round_.id, "status": round_.status}


@router.post("/{round_id}/calculate", response_model=RoundActionResponse, dependencies=[_supervisor], deprecated=True)
async def calculate(round_id: int, session: DbSession) -> RoundActionResponse:
    """Рассчитать тур. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    count = await calculate_round(session, round_id, contest_id)
    await session.commit()
    return RoundActionResponse(round_id=round_id, status=RoundStatus.CALCULATED, users_scored=count)


@router.post("/{round_id}/publish", dependencies=[_supervisor], deprecated=True)
async def publish_round(round_id: int, session: DbSession) -> dict:
    """Опубликовать тур. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    round_ = await transition_round(session, round_id, RoundStatus.PUBLISHED)
    await session.commit()
    return {"success": True, "status": round_.status}
