"""Password setup, invite acceptance, and password reset via signed tokens."""

from __future__ import annotations

import secrets

from config.settings import get_settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
from core.security import hash_password
from core.setup_tokens import build_setup_url, create_setup_token, decode_setup_token
from database.models import Contact, ContestParticipant, ParticipantStatus, User
from services.participant_service import (
    accept_participation_for_contest,
    accept_pending_participations,
)


def _is_setup_complete(
    user: User, contest_id: int | None, session_participant: ContestParticipant | None
) -> bool:
    """True when enrollment (if scoped) and password requirements are satisfied."""
    settings = get_settings()
    if contest_id is not None and session_participant is not None:
        if session_participant.status != ParticipantStatus.ACCEPTED:
            return False
        if not settings.enforce_password_setup:
            return True
    return not user.is_temp_password


async def preview_setup(session: AsyncSession, token: str) -> dict:
    """Return login, UI mode, and whether setup was already completed."""
    try:
        payload = decode_setup_token(token)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    user_id = int(payload["sub"])
    contest_id = payload.get("contest_id")
    if contest_id is not None:
        contest_id = int(contest_id)

    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")

    participant = None
    if contest_id is not None:
        participant = await session.get(ContestParticipant, (contest_id, user_id))

    settings = get_settings()
    mode = "password_form" if settings.enforce_password_setup else "confirm_only"
    already_completed = _is_setup_complete(user, contest_id, participant)

    return {
        "login": user.login,
        "mode": mode,
        "already_completed": already_completed,
    }


async def complete_setup(
    session: AsyncSession,
    token: str,
    new_password: str | None = None,
) -> dict:
    """Idempotent: set password (optional) and accept contest enrollment when present."""
    try:
        payload = decode_setup_token(token)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    user_id = int(payload["sub"])
    contest_id = payload.get("contest_id")
    if contest_id is not None:
        contest_id = int(contest_id)

    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")

    participant = None
    if contest_id is not None:
        participant = await session.get(ContestParticipant, (contest_id, user_id))

    if _is_setup_complete(user, contest_id, participant):
        return {"success": True, "accepted": False, "already_completed": True}

    settings = get_settings()
    if settings.enforce_password_setup:
        if not new_password:
            raise ValidationError("Новый пароль обязателен")
        user.password_hash = hash_password(new_password)
        user.is_temp_password = False

    accepted = False
    if contest_id is not None:
        rows = await accept_participation_for_contest(session, user_id, contest_id)
        accepted = rows > 0
    elif not user.is_temp_password:
        await accept_pending_participations(session, user_id)
        accepted = True

    return {"success": True, "accepted": accepted, "already_completed": False}


async def request_password_reset(session: AsyncSession, email: str) -> dict:
    """Always return a privacy-safe message; re-issue temp password when email exists."""
    contact = await session.scalar(select(Contact).where(Contact.email == email))
    message = "Если адрес зарегистрирован, инструкции отправлены"

    if contact is None:
        return {"message": message}

    user = await session.get(User, contact.user_id)
    if user is None:
        return {"message": message}

    temp_password = secrets.token_urlsafe(10)
    user.password_hash = hash_password(temp_password)
    user.is_temp_password = True

    # Token issued for dev/scripts; not returned in API response (privacy).
    _ = build_setup_url(create_setup_token(user_id=user.id))

    return {"message": message}
