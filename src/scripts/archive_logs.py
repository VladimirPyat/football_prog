"""Archive application log file when size or age threshold is reached.

Copies ``app.log`` (or ``LOG_FILE``) into ``logs/archive/`` and truncates the
active log so it does not grow without bound.

Usage::

    uv run python src/scripts/archive_logs.py           # archive if triggered
    uv run python src/scripts/archive_logs.py --force   # archive now (non-empty log)
    uv run python src/scripts/archive_logs.py --dry-run # show decision only

Schedule via cron (example — Sunday 03:00)::

    0 3 * * 0 cd /path/to/football_prog && uv run python src/scripts/archive_logs.py

**Note:** truncating the log while the API is running can desync an open
``FileHandler`` file descriptor. Prefer running during a maintenance window or
after stopping Uvicorn; restart the API after archive if logs look stale.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

logger = logging.getLogger(__name__)

LAST_ARCHIVE_MARKER = "last_archive"


def resolve_log_path(log_file: Path) -> Path:
    if log_file.is_absolute():
        return log_file
    return PROJECT_ROOT / log_file


def resolve_archive_dir(archive_dir: Path) -> Path:
    if archive_dir.is_absolute():
        return archive_dir
    return PROJECT_ROOT / archive_dir


def last_archive_time(archive_dir: Path) -> datetime | None:
    marker = archive_dir.parent / LAST_ARCHIVE_MARKER
    if not marker.is_file():
        return None
    raw = marker.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        logger.warning("Invalid timestamp in %s — ignoring", marker)
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def write_last_archive_time(archive_dir: Path, moment: datetime) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    marker = archive_dir.parent / LAST_ARCHIVE_MARKER
    marker.write_text(moment.astimezone(UTC).isoformat(), encoding="utf-8")


def should_archive(
    log_path: Path,
    *,
    max_bytes: int,
    interval_days: int,
    archive_dir: Path,
    now: datetime | None = None,
) -> tuple[bool, str]:
    """Return (True, reason) when log should be copied to archive."""
    if not log_path.is_file():
        return False, "log file does not exist"

    size = log_path.stat().st_size
    if size == 0:
        return False, "log file is empty"

    if size >= max_bytes:
        return True, f"size {size} >= max {max_bytes}"

    moment = now or datetime.now(tz=UTC)
    last = last_archive_time(archive_dir)
    if last is not None:
        if moment - last >= timedelta(days=interval_days):
            return True, f"{interval_days} day(s) since last archive"
        return False, f"last archive {last.isoformat()} — interval not reached"

    log_mtime = datetime.fromtimestamp(log_path.stat().st_mtime, tz=UTC)
    if moment - log_mtime >= timedelta(days=interval_days):
        return True, f"log older than {interval_days} day(s) (no prior archive)"

    return False, "size and age thresholds not reached"


def archive_log(*, force: bool = False, dry_run: bool = False) -> bool:
    """Copy log to archive and truncate active file. Returns True if archived."""
    from config.settings import get_settings

    settings = get_settings()
    log_path = resolve_log_path(settings.log_file)
    archive_dir = resolve_archive_dir(settings.log_archive_dir)

    if not log_path.is_file() or log_path.stat().st_size == 0:
        logger.info("Nothing to archive (%s missing or empty)", log_path)
        return False

    if force:
        reason = "forced"
        do_archive = True
    else:
        do_archive, reason = should_archive(
            log_path,
            max_bytes=settings.log_archive_max_bytes,
            interval_days=settings.log_archive_interval_days,
            archive_dir=archive_dir,
        )

    if not do_archive:
        logger.info("Skip archive: %s", reason)
        return False

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"{log_path.stem}-{stamp}{log_path.suffix}"

    logger.info("Archiving %s → %s (%s)", log_path, target, reason)
    if dry_run:
        return True

    shutil.copy2(log_path, target)
    log_path.open("w", encoding="utf-8").close()
    write_last_archive_time(archive_dir, datetime.now(tz=UTC))
    logger.info("Archived and truncated %s", log_path)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Archive app.log when size or age threshold hit")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Archive now if log is non-empty (ignore thresholds)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print decision without copying or truncating",
    )
    args = parser.parse_args()

    archived = archive_log(force=args.force, dry_run=args.dry_run)
    if args.force and not archived:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
