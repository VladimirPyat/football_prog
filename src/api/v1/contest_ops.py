"""Contest-scoped operational endpoints: rounds, predictions, admin, leaderboard."""

from __future__ import annotations

from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from api.deps import (
    ContestContext,
    CurrentUser,
    DbSession,
    RoleChecker,
    cache_control_header,
)
from api.handlers.leaderboard import (
    get_global_leaderboard_response,
    get_round_leaderboard_response,
    get_round_results_response,
)
from api.handlers.predictions import build_round_predictions_view
from core.exceptions import NotFoundError, ValidationError
from database.models import Contest, Match, MatchStatus, Round, RoundStatus, UserRole
from schemas.admin import (
    CreateRoundRequest,
    MatchResultRequest,
    MatchResultResponse,
    MatchStatusPatch,
    MatchStatusResponse,
    RoundActionResponse,
    UpdateRoundRequest,
)
from schemas.contest import FreeTourRequest
from schemas.leaderboard import LeaderboardOut, RoundResultsOut
from schemas.predictions import PredictionBatchRequest, PredictionBatchResponse, RoundPredictionsView
from schemas.rounds import RoundOut
from services.contest_lifecycle_service import assert_contest_running, ensure_running_on_first_activation
from services.leaderboard_service import compute_etag
from services.match_service import change_status, set_result
from services.prediction_service import submit_batch
from services.round_service import close_round, create_free_tour, set_deadline, transition_round
from services.scoring_persistence import calculate_round, recalculate_contest

router = APIRouter(prefix="/contests/{contest_id}", tags=["contest operations"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))
_admin = Depends(RoleChecker(UserRole.ADMIN))


@router.get("/rounds", response_model=list[RoundOut])
async def list_rounds(
    contest_id: int, session: DbSession, _contest: ContestContext
) -> list[RoundOut]:
    """Список туров конкурса (публичный)."""
    rounds = (
        await session.scalars(
            select(Round).where(Round.contest_id == contest_id).order_by(Round.number)
        )
    ).all()
    return [RoundOut.model_validate(r) for r in rounds]


@router.get("/rounds/{round_id}/predictions", response_model=RoundPredictionsView)
async def get_predictions(
    contest_id: int,
    round_id: int,
    session: DbSession,
    user: CurrentUser,
    _contest: ContestContext,
) -> RoundPredictionsView:
    """Прогнозы тура с учётом дедлайна и прав видимости.

    Args:
        contest_id: идентификатор конкурса
        round_id: идентификатор тура
    """
    return await build_round_predictions_view(session, contest_id, round_id, user)


@router.post("/rounds/{round_id}/predictions", response_model=PredictionBatchResponse)
async def post_predictions(
    contest_id: int,
    round_id: int,
    body: PredictionBatchRequest,
    session: DbSession,
    user: CurrentUser,
    _contest: ContestContext,
) -> PredictionBatchResponse:
    """Сохранить пакет прогнозов пользователя на тур.

    Args:
        contest_id: идентификатор конкурса
        round_id: идентификатор тура
        body: пакет прогнозов (все матчи обязательны)
    """
    await assert_contest_running(session, contest_id)
    items = [(p.match_id, p.score1, p.score2) for p in body.predictions]
    count = await submit_batch(session, contest_id, user.id, round_id, items)
    await session.commit()
    return PredictionBatchResponse(saved_count=count)


@router.get("/rounds/{round_id}/leaderboard", response_model=LeaderboardOut)
async def round_leaderboard(
    contest_id: int, round_id: int, session: DbSession, response: Response, _contest: ContestContext
) -> LeaderboardOut:
    """Таблица лидеров тура (публичный, с кэшированием)."""
    out = await get_round_leaderboard_response(session, contest_id, round_id)
    etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return out


@router.get("/rounds/{round_id}/results", response_model=RoundResultsOut)
async def round_results(
    contest_id: int, round_id: int, session: DbSession, response: Response, _contest: ContestContext
) -> RoundResultsOut:
    """Результаты матчей и очки участников тура."""
    out = await get_round_results_response(session, contest_id, round_id)
    etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return out


@router.get("/leaderboard", response_model=LeaderboardOut)
async def global_leaderboard(
    contest_id: int, session: DbSession, response: Response, _contest: ContestContext
) -> LeaderboardOut:
    """Общая таблица лидеров конкурса (публичный, с кэшированием)."""
    out = await get_global_leaderboard_response(session, contest_id)
    etag = await compute_etag(session, contest_id=contest_id)
    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return out


@router.post("/admin/rounds", dependencies=[_supervisor])
async def create_round(
    contest_id: int, body: CreateRoundRequest, session: DbSession, _contest: ContestContext
) -> dict:
    """Создать тур с матчами (SUPERVISOR+).

    Args:
        contest_id: идентификатор конкурса
        body: номер тура, дедлайн, список матчей
    """
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
        earliest = earliest.replace(tzinfo=timezone.utc)
    cutoff = earliest - timedelta(hours=deadline_rule)
    dl = body.deadline if body.deadline.tzinfo else body.deadline.replace(tzinfo=timezone.utc)
    if dl >= cutoff:
        raise ValidationError("Дедлайн нарушает правило 24 часов до первого матча")

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
        dt = m.date_time if m.date_time.tzinfo else m.date_time.replace(tzinfo=timezone.utc)
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


