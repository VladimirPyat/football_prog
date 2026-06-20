"""Contest lifecycle and settings admin endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import DbSession, RoleChecker
from database.models import UserRole
from schemas.contest import (
    ContestDeleteConfirmRequest,
    ContestDeleteResponse,
    ContestLifecycleOut,
    ContestSettingsOut,
    ContestSettingsPatchRequest,
    ExceptionalTiebreakRequest,
    ExceptionalTiebreakResponse,
)
from services.contest_lifecycle_service import (
    ContestDeleteDisabledError,
    ContestLockedError,
    ContestNotPausedError,
    GracePeriodError,
    IllegalTransitionError,
    assert_deletable,
    compute_deletable_at,
    delete_contest_data,
    finish_contest,
    get_contest_settings,
    pause_contest,
    require_unlocked,
    resume_contest,
    seconds_until_deletable,
    update_exceptional_tiebreak,
)

router = APIRouter(prefix="/admin", tags=["admin (contest)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))
_admin = Depends(RoleChecker(UserRole.ADMIN))


def _lifecycle_out(settings) -> ContestLifecycleOut:
    return ContestLifecycleOut(
        status=settings.status,
        paused_at=settings.paused_at,
        finished_at=settings.finished_at,
        deletable_at=compute_deletable_at(settings.paused_at),
        seconds_until_deletable=seconds_until_deletable(settings.paused_at),
    )


@router.get("/contest-settings", response_model=ContestSettingsOut, dependencies=[_supervisor])
async def get_settings(session: DbSession) -> ContestSettingsOut:
    settings = await get_contest_settings(session)
    return ContestSettingsOut.model_validate(settings)


@router.patch("/contest-settings", response_model=ContestSettingsOut, dependencies=[_supervisor])
async def patch_settings(body: ContestSettingsPatchRequest, session: DbSession) -> ContestSettingsOut:
    try:
        settings = await require_unlocked(session)
    except ContestLockedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    for field in ("total_teams", "matches_per_round", "total_rounds", "is_round_robin", "rules_json"):
        value = getattr(body, field)
        if value is not None:
            setattr(settings, field, value)

    await session.commit()
    return ContestSettingsOut.model_validate(settings)


@router.post("/contest/pause", response_model=ContestLifecycleOut, dependencies=[_admin])
async def pause(session: DbSession) -> ContestLifecycleOut:
    try:
        settings = await pause_contest(session)
        await session.commit()
    except IllegalTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _lifecycle_out(settings)


@router.post("/contest/resume", response_model=ContestLifecycleOut, dependencies=[_admin])
async def resume(session: DbSession) -> ContestLifecycleOut:
    try:
        settings = await resume_contest(session)
        await session.commit()
    except IllegalTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _lifecycle_out(settings)


@router.post("/contest/finish", response_model=ContestLifecycleOut, dependencies=[_admin])
async def finish(session: DbSession) -> ContestLifecycleOut:
    try:
        settings = await finish_contest(session)
        await session.commit()
    except IllegalTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _lifecycle_out(settings)


@router.delete("/contest", response_model=ContestDeleteResponse, dependencies=[_admin])
async def delete_contest(body: ContestDeleteConfirmRequest, session: DbSession) -> ContestDeleteResponse:
    if body.confirm != "DELETE":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="confirm must be 'DELETE'")

    try:
        await assert_deletable(session)
        await delete_contest_data(session)
        await session.commit()
    except ContestNotPausedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except GracePeriodError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ContestDeleteDisabledError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ContestDeleteResponse()


@router.put(
    "/users/{user_id}/exceptional-tiebreak",
    response_model=ExceptionalTiebreakResponse,
    dependencies=[_admin],
)
async def set_exceptional_tiebreak(
    user_id: int,
    body: ExceptionalTiebreakRequest,
    session: DbSession,
) -> ExceptionalTiebreakResponse:
    try:
        points = await update_exceptional_tiebreak(session, user_id, body.points)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ExceptionalTiebreakResponse(user_id=user_id, exceptional_tiebreak_points=points)
