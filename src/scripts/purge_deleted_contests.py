"""CLI: hard-delete soft-deleted contests from the database.

Examples:
    uv run python src/scripts/purge_deleted_contests.py --dry-run
    uv run python src/scripts/purge_deleted_contests.py
    uv run python src/scripts/purge_deleted_contests.py --before 2026-01-01
    uv run python src/scripts/purge_deleted_contests.py --all-deleted --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.settings import get_settings  # noqa: E402

from database.engine import create_engine, create_session_factory  # noqa: E402
from services.contest_purge_service import (  # noqa: E402
    list_purge_candidates,
    purge_deleted_contests,
)


def _parse_before(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    before = _parse_before(args.before) if args.before else None
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        if args.dry_run:
            candidates = await list_purge_candidates(
                session,
                before=before,
                include_all_deleted=args.all_deleted,
            )
            if not candidates:
                print("No contests eligible for purge.")
                return 0
            print(f"Would purge {len(candidates)} contest(s):")
            for c in candidates:
                print(f"  id={c.id} name={c.name!r} deleted_at={c.deleted_at}")
            return 0

        purged = await purge_deleted_contests(
            session,
            before=before,
            include_all_deleted=args.all_deleted,
            dry_run=False,
        )
        await session.commit()
        print(f"Purged {len(purged)} contest(s): {purged}")
        if not args.all_deleted and not args.before:
            days = settings.contest_purge_retention_seconds / 86400
            print(f"(retention default: {days:.0f} days — CONTEST_PURGE_RETENTION_SECONDS)")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Hard-delete soft-deleted contests")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List contests that would be purged without deleting",
    )
    parser.add_argument(
        "--before",
        metavar="ISO-DATE",
        help="Purge contests soft-deleted before this datetime (ISO 8601)",
    )
    parser.add_argument(
        "--all-deleted",
        action="store_true",
        help="Purge ALL soft-deleted contests regardless of retention window",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
