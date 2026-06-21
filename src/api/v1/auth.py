"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from core.security import create_access_token, hash_password, verify_password
from database.models import User
from schemas.auth import (
    ChangePasswordRequest,
    ContactOut,
    ContactPatchRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
)
from services.contact_service import get_contacts, upsert_contacts

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: DbSession) -> TokenResponse:
    """Вход в систему: проверка логина и пароля, выдача JWT."""
    user = await session.scalar(select(User).where(User.login == body.login))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        is_temp_password=user.is_temp_password,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict[str, bool]:
    """Сменить пароль (обязательно при первом входе с временным паролем)."""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный текущий пароль")

    user.password_hash = hash_password(body.new_password)
    user.is_temp_password = False
    await session.commit()
    return {"success": True}


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    """Профиль текущего авторизованного пользователя."""
    return UserOut.model_validate(user)


@router.get("/me/contacts", response_model=ContactOut)
async def get_my_contacts(user: CurrentUser, session: DbSession) -> ContactOut:
    """Контактные данные текущего пользователя."""
    return await get_contacts(session, user.id)


@router.patch("/me/contacts", response_model=ContactOut)
async def patch_my_contacts(
    body: ContactPatchRequest,
    user: CurrentUser,
    session: DbSession,
) -> ContactOut:
    """Обновить контактные данные (частичное обновление)."""
    patch = body.model_dump(exclude_unset=True)
    if "email" in patch and patch["email"] == "":
        patch["email"] = None
    result = await upsert_contacts(session, user.id, patch)
    await session.commit()
    return result
