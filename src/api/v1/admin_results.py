"""Admin match result and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import DbSession, RoleChecker
from database.models import MatchStatus, RoundStatus, UserRole
from schemas.admin import MatchResultRequest, MatchResultResponse, MatchStatusPatch, MatchStatusResponse
from services.contest_lifecycle_service import assert_contest_running
from services.match_service import change_status, set_result

router = APIRouter(prefix="/admin/matches", tags=["admin (supervisor)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))


@router.put("/{match_id}/result", response_model=MatchResultResponse, dependencies=[_supervisor])
async def apply_result(match_id: int, body: MatchResultRequest, session: DbSession) -> MatchResultResponse:
    await assert_contest_running(session)
    try:
        match = await set_result(session, match_id, body.score1, body.score2)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MatchResultResponse(round_id=match.round_id)


@router.patch("/{match_id}/status", response_model=MatchStatusResponse, dependencies=[_supervisor])
async def patch_status(match_id: int, body: MatchStatusPatch, session: DbSession) -> MatchStatusResponse:
    await assert_contest_running(session)
    from database.models import Match, Round  # noqa: PLC0415

    match = await session.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Match not found")

    round_ = await session.get(Round, match.round_id)
    was_calculated = round_ is not None and round_.status == RoundStatus.CALCULATED

    try:
        new_status = MatchStatus(body.status)
        await change_status(session, match_id, new_status)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    recalc = was_calculated and body.status == MatchStatus.VOID
    return MatchStatusResponse(recalculation_triggered=recalc)
