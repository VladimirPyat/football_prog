"""Contest team setup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import ContestContext, DbSession, RoleChecker
from database.models import UserRole
from schemas.contest import TeamCreateRequest, TeamOut, TeamPatchRequest
from services.contest_setup_service import (
    create_team,
    delete_team,
    list_teams,
    update_team,
)

router = APIRouter(prefix="/contests/{contest_id}/teams", tags=["contest setup"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))


@router.get("", response_model=list[TeamOut], dependencies=[_supervisor])
async def get_teams(contest_id: int, session: DbSession, _contest: ContestContext) -> list[TeamOut]:
    """Список команд конкурса."""
    teams = await list_teams(session, contest_id)
    return [TeamOut.model_validate(t) for t in teams]


@router.post("", response_model=TeamOut, dependencies=[_supervisor])
async def post_team(
    contest_id: int, body: TeamCreateRequest, session: DbSession, _contest: ContestContext
) -> TeamOut:
    """Создать команду (только в фазе SETUP, !is_locked).

    Args:
        contest_id: идентификатор конкурса
        body: данные команды
    """
    team = await create_team(
        session, contest_id, body.name, body.short_name, body.logo_url
    )
    await session.commit()
    return TeamOut.model_validate(team)


@router.patch("/{team_id}", response_model=TeamOut, dependencies=[_supervisor])
async def patch_team(
    contest_id: int,
    team_id: int,
    body: TeamPatchRequest,
    session: DbSession,
    _contest: ContestContext,
) -> TeamOut:
    """Обновить команду (только в фазе SETUP).

    Args:
        contest_id: идентификатор конкурса
        team_id: идентификатор команды
        body: поля для обновления
    """
    team = await update_team(
        session, contest_id, team_id, body.model_dump(exclude_unset=True)
    )
    await session.commit()
    return TeamOut.model_validate(team)


@router.delete("/{team_id}", dependencies=[_supervisor])
async def remove_team(
    contest_id: int, team_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    """Удалить команду (только в фазе SETUP)."""
    await delete_team(session, contest_id, team_id)
    await session.commit()
    return {"deleted": True}
