"""Bootstrap ADMIN and SUPERVISOR users from .env (one-time / dev server setup).

Run after migrations and optional contest seed::

    uv run python src/scripts/bootstrap_users.py

Requires SEED_ADMIN_PASSWORD in .env (or SEED_ADMIN_PASSWORD_HASH with a bcrypt hash).

Organizer (SUPERVISOR) block is optional via SEED_SUPERVISOR_* variables.
Comment out ``seed_supervisor_user`` call below once user management lives in the admin UI.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.settings import Settings, get_settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from database.base import Base
from database.engine import create_engine, create_session_factory
from database.models import Contest, ContestParticipant, ParticipantStatus, User, UserRole

logger = logging.getLogger(__name__)


def resolve_password_hash(settings: Settings, *, plain_var: str | None, hash_var: str | None, label: str) -> str:
    """Prefer plaintext env password (hashed at runtime); fall back to precomputed bcrypt hash."""
    if plain_var:
        return hash_password(plain_var)
    if hash_var:
        return hash_var
    raise SystemExit(
        f"Set {label}_PASSWORD (recommended) or {label}_PASSWORD_HASH in .env — see .env.example"
    )


async def seed_admin_user(session: AsyncSession, settings: Settings, contest_id: int | None) -> User | None:
    settings = settings
    existing = await session.scalar(select(User).where(User.login == settings.seed_admin_login))
    if existing is not None:
        logger.info("Admin user already exists (login=%s), skipping", existing.login)
        user = existing
    else:
        password_hash = resolve_password_hash(
            settings,
            plain_var=settings.seed_admin_password,
            hash_var=settings.seed_admin_password_hash,
            label="SEED_ADMIN",
        )
        user = User(
            login=settings.seed_admin_login,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            first_name=settings.seed_admin_first_name,
            last_name=settings.seed_admin_last_name,
            is_temp_password=False,
        )
        session.add(user)
        await session.flush()
        logger.info("Created admin user (login=%s, id=%s)", user.login, user.id)

    if contest_id is not None:
        participant = await session.get(ContestParticipant, (contest_id, user.id))
        if participant is None:
            session.add(
                ContestParticipant(
                    contest_id=contest_id,
                    user_id=user.id,
                    status=ParticipantStatus.ACCEPTED,
                )
            )
            logger.info("Enrolled admin as participant in contest id=%s", contest_id)
    return user


async def seed_supervisor_user(session: AsyncSession, settings: Settings) -> User | None:
    # When the admin UI can create organizers via POST /admin/users/supervisor,
    # comment out the call to this function in run_bootstrap().
    if not settings.seed_supervisor_password and not settings.seed_supervisor_password_hash:
        logger.info(
            "SEED_SUPERVISOR_PASSWORD not set — skipping organizer bootstrap (login=%s)",
            settings.seed_supervisor_login,
        )
        return None

    existing = await session.scalar(
        select(User).where(User.login == settings.seed_supervisor_login)
    )
    if existing is not None:
        logger.info("Supervisor user already exists (login=%s), skipping", existing.login)
        return existing

    password_hash = resolve_password_hash(
        settings,
        plain_var=settings.seed_supervisor_password,
        hash_var=settings.seed_supervisor_password_hash,
        label="SEED_SUPERVISOR",
    )
    user = User(
        login=settings.seed_supervisor_login,
        password_hash=password_hash,
        role=UserRole.SUPERVISOR,
        first_name=settings.seed_supervisor_first_name,
        last_name=settings.seed_supervisor_last_name,
        is_temp_password=False,
    )
    session.add(user)
    await session.flush()
    logger.info("Created supervisor user (login=%s, id=%s)", user.login, user.id)
    return user


async def seed_demo_user(
    session: AsyncSession, settings: Settings, contest_id: int | None
) -> User | None:
    # TEMPORARY (2.1.1): remove after Stage 2.3 when supervisor invite UI seeds participants.
    # Tracked in agent_docs/reports/todo.md
    if not settings.seed_demo_user_password:
        logger.info(
            "SEED_DEMO_USER_PASSWORD not set — skipping demo participant bootstrap (login=%s)",
            settings.seed_demo_user_login,
        )
        return None

    existing = await session.scalar(
        select(User).where(User.login == settings.seed_demo_user_login)
    )
    if existing is not None:
        logger.info("Demo user already exists (login=%s), skipping create", existing.login)
        user = existing
    else:
        password_hash = hash_password(settings.seed_demo_user_password)
        user = User(
            login=settings.seed_demo_user_login,
            password_hash=password_hash,
            role=UserRole.USER,
            first_name=settings.seed_demo_user_first_name,
            last_name=settings.seed_demo_user_last_name,
            is_temp_password=False,
        )
        session.add(user)
        await session.flush()
        logger.info("Created demo user (login=%s, id=%s)", user.login, user.id)

    if contest_id is not None:
        participant = await session.get(ContestParticipant, (contest_id, user.id))
        if participant is None:
            session.add(
                ContestParticipant(
                    contest_id=contest_id,
                    user_id=user.id,
                    status=ParticipantStatus.ACCEPTED,
                )
            )
            logger.info("Enrolled demo user as participant in contest id=%s", contest_id)
    return user


async def run_bootstrap(database_url: str | None = None, *, enroll_contest: bool = True) -> None:
    settings = get_settings()
    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        async with session.begin():
            contest_id: int | None = None
            if enroll_contest:
                contest = await session.scalar(select(Contest).order_by(Contest.id).limit(1))
                if contest is not None:
                    contest_id = contest.id
                else:
                    logger.warning("No contest row found — admin will not be enrolled as participant")

            await seed_admin_user(session, settings, contest_id)
            await seed_supervisor_user(session, settings)
            await seed_demo_user(session, settings, contest_id)

    await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Bootstrap ADMIN and SUPERVISOR users from .env")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Async SQLAlchemy database URL (defaults to DATABASE_URL / settings)",
    )
    parser.add_argument(
        "--no-contest-enroll",
        action="store_true",
        help="Do not add admin to contest_participants even if a contest exists",
    )
    args = parser.parse_args()
    asyncio.run(run_bootstrap(database_url=args.database_url, enroll_contest=not args.no_contest_enroll))


if __name__ == "__main__":
    main()
