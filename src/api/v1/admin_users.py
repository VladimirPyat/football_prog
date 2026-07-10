"""Admin-only user management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import DbSession, RoleChecker
from database.models import UserRole
from schemas.auth import UserOut
from schemas.users import CreateSupervisorRequest, CreateSupervisorResponse
from services.user_admin_service import create_supervisor

router = APIRouter(prefix="/admin/users", tags=["admin (users)"])

_support = Depends(RoleChecker(UserRole.SUPPORT))


@router.post(
    "/supervisor",
    response_model=CreateSupervisorResponse,
    dependencies=[_support],
)
async def post_supervisor(body: CreateSupervisorRequest, session: DbSession) -> CreateSupervisorResponse:
    """Создать организатора конкурса (роль SUPERVISOR). Только ADMIN."""
    user = await create_supervisor(
        session,
        login=body.login,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        is_temp_password=body.is_temp_password,
    )
    await session.commit()
    return CreateSupervisorResponse(user=UserOut.model_validate(user))
