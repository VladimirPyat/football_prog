"""Admin match result and status endpoints (legacy 1.3 shims)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import DbSession, RoleChecker, resolve_default_contest_id
from core.exceptions import NotFoundError
from database.models import Match, MatchStatus, Round, RoundStatus, UserRole
from schemas.admin import (
    MatchResultRequest,
    MatchResultResponse,
    MatchStatusPatch,
    MatchStatusResponse,
)
from services.contest_lifecycle_service import assert_contest_running
from services.match_service import change_status, set_result

router = APIRouter(prefix="/admin/matches", tags=["legacy (deprecated)", "admin (supervisor)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.SUPPORT))


@router.put("/{match_id}/result", response_model=MatchResultResponse, dependencies=[_supervisor], deprecated=True)
async def apply_result(match_id: int, body: MatchResultRequest, session: DbSession) -> MatchResultResponse:
    """Внести результат матча. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    match = await set_result(session, contest_id, match_id, body.score1, body.score2)
    await session.commit()
    return MatchResultResponse(round_id=match.round_id)


@router.patch("/{match_id}/status", response_model=MatchStatusResponse, dependencies=[_supervisor], deprecated=True)
async def patch_status(match_id: int, body: MatchStatusPatch, session: DbSession) -> MatchStatusResponse:
    """Изменить статус матча. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
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
