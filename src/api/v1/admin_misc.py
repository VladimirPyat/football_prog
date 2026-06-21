"""Public leaderboard/results and admin recalculate (legacy 1.3 shims)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from api.deps import DbSession, RoleChecker, cache_control_header, resolve_default_contest_id
from api.handlers.leaderboard import (
    get_global_leaderboard_response,
    get_round_leaderboard_response,
    get_round_results_response,
)
from database.models import UserRole
from schemas.leaderboard import LeaderboardOut, RoundResultsOut
from services.leaderboard_service import compute_etag
from services.scoring_persistence import recalculate_contest

router = APIRouter(tags=["legacy (deprecated)", "rounds (public)", "admin (system)"])

_admin = Depends(RoleChecker(UserRole.ADMIN))


@router.get("/leaderboard", response_model=LeaderboardOut, deprecated=True)
async def global_leaderboard(session: DbSession, response: Response) -> LeaderboardOut:
    """Общая таблица лидеров. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    out = await get_global_leaderboard_response(session, contest_id)
    etag = await compute_etag(session, contest_id=contest_id)
    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return out


@router.get("/rounds/{round_id}/leaderboard", response_model=LeaderboardOut, deprecated=True)
async def round_leaderboard(round_id: int, session: DbSession, response: Response) -> LeaderboardOut:
    """Таблица лидеров тура. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    out = await get_round_leaderboard_response(session, contest_id, round_id)
    etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return out


@router.get("/rounds/{round_id}/results", response_model=RoundResultsOut, deprecated=True)
async def round_results(round_id: int, session: DbSession, response: Response) -> RoundResultsOut:
    """Результаты тура. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    out = await get_round_results_response(session, contest_id, round_id)
    etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return out


@router.post("/admin/recalculate", dependencies=[_admin], deprecated=True)
async def admin_recalculate(session: DbSession) -> dict:
    """Пересчёт туров. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    count = await recalculate_contest(session, contest_id)
    await session.commit()
    return {"recalculated_rounds": count}
