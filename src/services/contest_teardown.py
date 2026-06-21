"""FK-safe contest data wipe and re-seed."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.models import (
    Contest,
    ContestLifecycleStatus,
    ContestParticipant,
    Match,
    Prediction,
    Round,
    Score,
    Team,
)


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


async def wipe_contest_data(
    session: AsyncSession, contest_id: int, *, keep_admin_users: bool = True
) -> None:
    """Delete one contest's operational data in FK-safe dependency order."""
    del keep_admin_users  # global users retained; only contest-scoped rows removed
    round_ids = list(
        await session.scalars(select(Round.id).where(Round.contest_id == contest_id))
    )
    if round_ids:
        await session.execute(delete(Prediction).where(Prediction.round_id.in_(round_ids)))
        await session.execute(delete(Score).where(Score.round_id.in_(round_ids)))
        await session.execute(delete(Match).where(Match.round_id.in_(round_ids)))
    await session.execute(delete(Round).where(Round.contest_id == contest_id))
    await session.execute(delete(Team).where(Team.contest_id == contest_id))
    await session.execute(
        delete(ContestParticipant).where(ContestParticipant.contest_id == contest_id)
    )


async def reset_contest_to_draft(session: AsyncSession, contest_id: int) -> Contest:
    """Wipe contest operational data and reset contest row to DRAFT defaults."""
    settings_cfg = get_settings()
    data = _load_contest_defaults(settings_cfg.contest_defaults_path)
    structure = data["contest_structure"]

    await wipe_contest_data(session, contest_id)

    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise ValueError(f"Contest {contest_id} not found")

    contest.is_locked = False
    contest.status = ContestLifecycleStatus.DRAFT
    contest.paused_at = None
    contest.finished_at = None
    contest.total_teams = structure["total_teams"]
    contest.matches_per_round = structure["matches_per_round"]
    contest.total_rounds = structure["total_rounds"]
    contest.is_round_robin = structure["is_round_robin"]
    contest.rules_json = _build_rules_json(data)
    return contest


async def reseed_contest(session: AsyncSession, *, name: str = "Default") -> Contest:
    """Insert fresh DRAFT contest from contest_defaults.json."""
    settings_cfg = get_settings()
    data = _load_contest_defaults(settings_cfg.contest_defaults_path)
    structure = data["contest_structure"]
    contest = Contest(
        name=name,
        slug=None,
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
    session.add(contest)
    await session.flush()
    return contest
