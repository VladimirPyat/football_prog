"""Admin-only user management (organizer / SUPERVISOR creation)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ValidationError
from core.security import hash_password
from database.models import User, UserRole


async def create_supervisor(
    session: AsyncSession,
    *,
    login: str,
    password: str,
    first_name: str,
    last_name: str,
    is_temp_password: bool = False,
) -> User:
    """Create a global SUPERVISOR (contest organizer) account."""
    login = login.strip()
    if not login:
        raise ValidationError("Логин не может быть пустым")
    if not password:
        raise ValidationError("Пароль не может быть пустым")

    existing = await session.scalar(select(User).where(User.login == login))
    if existing is not None:
        raise ValidationError(f"Логин «{login}» уже занят")

    user = User(
        login=login,
        password_hash=hash_password(password),
        role=UserRole.SUPERVISOR,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_temp_password=is_temp_password,
    )
    session.add(user)
    await session.flush()
    return user
