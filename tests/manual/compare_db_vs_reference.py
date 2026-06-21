#!/usr/bin/env python3
"""Script 2 — read-only DB vs contracted reference CSV comparison."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import get_settings
from tests.api.reference_compare import (
    build_score_lookup,
    compare_leaderboard_counts,
    compare_scores_to_expected,
    load_expected_scores,
    load_leaderboard,
)


async def _run(database_url: str, contest_id: int, expected_path: Path | None) -> int:
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()

    engine = create_async_engine(database_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    expected = load_expected_scores(expected_path)
    login_to_id, round_num_to_id, score_map = await build_score_lookup(sf, contest_id)
    matched, mismatches = compare_scores_to_expected(
        expected, login_to_id, round_num_to_id, score_map
    )
    if mismatches:
        print(f"SCORES FAIL: {len(mismatches)} mismatches (matched {matched}/90)", file=sys.stderr)
        for line in mismatches[:10]:
            print(line, file=sys.stderr)
        await engine.dispose()
        return 1

    lb_matched, lb_mismatches = compare_leaderboard_counts(
        load_leaderboard(), login_to_id, score_map
    )
    if lb_mismatches:
        print(f"LEADERBOARD FAIL: {len(lb_mismatches)} mismatches", file=sys.stderr)
        for line in lb_mismatches:
            print(line, file=sys.stderr)
        await engine.dispose()
        return 1

    print(f"OK scores={matched}/90 leaderboard={lb_matched}/10 contest_id={contest_id}")
    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1.4 Script 2 — DB vs CSV")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./football_verify.db"))
    parser.add_argument("--contest-id", type=int, default=int(os.environ.get("CONTEST_ID", "1")))
    parser.add_argument("--expected-scores", type=Path, default=None)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.database_url, args.contest_id, args.expected_scores)))


if __name__ == "__main__":
    main()
