"""Load contest defaults and initial admin user into the database."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.settings import get_settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from database.base import Base
from database.engine import create_engine, create_session_factory
from database.models import Contest, ContestParticipant, ParticipantStatus, User, UserRole

logger = logging.getLogger(__name__)


def load_contest_defaults(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_rules_json(data: dict) -> dict:
    return {
        "scoring_rules": data["scoring_rules"],
        "tiebreakers": data["tiebreakers"],
        "constraints": data["constraints"],
        "contest_structure": data["contest_structure"],
    }


async def seed_contest(session: AsyncSession, defaults_path: Path) -> Contest:
    existing = await session.scalar(select(Contest).order_by(Contest.id).limit(1))
    if existing is not None:
        logger.info("Contest already exists (id=%s), skipping", existing.id)
        return existing

    data = load_contest_defaults(defaults_path)
    structure = data["contest_structure"]
    contest = Contest(
        name="Default",
        slug=None,
        is_locked=False,
        total_teams=structure["total_teams"],
        matches_per_round=structure["matches_per_round"],
        total_rounds=structure["total_rounds"],
        is_round_robin=structure["is_round_robin"],
        rules_json=build_rules_json(data),
    )
    session.add(contest)
    await session.flush()
    logger.info("Created contest (id=%s)", contest.id)
    return contest


def _admin_password_hash() -> str:
    settings = get_settings()
    if settings.seed_admin_password:
        return hash_password(settings.seed_admin_password)
    if settings.seed_admin_password_hash:
        return settings.seed_admin_password_hash
    return "dev-only-placeholder-hash"


async def seed_admin_user(session: AsyncSession, contest_id: int) -> User:
    settings = get_settings()
    existing = await session.scalar(select(User).where(User.login == settings.seed_admin_login))
    if existing is not None:
        logger.info("Admin user already exists (login=%s), skipping", existing.login)
        participant = await session.get(ContestParticipant, (contest_id, existing.id))
        if participant is None:
            session.add(
                ContestParticipant(
                    contest_id=contest_id,
                    user_id=existing.id,
                    status=ParticipantStatus.ACCEPTED,
                )
            )
        return existing

    user = User(
        login=settings.seed_admin_login,
        password_hash=_admin_password_hash(),
        role=UserRole.ADMIN,
        first_name=settings.seed_admin_first_name,
        last_name=settings.seed_admin_last_name,
        is_temp_password=True,
    )
    session.add(user)
    await session.flush()
    session.add(
        ContestParticipant(
            contest_id=contest_id,
            user_id=user.id,
            status=ParticipantStatus.ACCEPTED,
        )
    )
    logger.info("Created admin user (login=%s, id=%s)", user.login, user.id)
    return user


async def run_seed(database_url: str | None = None, defaults_path: Path | None = None) -> None:
    app_settings = get_settings()
    path = defaults_path or app_settings.contest_defaults_path
    if not path.is_file():
        raise FileNotFoundError(f"Contest defaults not found: {path}")

    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        async with session.begin():
            contest = await seed_contest(session, path)
            await seed_admin_user(session, contest.id)

    await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Seed contest and admin user")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Async SQLAlchemy database URL (defaults to DATABASE_URL env / settings)",
    )
    parser.add_argument(
        "--defaults-path",
        type=Path,
        default=None,
        help="Path to contest_defaults.json",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(database_url=args.database_url, defaults_path=args.defaults_path))


if __name__ == "__main__":
    main()
