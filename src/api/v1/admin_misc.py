"""Public leaderboard/results and admin recalculate (legacy 1.3 shims)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.deps import DbSession, RoleChecker, cache_control_header, resolve_default_contest_id
from database.models import UserRole
from schemas.leaderboard import LeaderboardOut, RoundResultsOut
from services.leaderboard_service import compute_etag, get_global_leaderboard, get_round_leaderboard, get_round_results
from services.scoring_persistence import recalculate_contest

router = APIRouter(tags=["legacy (deprecated)", "rounds (public)", "admin (system)"])

_admin = Depends(RoleChecker(UserRole.ADMIN))


@router.get("/leaderboard", response_model=LeaderboardOut, deprecated=True)
async def global_leaderboard(session: DbSession, response: Response) -> LeaderboardOut:
    contest_id = await resolve_default_contest_id(session)
    try:
        data = await get_global_leaderboard(session, contest_id)
        etag = await compute_etag(session, contest_id=contest_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return LeaderboardOut(**data)


@router.get("/rounds/{round_id}/leaderboard", response_model=LeaderboardOut, deprecated=True)
async def round_leaderboard(round_id: int, session: DbSession, response: Response) -> LeaderboardOut:
    contest_id = await resolve_default_contest_id(session)
    try:
        data = await get_round_leaderboard(session, contest_id, round_id)
        etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return LeaderboardOut(**data)


@router.get("/rounds/{round_id}/results", response_model=RoundResultsOut, deprecated=True)
async def round_results(round_id: int, session: DbSession, response: Response) -> RoundResultsOut:
    contest_id = await resolve_default_contest_id(session)
    try:
        data = await get_round_results(session, contest_id, round_id)
        etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return RoundResultsOut(**data)


@router.post("/admin/recalculate", dependencies=[_admin], deprecated=True)
async def admin_recalculate(session: DbSession) -> dict:
    contest_id = await resolve_default_contest_id(session)
    count = await recalculate_contest(session, contest_id)
    await session.commit()
    return {"recalculated_rounds": count}
