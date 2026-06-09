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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.base import Base
from database.engine import create_engine, create_session_factory
from database.models import ContestSettings, User, UserRole

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


async def seed_contest_settings(session: AsyncSession, defaults_path: Path) -> ContestSettings:
    existing = await session.scalar(select(ContestSettings).limit(1))
    if existing is not None:
        logger.info("Contest settings already exist (id=%s), skipping", existing.id)
        return existing

    data = load_contest_defaults(defaults_path)
    structure = data["contest_structure"]
    settings = ContestSettings(
        is_locked=False,
        total_teams=structure["total_teams"],
        matches_per_round=structure["matches_per_round"],
        total_rounds=structure["total_rounds"],
        is_round_robin=structure["is_round_robin"],
        rules_json=build_rules_json(data),
    )
    session.add(settings)
    await session.flush()
    logger.info("Created contest settings (id=%s)", settings.id)
    return settings


async def seed_admin_user(session: AsyncSession) -> User:
    settings = get_settings()
    existing = await session.scalar(select(User).where(User.login == settings.seed_admin_login))
    if existing is not None:
        logger.info("Admin user already exists (login=%s), skipping", existing.login)
        return existing

    user = User(
        login=settings.seed_admin_login,
        password_hash=settings.seed_admin_password_hash,
        role=UserRole.ADMIN,
        first_name=settings.seed_admin_first_name,
        last_name=settings.seed_admin_last_name,
        is_temp_password=True,
    )
    session.add(user)
    await session.flush()
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
            await seed_contest_settings(session, path)
            await seed_admin_user(session)

    await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Seed contest settings and admin user")
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
