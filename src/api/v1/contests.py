"""Contest CRUD and lifecycle endpoints."""

from __future__ import annotations

from config.settings import get_settings
from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.deps import CurrentUser, DbSession, RoleChecker, cache_control_header
from database.models import ContestLifecycleStatus, User, UserRole
from schemas.contest import (
    ContestDeleteConfirmRequest,
    ContestDeleteResponse,
    ContestLifecycleOut,
    ContestOut,
    ContestPatchRequest,
    ContestRestoreResponse,
    CreateContestRequest,
    DeletedContestOut,
    PublicContestOut,
)
from services.contest_discovery_service import list_public_contests
from services.contest_lifecycle_service import (
    assert_deletable,
    compute_deletable_at,
    delete_contest_data,
    finish_contest,
    get_contest,
    pause_contest,
    resume_contest,
    seconds_until_deletable,
    start_contest,
)
from services.contest_restore_service import restore_contest_from_snapshot
from services.contest_setup_service import create_contest, update_contest

router = APIRouter(prefix="/contests", tags=["contests"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.SUPPORT))
_support = Depends(RoleChecker(UserRole.SUPPORT))


async def require_delete_role(user: CurrentUser) -> User:
    """SUPERVISOR and ADMIN may delete contests (subject to lifecycle rules)."""
    if user.role not in {UserRole.SUPPORT.value, UserRole.SUPERVISOR.value}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return user


async def require_finish_role(user: CurrentUser) -> User:
    """ADMIN may finish; SUPERVISOR only in training mode."""
    if user.role == UserRole.SUPPORT.value:
        return user
    settings = get_settings()
    if user.role == UserRole.SUPERVISOR.value and settings.supervisor_training_mode:
        return user
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")


async def require_restore_role(user: CurrentUser) -> User:
    """Only ADMIN may restore soft-deleted contests."""
    if user.role != UserRole.SUPPORT.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return user


_finish = Depends(require_finish_role)
_delete = Depends(require_delete_role)
_restore = Depends(require_restore_role)


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

    contests = (
        await session.scalars(
            select(Contest).where(Contest.deleted_at.is_(None)).order_by(Contest.id)
        )
    ).all()
    return [ContestOut.model_validate(c) for c in contests]


@router.get("/deleted", response_model=list[DeletedContestOut], dependencies=[_support])
async def list_deleted(session: DbSession) -> list[DeletedContestOut]:
    """Soft-deleted contests (ADMIN) — for restore within snapshot window."""
    from sqlalchemy import select  # noqa: PLC0415

    from database.models import Contest  # noqa: PLC0415
    from services.contest_restore_service import has_restore_snapshot  # noqa: PLC0415

    rows = (
        await session.scalars(
            select(Contest).where(Contest.deleted_at.is_not(None)).order_by(Contest.deleted_at.desc())
        )
    ).all()
    result: list[DeletedContestOut] = []
    for c in rows:
        restore_available = await has_restore_snapshot(session, c.id)
        result.append(
            DeletedContestOut(
                id=c.id,
                name=c.name,
                deleted_at=c.deleted_at,
                restore_available=restore_available,
            )
        )
    return result


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


@router.post("/{contest_id}/start", response_model=ContestLifecycleOut, dependencies=[_supervisor])
async def start(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Запустить конкурс (DRAFT → RUNNING, блокировка структуры)."""
    contest = await start_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.post("/{contest_id}/pause", response_model=ContestLifecycleOut, dependencies=[_supervisor])
async def pause(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Приостановить конкурс (RUNNING → PAUSED)."""
    contest = await pause_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.post("/{contest_id}/resume", response_model=ContestLifecycleOut, dependencies=[_supervisor])
async def resume(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Возобновить конкурс (PAUSED → RUNNING)."""
    contest = await resume_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.post(
    "/{contest_id}/finish",
    response_model=ContestLifecycleOut,
    dependencies=[_finish],
)
async def finish(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Досрочно завершить конкурс (RUNNING|PAUSED → FINISHED)."""
    contest = await finish_contest(session, contest_id)
    await session.commit()
    return _lifecycle_out(contest)


@router.delete(
    "/{contest_id}",
    response_model=ContestDeleteResponse,
    dependencies=[_delete],
)
async def delete_one(
    contest_id: int,
    body: ContestDeleteConfirmRequest,
    session: DbSession,
    user: CurrentUser,
) -> ContestDeleteResponse:
    """Soft-delete contest (DRAFT instant; PAUSED after grace). Hidden from lists; ADMIN may restore."""
    settings = get_settings()
    contest = await get_contest(session, contest_id)
    instant = (
        settings.contest_allow_instant_delete
        or settings.supervisor_training_mode
        or contest.status == ContestLifecycleStatus.DRAFT
    )
    allow_draft = True
    await assert_deletable(
        session, contest_id, instant=instant, allow_draft=allow_draft
    )
    await delete_contest_data(session, contest_id, deleted_by_user_id=user.id)
    await session.commit()
    return ContestDeleteResponse()


@router.post(
    "/{contest_id}/restore",
    response_model=ContestRestoreResponse,
    dependencies=[_restore],
)
async def restore_one(contest_id: int, session: DbSession) -> ContestRestoreResponse:
    """Restore contest from training-mode snapshot within the restore window."""
    await restore_contest_from_snapshot(session, contest_id)
    await session.commit()
    return ContestRestoreResponse()
