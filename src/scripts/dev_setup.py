"""One-shot local dev bootstrap: deps, migrations, test data, admin users, RUNNING contest.

Usage::

    uv run python src/scripts/dev_setup.py              # full (default)
    uv run python src/scripts/dev_setup.py --run        # full setup + start API & UI
    uv run python src/scripts/dev_setup.py --run-only   # start API & UI (skip setup)
    uv run python src/scripts/dev_setup.py --minimal
    uv run python src/scripts/dev_setup.py --check
    uv run python src/scripts/dev_setup.py --check-ports
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
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

logger = logging.getLogger(__name__)

DEFAULT_CONTEST_ID = 1
API_HOST = "127.0.0.1"
API_PORT = 8000
UI_HOST = "127.0.0.1"
UI_PORT = 3000
STARTUP_TIMEOUT_SEC = 90.0

DEV_PORTS: tuple[tuple[str, int, str], ...] = (
    (API_HOST, API_PORT, "API"),
    (UI_HOST, UI_PORT, "UI"),
)


def is_port_in_use(host: str, port: int) -> bool:
    """True when something is already accepting TCP connections on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def check_dev_ports() -> list[str]:
    """Return human-readable lines for ports that are already in use."""
    busy: list[str] = []
    for host, port, label in DEV_PORTS:
        if is_port_in_use(host, port):
            busy.append(f"{label}: {host}:{port} is in use")
    return busy


def assert_dev_ports_free() -> None:
    """Abort before starting dev servers if API or UI port is taken."""
    busy = check_dev_ports()
    if not busy:
        return
    print("❌ Cannot start dev stack — port(s) already in use:", file=sys.stderr)
    for line in busy:
        print(f"   {line}", file=sys.stderr)
    print(
        "   Check:  uv run python src/scripts/dev_setup.py --check-ports",
        file=sys.stderr,
    )
    print(
        "   Hint:   stop the other stack (Ctrl+C in its terminal) or free the port:",
        file=sys.stderr,
    )
    print("           ss -lntp | grep -E ':3000|:8000'", file=sys.stderr)
    sys.exit(1)


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    logger.info("→ %s", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=True)


def check_prerequisites(*, require_frontend: bool = False) -> list[str]:
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
    if require_frontend:
        if shutil.which("node") is None:
            warnings.append("node not found — required for --run")
        if shutil.which("npm") is None:
            warnings.append("npm not found — required for --run")
        if not FRONTEND_DIR.is_dir():
            warnings.append("frontend/ missing — Stage 2.1 scaffold required for --run")
    elif shutil.which("node") is None:
        warnings.append("node not found — required for frontend (Stage 2+)")
    return warnings


def ensure_frontend_env() -> None:
    """Create frontend/.env.local from example when missing."""
    env_local = FRONTEND_DIR / ".env.local"
    env_example = FRONTEND_DIR / ".env.local.example"
    if env_local.exists():
        return
    if not env_example.is_file():
        raise SystemExit("frontend/.env.local.example missing — cannot start UI")
    shutil.copy(env_example, env_local)
    logger.info("Created frontend/.env.local from .env.local.example")


def ensure_frontend_deps() -> None:
    """Run npm install on first use."""
    if (FRONTEND_DIR / "node_modules").is_dir():
        return
    logger.info("→ npm install (first run)")
    _run(["npm", "install"], cwd=FRONTEND_DIR)


def _wait_for_http(url: str, *, timeout: float, label: str) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    logger.info("%s ready: %s", label, url)
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    logger.warning("%s not ready within %.0fs (%s)", label, timeout, url)
    return False


