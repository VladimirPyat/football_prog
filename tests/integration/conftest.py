"""Shared fixtures for Stage 1.2 integration tests.

Two fixture families:
  loaded_db  — full contracted test data in an isolated SQLite file (function-scoped).
  minimal_db — bare in-memory SQLite with schema only; for synthetic-data tests.
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.base import Base
from scripts.load_test_data import run_load


@pytest_asyncio.fixture
async def loaded_db(tmp_path):
    """Isolated SQLite DB fully loaded via load_test_data.py --reset.

    Yields (session_factory, engine, db_url).
    Each test that uses this fixture gets a fresh copy of the loaded data.
    """
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    await run_load(database_url=db_url, reset=True)

    engine = create_async_engine(db_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    yield sf, engine, db_url
    await engine.dispose()


@pytest_asyncio.fixture
async def minimal_db():
    """In-memory SQLite DB with schema only (no data).  For deadline / batch / status tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, expire_on_commit=False)
    yield sf
    await engine.dispose()
