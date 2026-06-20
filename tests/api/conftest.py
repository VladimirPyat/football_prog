"""Fixtures for Stage 1.3 HTTP API tests (loader DB + httpx ASGI client)."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for _p in (str(_ROOT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.security import hash_password
from database.models import (
    ContestLifecycleStatus,
    ContestSettings,
    Match,
    Round,
    RoundStatus,
    User,
    UserRole,
)
from scripts.load_test_data import run_load

TEST_PASSWORD = "testpass123"
API_PREFIX = "/api/v1"


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def api_login(client: httpx.AsyncClient, login: str, password: str = TEST_PASSWORD) -> str:
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"login": login, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _seed_test_users(sf: async_sessionmaker[AsyncSession]) -> None:
    async with sf() as session:
        async with session.begin():
            all_users = (await session.scalars(select(User))).all()
            for user in all_users:
                user.password_hash = hash_password(TEST_PASSWORD)

            for login, role in [("admin_api", UserRole.ADMIN), ("supervisor_api", UserRole.SUPERVISOR)]:
                existing = await session.scalar(select(User).where(User.login == login))
                if existing is None:
                    session.add(
                        User(
                            login=login,
                            password_hash=hash_password(TEST_PASSWORD),
                            role=role.value,
                            first_name="",
                            last_name=login,
                            is_temp_password=False,
                        )
                    )
                else:
                    existing.role = role.value

            temp = await session.scalar(select(User).where(User.login == "temp_user"))
            if temp is None:
                session.add(
                    User(
                        login="temp_user",
                        password_hash=hash_password(TEST_PASSWORD),
                        role=UserRole.USER.value,
                        first_name="",
                        last_name="temp",
                        is_temp_password=True,
                    )
                )
            else:
                temp.is_temp_password = True


async def _shift_round10_forward(sf: async_sessionmaker[AsyncSession]) -> None:
    async with sf() as session:
        async with session.begin():
            round_ = await session.scalar(select(Round).where(Round.number == 10))
            if round_ is None:
                return
            matches = (
                await session.scalars(select(Match).where(Match.round_id == round_.id))
            ).all()
            base = datetime.now(timezone.utc) + timedelta(days=14)
            for i, match in enumerate(sorted(matches, key=lambda m: m.id)):
                match.date_time = base + timedelta(hours=i)
            earliest = min(m.date_time for m in matches)
            round_.deadline = earliest - timedelta(days=3)
            round_.status = RoundStatus.ACTIVE.value


async def get_round_id(sf: async_sessionmaker[AsyncSession], number: int) -> int:
    async with sf() as session:
        round_ = await session.scalar(select(Round).where(Round.number == number))
        assert round_ is not None, f"Round {number} missing"
        return round_.id


async def get_round10_match_ids(sf: async_sessionmaker[AsyncSession]) -> list[int]:
    async with sf() as session:
        round_ = await session.scalar(select(Round).where(Round.number == 10))
        assert round_ is not None
        matches = (
            await session.scalars(
                select(Match).where(Match.round_id == round_.id).order_by(Match.id)
            )
        ).all()
        return [m.id for m in matches]


async def reset_contest_unlocked(sf: async_sessionmaker[AsyncSession]) -> None:
    async with sf() as session:
        async with session.begin():
            settings = await session.scalar(select(ContestSettings).limit(1))
            if settings:
                settings.is_locked = False
                settings.status = ContestLifecycleStatus.DRAFT.value


async def set_round_draft(sf: async_sessionmaker[AsyncSession], number: int) -> int:
    async with sf() as session:
        async with session.begin():
            round_ = await session.scalar(select(Round).where(Round.number == number))
            assert round_ is not None
            round_.status = RoundStatus.DRAFT.value
            return round_.id


async def ensure_contest_running(
    sf: async_sessionmaker[AsyncSession], client: httpx.AsyncClient
) -> None:
    """Activate round 10 if contest not yet RUNNING (idempotent)."""
    async with sf() as session:
        settings = await session.scalar(select(ContestSettings).limit(1))
        if (
            settings
            and settings.status == ContestLifecycleStatus.RUNNING.value
            and settings.is_locked
        ):
            return

    rid = await set_round_draft(sf, 10)
    await reset_contest_unlocked(sf)
    sup = await api_login(client, "supervisor_api")
    resp = await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/activate",
        headers=auth_header(sup),
    )
    if resp.status_code == 400 and "ACTIVE → ACTIVE" in resp.text:
        async with sf() as session:
            async with session.begin():
                settings = await session.scalar(select(ContestSettings).limit(1))
                round_ = await session.get(Round, rid)
                if settings and round_ and round_.status == RoundStatus.ACTIVE.value:
                    settings.is_locked = True
                    settings.status = ContestLifecycleStatus.RUNNING.value
        return
    assert resp.status_code == 200, resp.text


def _ensure_src_api_importable() -> None:
    """pytest adds tests/api/ to sys.path — it shadows src/api."""
    test_dir = str(Path(__file__).resolve().parent)
    sys.path[:] = [p for p in sys.path if p not in (test_dir, "")]
    for p in (str(_SRC), str(_ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


def _patch_sqlite_grace_datetimes(monkeypatch: pytest.MonkeyPatch) -> None:
    """SQLite may return naive datetimes from TZ columns — normalize for grace checks."""
    import services.contest_lifecycle_service as svc

    _orig = svc.compute_deletable_at

    def _aware_compute(paused_at: datetime | None) -> datetime | None:
        if paused_at is not None and paused_at.tzinfo is None:
            paused_at = paused_at.replace(tzinfo=timezone.utc)
        return _orig(paused_at)

    monkeypatch.setattr(svc, "compute_deletable_at", _aware_compute)


def _patch_deps(monkeypatch: pytest.MonkeyPatch, engine: Any, sf: async_sessionmaker) -> None:
    import api.deps as deps

    monkeypatch.setattr(deps, "_engine", engine)
    monkeypatch.setattr(deps, "_session_factory", sf)


@pytest_asyncio.fixture
async def loaded_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    db_url = f"sqlite+aiosqlite:///{tmp_path}/api_test.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("CONTEST_ALLOW_INSTANT_DELETE", "false")
    from config.settings import get_settings

    get_settings.cache_clear()

    _ensure_src_api_importable()
    await run_load(database_url=db_url, reset=True)
    engine = create_async_engine(db_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    await _seed_test_users(sf)
    await _shift_round10_forward(sf)
    _patch_deps(monkeypatch, engine, sf)
    _patch_sqlite_grace_datetimes(monkeypatch)

    from main import app

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, sf, db_url
    await engine.dispose()


@pytest_asyncio.fixture
async def delete_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    db_url = f"sqlite+aiosqlite:///{tmp_path}/api_delete.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("CONTEST_ALLOW_INSTANT_DELETE", "true")
    from config.settings import get_settings

    get_settings.cache_clear()

    _ensure_src_api_importable()
    await run_load(database_url=db_url, reset=True)
    engine = create_async_engine(db_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    await _seed_test_users(sf)
    await _shift_round10_forward(sf)
    _patch_deps(monkeypatch, engine, sf)

    from main import app

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, sf, db_url
    await engine.dispose()
