"""Public leaderboard/results and admin recalculate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from api.deps import DbSession, RoleChecker, cache_control_header
from database.models import Round, RoundStatus, UserRole
from schemas.leaderboard import LeaderboardOut, RoundResultsOut
from services.leaderboard_service import compute_etag, get_global_leaderboard, get_round_leaderboard, get_round_results
from services.scoring_persistence import recalculate_round

router = APIRouter(tags=["rounds (public)", "admin (system)"])

_admin = Depends(RoleChecker(UserRole.ADMIN))


@router.get("/leaderboard", response_model=LeaderboardOut)
async def global_leaderboard(session: DbSession, response: Response) -> LeaderboardOut:
    try:
        data = await get_global_leaderboard(session)
        etag = await compute_etag(session)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return LeaderboardOut(**data)


@router.get("/rounds/{round_id}/leaderboard", response_model=LeaderboardOut)
async def round_leaderboard(round_id: int, session: DbSession, response: Response) -> LeaderboardOut:
    try:
        data = await get_round_leaderboard(session, round_id)
        etag = await compute_etag(session, round_id=round_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return LeaderboardOut(**data)


@router.get("/rounds/{round_id}/results", response_model=RoundResultsOut)
async def round_results(round_id: int, session: DbSession, response: Response) -> RoundResultsOut:
    try:
        data = await get_round_results(session, round_id)
        etag = await compute_etag(session, round_id=round_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return RoundResultsOut(**data)


@router.post("/admin/recalculate", dependencies=[_admin])
async def admin_recalculate(session: DbSession) -> dict:
    rounds = (
        await session.scalars(
            select(Round).where(Round.status == RoundStatus.CALCULATED)
        )
    ).all()
    count = 0
    for round_ in rounds:
        await recalculate_round(session, round_.id)
        count += 1
    await session.commit()
    return {"recalculated_rounds": count}
