"""Smoke tests for Stage 1.2.1 migration upgrade/downgrade."""

from __future__ import annotations

import subprocess
import sys


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_migration_upgrade_downgrade_cycle() -> None:
    """Alembic upgrade head and downgrade -1 must succeed."""
    upgrade = _run_alembic("upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = _run_alembic("downgrade", "-1")
    assert downgrade.returncode == 0, downgrade.stderr

    re_upgrade = _run_alembic("upgrade", "head")
    assert re_upgrade.returncode == 0, re_upgrade.stderr
