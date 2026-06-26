"""Authentication endpoints."""

from __future__ import annotations

from config.settings import get_settings
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from core.exceptions import PasswordSetupRequiredError
from core.security import create_access_token, hash_password, verify_password
from database.models import User
from schemas.auth import (
    ChangePasswordRequest,
    CompleteSetupRequest,
    CompleteSetupResponse,
    ContactOut,
    ContactPatchRequest,
    LoginRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    SetupPreviewResponse,
    TokenResponse,
    UserOut,
)
from services.auth_setup_service import complete_setup, preview_setup, request_password_reset
from services.contact_service import get_contacts, upsert_contacts
from services.participant_service import accept_pending_participations

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: DbSession) -> TokenResponse:
    """Вход в систему: проверка логина и пароля, выдача JWT."""
    user = await session.scalar(select(User).where(User.login == body.login))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    settings = get_settings()
    if settings.enforce_password_setup and user.is_temp_password:
        raise PasswordSetupRequiredError(
            "Подтвердите участие и установите пароль по ссылке из письма"
        )

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        is_temp_password=user.is_temp_password,
    )


@router.get("/setup-preview", response_model=SetupPreviewResponse)
async def setup_preview(token: str = Query(...), session: DbSession = ...) -> SetupPreviewResponse:
    """Preview invite/reset link: login, UI mode, completion state."""
    result = await preview_setup(session, token)
    return SetupPreviewResponse(**result)


@router.post("/complete-setup", response_model=CompleteSetupResponse)
async def post_complete_setup(
    body: CompleteSetupRequest, session: DbSession
) -> CompleteSetupResponse:
    """Accept invite and/or set password via signed token (idempotent)."""
    result = await complete_setup(session, body.token, body.new_password)
    await session.commit()
    return CompleteSetupResponse(**result)


@router.post("/request-password-reset", response_model=PasswordResetResponse)
async def post_request_password_reset(
    body: PasswordResetRequest, session: DbSession
) -> PasswordResetResponse:
    """Always 200 — re-issue temp password when email is known (no SMTP in v1)."""
    result = await request_password_reset(session, body.email)
    await session.commit()
    return PasswordResetResponse(**result)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict[str, bool]:
    """Сменить пароль (обязательно при первом входе с временным паролем).

    При смене временного пароля участник переводится в статус ACCEPTED во всех конкурсах.
    """
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный текущий пароль")

    user.password_hash = hash_password(body.new_password)
    user.is_temp_password = False
    await accept_pending_participations(session, user.id)
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
