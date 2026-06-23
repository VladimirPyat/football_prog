"""Unit tests for log archive threshold logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.archive_logs import (
    LAST_ARCHIVE_MARKER,
    should_archive,
    write_last_archive_time,
)


def test_should_archive_when_size_exceeds_max(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("x" * 100, encoding="utf-8")
    archive_dir = tmp_path / "archive"

    do_archive, reason = should_archive(
        log_path,
        max_bytes=50,
        interval_days=7,
        archive_dir=archive_dir,
    )

    assert do_archive is True
    assert "size" in reason


def test_should_archive_when_interval_elapsed_since_marker(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("hello", encoding="utf-8")
    archive_dir = tmp_path / "archive"
    write_last_archive_time(archive_dir, datetime.now(tz=UTC) - timedelta(days=8))

    do_archive, reason = should_archive(
        log_path,
        max_bytes=10_000,
        interval_days=7,
        archive_dir=archive_dir,
        now=datetime.now(tz=UTC),
    )

    assert do_archive is True
    assert "since last archive" in reason


def test_should_skip_empty_log(tmp_path: Path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text("", encoding="utf-8")

    do_archive, reason = should_archive(
        log_path,
        max_bytes=1,
        interval_days=1,
        archive_dir=tmp_path / "archive",
    )

    assert do_archive is False
    assert "empty" in reason


def test_last_archive_marker_written(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    moment = datetime(2026, 6, 24, 12, 0, 0, tzinfo=UTC)
    write_last_archive_time(archive_dir, moment)
    marker = tmp_path / LAST_ARCHIVE_MARKER
    assert marker.is_file()
    assert "2026-06-24" in marker.read_text(encoding="utf-8")
