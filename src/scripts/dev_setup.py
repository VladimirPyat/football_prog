"""One-shot local dev bootstrap: deps, migrations, test data, admin users, RUNNING contest.

Usage::

    uv run python src/scripts/dev_setup.py              # full (default)
    uv run python src/scripts/dev_setup.py --minimal
    uv run python src/scripts/dev_setup.py --check
    uv run python src/scripts/dev_setup.py --ensure-running-only

Full mode order (important):
  1. alembic upgrade head
  2. load_test_data.py --reset   (wipes users table)
  3. bootstrap_users.py          (restores admin/supervisor from .env)
  4. ensure contest id=1 RUNNING + is_locked for GET /contests/public (B2)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

logger = logging.getLogger(__name__)

DEFAULT_CONTEST_ID = 1


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    logger.info("→ %s", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=True)


def check_prerequisites() -> list[str]:
    """Return list of warnings (empty if all OK)."""
    warnings: list[str] = []
    if shutil.which("uv") is None:
        warnings.append("uv not found — install from https://docs.astral.sh/uv/")
    if sys.version_info < (3, 12):
        warnings.append(f"Python {sys.version_info.major}.{sys.version_info.minor} — need ≥ 3.12")
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        warnings.append(".env missing — copy .env.example and set SEED_*_PASSWORD")
    elif env_file.read_text(encoding="utf-8").find("your-admin-password-here") >= 0:
        warnings.append(".env still has placeholder SEED_ADMIN_PASSWORD — edit before bootstrap")
    node = shutil.which("node")
    if node is None:
        warnings.append("node not found — required for frontend (Stage 2+)")
    return warnings


async def ensure_dev_contest_running(contest_id: int = DEFAULT_CONTEST_ID) -> None:
    """Set contest RUNNING + is_locked so public discovery and frontend dev work."""
    from sqlalchemy import select

    from database.engine import create_engine, create_session_factory
    from database.models import Contest, ContestLifecycleStatus, Round, RoundStatus

    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        async with session.begin():
            contest = await session.get(Contest, contest_id)
            if contest is None:
                logger.warning("Contest id=%s not found — skip ensure RUNNING", contest_id)
                await engine.dispose()
                return

            round_10 = await session.scalar(
                select(Round).where(
                    Round.contest_id == contest_id,
                    Round.number == 10,
                )
            )
            if round_10 and round_10.status != RoundStatus.ACTIVE.value:
                round_10.status = RoundStatus.ACTIVE.value
                logger.info("Round 10 set ACTIVE")

            contest.status = ContestLifecycleStatus.RUNNING.value
            contest.is_locked = True
            logger.info(
                "Contest id=%s → status=RUNNING, is_locked=true",
                contest_id,
            )
    await engine.dispose()


def run_full_setup(*, reset: bool) -> None:
    _run(["uv", "sync"])
    _run(["uv", "run", "alembic", "upgrade", "head"])
    loader_cmd = ["uv", "run", "python", "src/scripts/load_test_data.py"]
    if reset:
        loader_cmd.append("--reset")
    _run(loader_cmd)
    _run(["uv", "run", "python", "src/scripts/bootstrap_users.py"])
    asyncio.run(ensure_dev_contest_running())


def run_minimal_setup() -> None:
    _run(["uv", "sync"])
    _run(["uv", "run", "alembic", "upgrade", "head"])
    _run(["uv", "run", "python", "src/scripts/seed.py"])
    _run(["uv", "run", "python", "src/scripts/bootstrap_users.py"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Bootstrap local dev environment (migrations, data, admin users)",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="seed.py + bootstrap only (no CSV loader / user user)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Full mode: load test data without --reset (append; may fail if DB not empty)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check prerequisites only; exit 0 with warnings printed",
    )
    parser.add_argument(
        "--ensure-running-only",
        action="store_true",
        help="Only set contest 1 to RUNNING+locked (after manual loader/bootstrap)",
    )
    args = parser.parse_args()

    warnings = check_prerequisites()
    for w in warnings:
        logger.warning("⚠ %s", w)

    if args.check:
        if warnings:
            logger.info("Check complete with %d warning(s)", len(warnings))
        else:
            logger.info("Prerequisites OK")
        sys.exit(0)

    if args.ensure_running_only:
        asyncio.run(ensure_dev_contest_running())
        print("✅ Contest dev state ensured (RUNNING + locked)")
        sys.exit(0)

    try:
        if args.minimal:
            run_minimal_setup()
        else:
            run_full_setup(reset=not args.no_reset)
    except subprocess.CalledProcessError as exc:
        print(f"❌ Setup failed (exit {exc.returncode})", file=sys.stderr)
        sys.exit(exc.returncode or 1)

    print("✅ Dev setup complete")
    print("   API:  uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000")
    print("   UI:   cd frontend && npm install && npm run dev")
    print("   Docs: manuals/DEV_SETUP.md")


if __name__ == "__main__":
    main()
