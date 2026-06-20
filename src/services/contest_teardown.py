"""FK-safe contest data wipe and re-seed."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.models import ContestLifecycleStatus, ContestSettings


def _build_rules_json(data: dict) -> dict:
    return {
        "scoring_rules": data["scoring_rules"],
        "tiebreakers": data["tiebreakers"],
        "constraints": data["constraints"],
        "contest_structure": data["contest_structure"],
    }


def _load_contest_defaults(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


async def wipe_contest_data(session: AsyncSession, *, keep_admin_users: bool = True) -> None:
    """Delete contest data in FK-safe dependency order."""
    for table in ("predictions", "scores", "matches", "rounds", "contacts"):
        await session.execute(text(f"DELETE FROM {table}"))  # noqa: S608

    if keep_admin_users:
        await session.execute(text("DELETE FROM users WHERE role != 'ADMIN'"))
    else:
        await session.execute(text("DELETE FROM users"))

    await session.execute(text("DELETE FROM teams"))
    await session.execute(text("DELETE FROM contest_settings"))


async def reseed_contest_settings(session: AsyncSession) -> ContestSettings:
    """Insert fresh DRAFT contest_settings from contest_defaults.json."""
    settings_cfg = get_settings()
    data = _load_contest_defaults(settings_cfg.contest_defaults_path)
    structure = data["contest_structure"]
    settings = ContestSettings(
        is_locked=False,
        status=ContestLifecycleStatus.DRAFT,
        paused_at=None,
        finished_at=None,
        total_teams=structure["total_teams"],
        matches_per_round=structure["matches_per_round"],
        total_rounds=structure["total_rounds"],
        is_round_robin=structure["is_round_robin"],
        rules_json=_build_rules_json(data),
    )
    session.add(settings)
    await session.flush()
    return settings
