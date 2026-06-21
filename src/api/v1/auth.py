"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from core.security import create_access_token, hash_password, verify_password
from database.models import User
from schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut

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
