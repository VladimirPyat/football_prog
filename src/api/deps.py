"""FastAPI dependency injection: DB session, auth, RBAC, contest context."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from core.security import decode_access_token
from database.engine import create_engine, create_session_factory
from database.models import Contest, ContestLifecycleStatus, User, UserRole
from services.round_auto_close_service import auto_close_expired_rounds

_engine = create_engine()
_session_factory = create_session_factory(_engine)

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _fetch_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    return await _fetch_user(session, int(sub))


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return await _fetch_user(session, int(payload["sub"]))
    except (ValueError, KeyError):
        return None


class RoleChecker:
    """RBAC dependency: allow only specified roles."""

    def __init__(self, *allowed_roles: UserRole | str) -> None:
        self.allowed = {r.value if isinstance(r, UserRole) else r for r in allowed_roles}

    async def __call__(self, user: CurrentUser) -> User:
        if user.role not in self.allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user


def require_not_temp_password(user: CurrentUser) -> User:
    """Block endpoints when user must change temp password first."""
    if user.is_temp_password:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Temporary password must be changed before accessing this resource",
        )
    return user


def cache_control_header() -> dict[str, str]:
    settings = get_settings()
    return {
        "Cache-Control": (
            f"public, max-age={settings.cache_max_age_seconds}, "
            f"stale-while-revalidate={settings.cache_stale_while_revalidate_seconds}"
        ),
    }


async def resolve_default_contest_id(session: AsyncSession) -> int:
    """Resolve default contest for legacy 1.3 shims (RUNNING first, else lowest id)."""
    running_id = await session.scalar(
        select(Contest.id)
        .where(Contest.status == ContestLifecycleStatus.RUNNING)
        .order_by(Contest.id)
        .limit(1)
    )
    if running_id is not None:
        return running_id

    first_id = await session.scalar(select(Contest.id).order_by(Contest.id).limit(1))
    if first_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No contest found")
    return first_id


async def get_contest_context(session: DbSession, contest_id: int) -> Contest:
    """Load contest and auto-close expired ACTIVE rounds before handler runs."""
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Contest {contest_id} not found")
    closed_ids = await auto_close_expired_rounds(session, contest_id)
    if closed_ids:
        await session.commit()
        await session.refresh(contest)
    return contest


ContestContext = Annotated[Contest, Depends(get_contest_context)]
