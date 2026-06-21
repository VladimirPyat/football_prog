"""Current-user endpoints (enrolled contests, etc.)."""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import CurrentUser, DbSession
from schemas.contest import UserContestOut
from services.contest_discovery_service import list_user_contests

router = APIRouter(prefix="/me", tags=["user"])


@router.get("/contests", response_model=list[UserContestOut])
async def my_contests(user: CurrentUser, session: DbSession) -> list[UserContestOut]:
    """Список конкурсов, в которых текущий пользователь участвует."""
    return await list_user_contests(session, user_id=user.id, role=user.role)
