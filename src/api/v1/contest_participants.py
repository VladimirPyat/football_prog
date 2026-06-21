"""Contest participant setup and exceptional tie-break endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import ContestContext, DbSession, RoleChecker
from database.models import UserRole
from schemas.contest import (
    ExceptionalTiebreakRequest,
    ExceptionalTiebreakResponse,
    ParticipantCreateRequest,
    ParticipantInviteOut,
    ParticipantOut,
)
from services.contest_lifecycle_service import ContestLockedError, update_exceptional_tiebreak
from services.contest_setup_service import add_participant, list_participants, remove_participant

router = APIRouter(prefix="/contests/{contest_id}/participants", tags=["contest setup"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))
_admin = Depends(RoleChecker(UserRole.ADMIN))


@router.get("", response_model=list[ParticipantOut], dependencies=[_supervisor])
async def get_participants(
    contest_id: int, session: DbSession, _contest: ContestContext
) -> list[ParticipantOut]:
    rows = await list_participants(session, contest_id)
    return [ParticipantOut(**row) for row in rows]


@router.post("", response_model=ParticipantInviteOut, dependencies=[_supervisor])
async def post_participant(
    contest_id: int,
    body: ParticipantCreateRequest,
    session: DbSession,
    _contest: ContestContext,
) -> ParticipantInviteOut:
    try:
        result = await add_participant(
            session,
            contest_id,
            body.email,
            body.first_name,
            body.last_name,
            login=body.login,
        )
        await session.commit()
    except ContestLockedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ParticipantInviteOut(**result)


@router.delete("/{user_id}", dependencies=[_supervisor])
async def delete_participant(
    contest_id: int, user_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    try:
        await remove_participant(session, contest_id, user_id)
        await session.commit()
    except ContestLockedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"removed": True}


@router.put(
    "/{user_id}/exceptional-tiebreak",
    response_model=ExceptionalTiebreakResponse,
    dependencies=[_admin],
)
async def set_exceptional_tiebreak(
    contest_id: int,
    user_id: int,
    body: ExceptionalTiebreakRequest,
    session: DbSession,
    _contest: ContestContext,
) -> ExceptionalTiebreakResponse:
    try:
        points = await update_exceptional_tiebreak(session, contest_id, user_id, body.points)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ExceptionalTiebreakResponse(
        contest_id=contest_id, user_id=user_id, exceptional_tiebreak_points=points
    )
