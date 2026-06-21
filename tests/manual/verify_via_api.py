#!/usr/bin/env python3
"""Script 1 — drive contest-scoped API without reading expected oracle CSVs."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings
from database.base import Base
from tests.api.conftest import (
    _seed_test_users,
    build_contracted_contest_via_http,
    calculate_rounds_via_http,
    contest_url,
)


async def _run(database_url: str, base_url: str, bootstrap: str) -> int:
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("CONTEST_ALLOW_INSTANT_DELETE", "false")
    get_settings.cache_clear()

    engine = create_async_engine(database_url)
    if bootstrap == "empty":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    elif bootstrap == "load":
        from scripts.load_test_data import run_load

        await run_load(database_url=database_url, reset=True)
    else:
        print(f"Unknown bootstrap mode: {bootstrap}", file=sys.stderr)
        return 2

    sf = async_sessionmaker(engine, expire_on_commit=False)
    await _seed_test_users(sf)

    import api.deps as deps

    deps._engine = engine
    deps._session_factory = sf

    from main import app

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        if bootstrap == "empty":
            contest_id = await build_contracted_contest_via_http(client, sf)
        else:
            contest_id = 1
            await calculate_rounds_via_http(client, sf, contest_id)

        lb = await client.get(contest_url(contest_id, "/leaderboard"))
        if lb.status_code != 200:
            print(f"Leaderboard GET failed: {lb.status_code} {lb.text}", file=sys.stderr)
            return 1

        rounds = await client.get(contest_url(contest_id, "/rounds"))
        if rounds.status_code != 200:
            print(f"Rounds GET failed: {rounds.status_code}", file=sys.stderr)
            return 1

        print(f"OK contest_id={contest_id} rounds={len(rounds.json())} leaderboard_rows={len(lb.json()['leaderboard'])}")

    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1.4 Script 1 — HTTP verification")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./football_verify.db"))
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", "http://test"))
    parser.add_argument(
        "--bootstrap",
        choices=("empty", "load"),
        default=os.environ.get("VERIFY_BOOTSTRAP", "load"),
        help="empty=full HTTP setup; load=CSV loader + HTTP calculate",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.database_url, args.base_url, args.bootstrap)))


if __name__ == "__main__":
    main()