@router.patch("/admin/rounds/{round_id}", dependencies=[_supervisor])
async def update_round(
    contest_id: int,
    round_id: int,
    body: UpdateRoundRequest,
    session: DbSession,
    _contest: ContestContext,
) -> dict:
    """Обновить дедлайн или матчи активного тура.

    Args:
        contest_id: идентификатор конкурса
        round_id: идентификатор тура
        body: новый дедлайн и/или матчи
    """
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не найден")
    if round_.status != RoundStatus.ACTIVE:
        raise ValidationError("Редактировать можно только активный тур")

    if body.deadline is not None:
        await set_deadline(session, round_id, body.deadline)

    if body.matches:
        for item in body.matches:
            if item.match_id is None:
                continue
            match = await session.get(Match, item.match_id)
            if match is None or match.round_id != round_id:
                raise NotFoundError(f"Матч {item.match_id} не найден")
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


@router.post("/admin/rounds/{round_id}/activate", dependencies=[_supervisor])
async def activate_round(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    """Активировать тур (DRAFT → ACTIVE); при первой активации конкурс → RUNNING."""
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не найден")
    round_ = await transition_round(session, round_id, RoundStatus.ACTIVE)
    await ensure_running_on_first_activation(session, contest_id)
    await session.commit()
    return {"success": True, "status": round_.status}


@router.post("/admin/rounds/{round_id}/close", dependencies=[_supervisor])
async def close_round_endpoint(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    """Закрыть тур вручную (ACTIVE → CLOSED после дедлайна)."""
    await assert_contest_running(session, contest_id)
    round_ = await close_round(session, contest_id, round_id)
    await session.commit()
    return {"round_id": round_.id, "status": round_.status}


@router.post("/admin/rounds/{round_id}/calculate", response_model=RoundActionResponse, dependencies=[_supervisor])
async def calculate(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> RoundActionResponse:
    """Рассчитать очки тура (CLOSED → CALCULATED)."""
    await assert_contest_running(session, contest_id)
    count = await calculate_round(session, round_id, contest_id)
    await session.commit()
    return RoundActionResponse(round_id=round_id, status=RoundStatus.CALCULATED, users_scored=count)


@router.post("/admin/rounds/{round_id}/publish", dependencies=[_supervisor])
async def publish_round(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    """Опубликовать результаты тура (CALCULATED → PUBLISHED)."""
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не найден")
    round_ = await transition_round(session, round_id, RoundStatus.PUBLISHED)
    await session.commit()
    return {"success": True, "status": round_.status}


@router.post("/admin/rounds/free-tour", dependencies=[_supervisor])
async def free_tour(
    contest_id: int, body: FreeTourRequest, session: DbSession, _contest: ContestContext
) -> dict:
    """Создать free tour: перенести POSTPONED-матчи в новый тур.

    Args:
        contest_id: идентификатор конкурса
        body: дедлайн и список матчей с новыми датами
    """
    await assert_contest_running(session, contest_id)
    new_round = await create_free_tour(
        session,
        contest_id,
        [{"match_id": m.match_id, "new_date_time": m.new_date_time} for m in body.matches],
        body.deadline,
    )
    await session.commit()
    return {"round_id": new_round.id, "round_number": new_round.number}


@router.put("/admin/matches/{match_id}/result", response_model=MatchResultResponse, dependencies=[_supervisor])
async def apply_result(
    contest_id: int,
    match_id: int,
    body: MatchResultRequest,
    session: DbSession,
    _contest: ContestContext,
) -> MatchResultResponse:
    """Внести результат матча (после дедлайна, тур CLOSED).

    Args:
        contest_id: идентификатор конкурса
        match_id: идентификатор матча
        body: счёт матча
    """
    match = await set_result(session, contest_id, match_id, body.score1, body.score2)
    await session.commit()
    return MatchResultResponse(round_id=match.round_id)


@router.patch("/admin/matches/{match_id}/status", response_model=MatchStatusResponse, dependencies=[_supervisor])
async def patch_status(
    contest_id: int,
    match_id: int,
    body: MatchStatusPatch,
    session: DbSession,
    _contest: ContestContext,
) -> MatchStatusResponse:
    """Изменить статус матча (VOID / POSTPONED / CANCELED).

    Args:
        contest_id: идентификатор конкурса
        match_id: идентификатор матча
        body: новый статус
    """
    await assert_contest_running(session, contest_id)
    match = await session.get(Match, match_id)
    if match is None:
        raise NotFoundError(f"Матч {match_id} не найден")

    round_ = await session.get(Round, match.round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Матч {match_id} не найден")

    was_calculated = RoundStatus(round_.status) == RoundStatus.CALCULATED
    new_status = MatchStatus(body.status)
    await change_status(session, contest_id, match_id, new_status)
    await session.commit()

    recalc = was_calculated and body.status == MatchStatus.VOID
    return MatchStatusResponse(recalculation_triggered=recalc)


@router.post("/admin/recalculate", dependencies=[_admin])
async def admin_recalculate(
    contest_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    """Пересчитать все CALCULATED-туры конкурса (ADMIN)."""
    count = await recalculate_contest(session, contest_id)
    await session.commit()
    return {"recalculated_rounds": count}
