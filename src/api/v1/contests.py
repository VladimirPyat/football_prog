"""Contest CRUD and lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from api.deps import DbSession, RoleChecker, cache_control_header
from database.models import UserRole
from schemas.contest import (
    ContestDeleteConfirmRequest,
    ContestDeleteResponse,
    ContestLifecycleOut,
    ContestOut,
    ContestPatchRequest,
    CreateContestRequest,
    PublicContestOut,
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
)
from services.contest_setup_service import create_contest, update_contest
from services.contest_discovery_service import list_public_contests

router = APIRouter(prefix="/contests", tags=["contests"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))
_admin = Depends(RoleChecker(UserRole.ADMIN))


def _lifecycle_out(contest) -> ContestLifecycleOut:
    return ContestLifecycleOut(
        status=contest.status,
        paused_at=contest.paused_at,
        finished_at=contest.finished_at,
        deletable_at=compute_deletable_at(contest.paused_at),
        seconds_until_deletable=seconds_until_deletable(contest.paused_at),
    )


@router.get("", response_model=list[ContestOut], dependencies=[_supervisor])
async def list_contests(session: DbSession) -> list[ContestOut]:
    """Список всех конкурсов (SUPERVISOR+)."""
    from sqlalchemy import select  # noqa: PLC0415
    from database.models import Contest  # noqa: PLC0415

    contests = (await session.scalars(select(Contest).order_by(Contest.id))).all()
    return [ContestOut.model_validate(c) for c in contests]


@router.get("/public", response_model=list[PublicContestOut])
async def list_public(session: DbSession, response: Response) -> list[PublicContestOut]:
    """Публичный список активных конкурсов для неавторизованных посетителей."""
    for k, v in cache_control_header().items():
        response.headers[k] = v
    return await list_public_contests(session)


@router.post("", response_model=ContestOut, dependencies=[_supervisor])
async def create(body: CreateContestRequest, session: DbSession) -> ContestOut:
    """Создать конкурс в статусе DRAFT (фаза SETUP)."""
    contest = await create_contest(
        session,
        body.name,
        slug=body.slug,
        rules_json=body.rules_json,
        total_teams=body.total_teams,
        matches_per_round=body.matches_per_round,
        total_rounds=body.total_rounds,
        is_round_robin=body.is_round_robin,
    )
    await session.commit()
    return ContestOut.model_validate(contest)


@router.get("/{contest_id}", response_model=ContestOut, dependencies=[_supervisor])
async def get_one(contest_id: int, session: DbSession) -> ContestOut:
    """Получить конкурс по идентификатору."""
    contest = await get_contest(session, contest_id)
    return ContestOut.model_validate(contest)


@router.patch("/{contest_id}", response_model=ContestOut, dependencies=[_supervisor])
async def patch_one(
    contest_id: int, body: ContestPatchRequest, session: DbSession
) -> ContestOut:
    """Обновить настройки конкурса (запрещено при is_locked).

    Args:
        contest_id: идентификатор конкурса
        body: поля для частичного обновления
    """
    contest = await update_contest(
        session,
        contest_id,
        body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return ContestOut.model_validate(contest)


@router.post("/{contest_id}/pause", response_model=ContestLifecycleOut, dependencies=[_admin])
async def pause(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Приостановить конкурс (RUNNING → PAUSED)."""
    contest = await pause_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.post("/{contest_id}/resume", response_model=ContestLifecycleOut, dependencies=[_admin])
async def resume(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Возобновить конкурс (PAUSED → RUNNING)."""
    contest = await resume_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.post("/{contest_id}/finish", response_model=ContestLifecycleOut, dependencies=[_admin])
async def finish(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Досрочно завершить конкурс (RUNNING|PAUSED → FINISHED)."""
    contest = await finish_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.delete("/{contest_id}", response_model=ContestDeleteResponse, dependencies=[_admin])
async def delete_one(
    contest_id: int, body: ContestDeleteConfirmRequest, session: DbSession
) -> ContestDeleteResponse:
    """Безопасно удалить данные конкурса (PAUSED + grace + confirm DELETE).

    Args:
        contest_id: идентификатор конкурса
        body: подтверждение удаления
    """
    await assert_deletable(session, contest_id)
    await delete_contest_data(session, contest_id)
    await session.commit()
    return ContestDeleteResponse()
