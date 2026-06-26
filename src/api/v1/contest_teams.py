"""Contest team setup endpoints."""

from __future__ import annotations

from config.settings import get_settings
from fastapi import APIRouter, Depends, File, UploadFile

from api.deps import ContestContext, DbSession, RoleChecker
from database.models import UserRole
from schemas.contest import LogoUploadResponse, TeamCreateRequest, TeamOut, TeamPatchRequest
from services.contest_setup_service import (
    create_team,
    delete_team,
    list_teams,
    update_team,
)
from services.team_logo_service import resolve_team_logo_url, save_team_logo
from services.team_out import team_to_out

router = APIRouter(prefix="/contests/{contest_id}/teams", tags=["contest setup"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))


@router.get("", response_model=list[TeamOut], dependencies=[_supervisor])
async def get_teams(contest_id: int, session: DbSession, _contest: ContestContext) -> list[TeamOut]:
    """Список команд конкурса."""
    settings = get_settings()
    teams = await list_teams(session, contest_id)
    return [team_to_out(t, settings) for t in teams]


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
    return team_to_out(team, get_settings())


@router.post("/{team_id}/logo", response_model=LogoUploadResponse, dependencies=[_supervisor])
async def upload_team_logo(
    contest_id: int,
    team_id: int,
    session: DbSession,
    _contest: ContestContext,
    file: UploadFile = File(...),
) -> LogoUploadResponse:
    """Загрузить логотип команды (PNG/JPG/GIF, до 2 МБ). Доступно только в фазе SETUP."""
    settings = get_settings()
    file_bytes = await file.read()
    stored_url = await save_team_logo(
        session,
        contest_id=contest_id,
        team_id=team_id,
        file_bytes=file_bytes,
        content_type=file.content_type or "",
        settings=settings,
    )
    await session.commit()
    return LogoUploadResponse(logo_url=resolve_team_logo_url(stored_url, settings))


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
    return team_to_out(team, get_settings())


@router.delete("/{team_id}", dependencies=[_supervisor])
async def remove_team(
    contest_id: int, team_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    """Удалить команду (только в фазе SETUP)."""
    await delete_team(session, contest_id, team_id)
    await session.commit()
    return {"deleted": True}
