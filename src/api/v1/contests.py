"""Contest CRUD and lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import DbSession, RoleChecker
from database.models import UserRole
from schemas.contest import (
    ContestDeleteConfirmRequest,
    ContestDeleteResponse,
    ContestLifecycleOut,
    ContestOut,
    ContestPatchRequest,
    CreateContestRequest,
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
    get_contest,
    pause_contest,
    resume_contest,
    seconds_until_deletable,
)
from services.contest_setup_service import create_contest, update_contest

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
    from sqlalchemy import select  # noqa: PLC0415
    from database.models import Contest  # noqa: PLC0415

    contests = (await session.scalars(select(Contest).order_by(Contest.id))).all()
    return [ContestOut.model_validate(c) for c in contests]


@router.post("", response_model=ContestOut, dependencies=[_supervisor])
async def create(body: CreateContestRequest, session: DbSession) -> ContestOut:
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
    contest = await get_contest(session, contest_id)
    return ContestOut.model_validate(contest)


@router.patch("/{contest_id}", response_model=ContestOut, dependencies=[_supervisor])
async def patch_one(
    contest_id: int, body: ContestPatchRequest, session: DbSession
) -> ContestOut:
    try:
        contest = await update_contest(
            session,
            contest_id,
            body.model_dump(exclude_unset=True),
        )
        await session.commit()
    except ContestLockedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ContestOut.model_validate(contest)


@router.post("/{contest_id}/pause", response_model=ContestLifecycleOut, dependencies=[_admin])
async def pause(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    try:
        contest = await pause_contest(session, contest_id)
        await session.commit()
    except IllegalTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _lifecycle_out(contest)


@router.post("/{contest_id}/resume", response_model=ContestLifecycleOut, dependencies=[_admin])
async def resume(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    try:
        contest = await resume_contest(session, contest_id)
        await session.commit()
    except IllegalTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _lifecycle_out(contest)


@router.post("/{contest_id}/finish", response_model=ContestLifecycleOut, dependencies=[_admin])
async def finish(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    try:
        contest = await finish_contest(session, contest_id)
        await session.commit()
    except IllegalTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _lifecycle_out(contest)


@router.delete("/{contest_id}", response_model=ContestDeleteResponse, dependencies=[_admin])
async def delete_one(
    contest_id: int, body: ContestDeleteConfirmRequest, session: DbSession
) -> ContestDeleteResponse:
    try:
        await assert_deletable(session, contest_id)
        await delete_contest_data(session, contest_id)
        await session.commit()
    except ContestNotPausedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except GracePeriodError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ContestDeleteDisabledError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ContestDeleteResponse()
