"""Contest lifecycle and settings admin endpoints (legacy 1.3 shims)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import DbSession, RoleChecker, resolve_default_contest_id
from core.exceptions import ValidationError
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
    assert_deletable,
    compute_deletable_at,
    delete_contest_data,
    finish_contest,
    get_contest,
    pause_contest,
    resume_contest,
    seconds_until_deletable,
    update_exceptional_tiebreak,
)
from services.contest_setup_service import update_contest

router = APIRouter(prefix="/admin", tags=["legacy (deprecated)", "admin (contest)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.SUPPORT))
_support = Depends(RoleChecker(UserRole.SUPPORT))


def _lifecycle_out(settings) -> ContestLifecycleOut:
    return ContestLifecycleOut(
        status=settings.status,
        paused_at=settings.paused_at,
        finished_at=settings.finished_at,
        deletable_at=compute_deletable_at(settings.paused_at),
        seconds_until_deletable=seconds_until_deletable(settings.paused_at),
    )


@router.get(
    "/contest-settings",
    response_model=ContestSettingsOut,
    dependencies=[_supervisor],
    deprecated=True,
)
async def get_settings(session: DbSession) -> ContestSettingsOut:
    """Настройки конкурса. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    settings = await get_contest(session, contest_id)
    return ContestSettingsOut.model_validate(settings)


@router.patch(
    "/contest-settings",
    response_model=ContestSettingsOut,
    dependencies=[_supervisor],
    deprecated=True,
)
async def patch_settings(body: ContestSettingsPatchRequest, session: DbSession) -> ContestSettingsOut:
    """Обновить настройки. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    settings = await update_contest(
        session, contest_id, body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return ContestSettingsOut.model_validate(settings)


@router.post("/contest/pause", response_model=ContestLifecycleOut, dependencies=[_support], deprecated=True)
async def pause(session: DbSession) -> ContestLifecycleOut:
    """Приостановить конкурс. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    settings = await pause_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(settings)


@router.post("/contest/resume", response_model=ContestLifecycleOut, dependencies=[_support], deprecated=True)
async def resume(session: DbSession) -> ContestLifecycleOut:
    """Возобновить конкурс. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    settings = await resume_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(settings)


@router.post("/contest/finish", response_model=ContestLifecycleOut, dependencies=[_support], deprecated=True)
async def finish(session: DbSession) -> ContestLifecycleOut:
    """Завершить конкурс. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    settings = await finish_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(settings)


@router.delete("/contest", response_model=ContestDeleteResponse, dependencies=[_support], deprecated=True)
async def delete_contest(body: ContestDeleteConfirmRequest, session: DbSession) -> ContestDeleteResponse:
    """Удалить данные конкурса. Устаревший shim: default contest."""
    if body.confirm != "DELETE":
        raise ValidationError("Для подтверждения укажите confirm=DELETE")

    contest_id = await resolve_default_contest_id(session)
    await assert_deletable(session, contest_id)
    await delete_contest_data(session, contest_id)
    await session.commit()
    return ContestDeleteResponse()


@router.put(
    "/users/{user_id}/exceptional-tiebreak",
    response_model=ExceptionalTiebreakResponse,
    dependencies=[_support],
    deprecated=True,
)
async def set_exceptional_tiebreak(
    user_id: int,
    body: ExceptionalTiebreakRequest,
    session: DbSession,
) -> ExceptionalTiebreakResponse:
    """Исключительный тай-брейк. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    points = await update_exceptional_tiebreak(session, contest_id, user_id, body.points)
    await session.commit()
    return ExceptionalTiebreakResponse(
        contest_id=contest_id, user_id=user_id, exceptional_tiebreak_points=points
    )