def _terminate_processes(processes: list[subprocess.Popen[bytes]]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        if proc.poll() is not None:
            continue
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run_dev_servers() -> None:
    """Start uvicorn and Next.js dev server; block until Ctrl+C or a child exits."""
    assert_dev_ports_free()
    ensure_frontend_env()
    ensure_frontend_deps()

    api_cmd = [
        "uv",
        "run",
        "uvicorn",
        "main:app",
        "--reload",
        "--reload-dir",
        "src",
        "--reload-dir",
        "main.py",
        "--host",
        API_HOST,
        "--port",
        str(API_PORT),
    ]
    # Avoid app.log feedback loop with watchfiles during hot reload (see logging_config).
    api_env = {**os.environ, "LOG_TO_FILE": "false"}
    ui_cmd = ["npm", "run", "dev"]

    logger.info("Starting API → http://%s:%s", API_HOST, API_PORT)
    logger.info("Starting UI  → http://%s:%s", UI_HOST, UI_PORT)

    processes: list[subprocess.Popen[bytes]] = []
    shutting_down = False

    def shutdown(signum: int | None = None, _frame: object | None = None) -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        if signum is not None:
            logger.info("Stopping dev servers (signal %s)...", signum)
        else:
            logger.info("Stopping dev servers...")
        _terminate_processes(processes)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    api_proc = subprocess.Popen(api_cmd, cwd=PROJECT_ROOT, env=api_env)
    ui_proc = subprocess.Popen(ui_cmd, cwd=FRONTEND_DIR)
    processes.extend([api_proc, ui_proc])

    api_ok = _wait_for_http(
        f"http://{API_HOST}:{API_PORT}/health",
        timeout=STARTUP_TIMEOUT_SEC,
        label="API",
    )
    ui_ok = _wait_for_http(
        f"http://{UI_HOST}:{UI_PORT}/",
        timeout=STARTUP_TIMEOUT_SEC,
        label="UI",
    )

    if api_ok and ui_ok:
        print("\n✅ Dev stack running")
        print(f"   UI:  http://{UI_HOST}:{UI_PORT}/")
        print(f"   API: http://{API_HOST}:{API_PORT}/health")
        print("   Press Ctrl+C to stop both servers")
        _print_manual_qa_cheatsheet()
        print()
    elif not api_ok or not ui_ok:
        print("\n⚠ One or more servers did not become ready — check logs above", file=sys.stderr)

    exit_code = 0
    try:
        while True:
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    name = "API" if proc is api_proc else "UI"
                    logger.error("%s exited with code %s", name, code)
                    exit_code = code or 1
                    shutdown()
                    sys.exit(exit_code)
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()
        sys.exit(0)
    finally:
        shutdown()


async def ensure_dev_contest_running(
    contest_id: int = DEFAULT_CONTEST_ID,
    *,
    e2e: bool = False,
) -> None:
    """Set contest RUNNING + is_locked; E2E profile keeps round 10 ACTIVE with future deadline."""
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from database.engine import create_engine, create_session_factory
    from database.models import Contest, ContestLifecycleStatus, Match, Round, RoundStatus

    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        async with session.begin():
            contest = await session.get(Contest, contest_id)
            if contest is None:
                logger.warning("Contest id=%s not found — skip ensure RUNNING", contest_id)
                await engine.dispose()
                return

            if e2e:
                round_10 = await session.scalar(
                    select(Round).where(
                        Round.contest_id == contest_id,
                        Round.number == 10,
                    )
                )
                if round_10:
                    matches = (
                        await session.scalars(select(Match).where(Match.round_id == round_10.id))
                    ).all()
                    if matches:
                        base = datetime.now(UTC) + timedelta(days=14)
                        for i, match in enumerate(sorted(matches, key=lambda m: m.id)):
                            match.date_time = base + timedelta(hours=i)
                        earliest = min(m.date_time for m in matches)
                        deadline_rule_hours: int = contest.rules_json["contest_structure"][
                            "deadline_rule_hours"
                        ]
                        round_10.deadline = earliest - timedelta(hours=deadline_rule_hours)
                    round_10.status = RoundStatus.ACTIVE.value
                    logger.info("Round 10 shifted forward and set ACTIVE (e2e profile)")

            contest.status = ContestLifecycleStatus.RUNNING.value
            contest.is_locked = True
            logger.info(
                "Contest id=%s → status=RUNNING, is_locked=true",
                contest_id,
            )
    await engine.dispose()


def _finalize_manual_fixture() -> None:
    from scripts.finalize_dev_fixture import finalize_dev_fixture

    asyncio.run(finalize_dev_fixture(contest_id=DEFAULT_CONTEST_ID, profile="manual"))


def run_full_setup(*, reset: bool, e2e: bool = False) -> None:
    _run(["uv", "sync"])
    _run(["uv", "run", "alembic", "upgrade", "head"])
    loader_cmd = ["uv", "run", "python", "src/scripts/load_test_data.py"]
    if reset:
        loader_cmd.append("--reset")
    _run(loader_cmd)
    _run(["uv", "run", "python", "src/scripts/bootstrap_users.py"])
    asyncio.run(ensure_dev_contest_running(e2e=e2e))
    if not e2e:
        _finalize_manual_fixture()


def run_minimal_setup() -> None:
    _run(["uv", "sync"])
    _run(["uv", "run", "alembic", "upgrade", "head"])
    _run(["uv", "run", "python", "src/scripts/seed.py"])
    _run(["uv", "run", "python", "src/scripts/bootstrap_users.py"])


def _print_manual_qa_cheatsheet() -> None:
    """Commands for manual supervisor QA (also printed after dev stack starts)."""
    print("\n--- Manual QA helpers ---")
    print("Reset DB to demo fixture (contest id=1, wipes loader data):")
    print("  uv run python src/scripts/dev_setup.py")
    print("  # or loader only: uv run python src/scripts/load_test_data.py --reset")
    print("     && uv run python src/scripts/bootstrap_users.py")
    print("     && uv run python src/scripts/dev_setup.py --ensure-running-only")
    print("")
    print("Accept all pending invites for a contest (no SMTP):")
    print("  uv run python src/scripts/dev_invite_setup.py list-pending")
    print("  uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id <ID>")
    print("  # password: SEED_SUPERVISOR_PASSWORD from .env (or --password)")
    print("")
    print("Remove soft-deleted contests from DB (hard purge):")
    print("  uv run python src/scripts/purge_deleted_contests.py --all-deleted --dry-run")
    print("  uv run python src/scripts/purge_deleted_contests.py --all-deleted")
    print("  # UI: supervisor «Удалить конкурс» hides draft; ADMIN restores at /admin/lifecycle")
    print("")
    print("Full reference: manuals/DEV_SETUP.md#manual-qa-cheatsheet")


def _print_manual_start_hint() -> None:
    print("✅ Dev setup complete")
    print("   API:  uv run uvicorn main:app --reload --reload-dir src --reload-dir main.py --host 127.0.0.1 --port 8000")
    print("   UI:   cd frontend && npm install && npm run dev")
    print("   Or:   uv run python src/scripts/dev_setup.py --run-only")
    _print_manual_qa_cheatsheet()


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
        "--check-ports",
        action="store_true",
        help="Check API (:8000) and UI (:3000) are free; exit 1 if either is in use",
    )
    parser.add_argument(
        "--ensure-running-only",
        action="store_true",
        help="RUNNING+locked and manual dev fixture (or e2e round-10 ACTIVE with --e2e)",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="E2E profile: round 10 ACTIVE with future deadline; skip finalize fixture",
    )
    parser.add_argument(
        "--finalize-fixture-only",
        action="store_true",
        help="Run finalize_dev_fixture on existing DB (repair without servers)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="After setup, start API (:8000) and frontend dev server (:3000)",
    )
    parser.add_argument(
        "--run-only",
        action="store_true",
        help="Skip setup; only start API and frontend dev servers",
    )
    args = parser.parse_args()

    if args.run and args.run_only:
        parser.error("--run and --run-only are mutually exclusive")

    require_frontend = args.run or args.run_only
    warnings = check_prerequisites(require_frontend=require_frontend)
    for w in warnings:
        logger.warning("⚠ %s", w)

    if args.check:
        if warnings:
            logger.info("Check complete with %d warning(s)", len(warnings))
        else:
            logger.info("Prerequisites OK")
        sys.exit(0)

    if args.check_ports:
        busy = check_dev_ports()
        if busy:
            for line in busy:
                print(f"❌ {line}")
            sys.exit(1)
        for host, port, label in DEV_PORTS:
            print(f"✅ {label}: {host}:{port} is free")
        sys.exit(0)

    if args.finalize_fixture_only:
        _finalize_manual_fixture()
        print("✅ Dev fixture finalized (manual profile)")
        sys.exit(0)

    if args.ensure_running_only:
        asyncio.run(ensure_dev_contest_running(e2e=args.e2e))
        if not args.e2e:
            _finalize_manual_fixture()
            print("✅ Contest dev state ensured (RUNNING + manual fixture)")
        else:
            print("✅ Contest dev state ensured (RUNNING + e2e round 10 ACTIVE)")
        sys.exit(0)

    if args.run_only:
        if require_frontend and any(
            "frontend/" in w or "npm not found" in w or "node not found" in w for w in warnings
        ):
            print("❌ Cannot start dev servers — fix prerequisites above", file=sys.stderr)
            sys.exit(1)
        run_dev_servers()
        return

    try:
        if args.minimal:
            run_minimal_setup()
        else:
            run_full_setup(reset=not args.no_reset, e2e=args.e2e)
    except subprocess.CalledProcessError as exc:
        print(f"❌ Setup failed (exit {exc.returncode})", file=sys.stderr)
        sys.exit(exc.returncode or 1)

    if args.run:
        if require_frontend and any(
            "frontend/" in w or "npm not found" in w or "node not found" in w for w in warnings
        ):
            print("❌ Setup OK but cannot start servers — fix prerequisites above", file=sys.stderr)
            sys.exit(1)
        run_dev_servers()
        return

    _print_manual_start_hint()


if __name__ == "__main__":
    main()
