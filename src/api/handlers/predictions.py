"""Shared handlers for predictions views."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from database.models import Match, Round, Team, User
from schemas.predictions import RoundPredictionsView
from services.prediction_service import visible_predictions

logger = logging.getLogger(__name__)


def _team_display_name(teams: dict[int, Team], team_id: int) -> str:
    team = teams.get(team_id)
    if team is None:
        logger.warning("team name missing team_id=%s — using id as fallback", team_id)
        return str(team_id)
    return team.name


async def build_round_predictions_view(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    user: User,
) -> RoundPredictionsView:
    """Build predictions view for a round with visibility rules."""
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не найден")

    now = datetime.now(timezone.utc)
    deadline = round_.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    matches = (
        await session.scalars(select(Match).where(Match.round_id == round_id))
    ).all()
    team_ids = {m.team1_id for m in matches} | {m.team2_id for m in matches}
    teams = {
        t.id: t
        for t in (await session.scalars(select(Team).where(Team.id.in_(team_ids)))).all()
    }

    match_out = []
    for m in matches:
        match_out.append(
            {
                "id": m.id,
                "team1": _team_display_name(teams, m.team1_id),
                "team2": _team_display_name(teams, m.team2_id),
                "date_time": m.date_time.isoformat(),
                "score1": m.score1,
                "score2": m.score2,
                "status": m.status,
            }
        )

    raw = await visible_predictions(session, contest_id, round_id, user.role, user.id)
    users = {u.id: u for u in (await session.scalars(select(User))).all()}
    by_user: dict[int, list] = {}
    for item in raw:
        uid = item["user_id"]
        by_user.setdefault(uid, []).append(item)

    entries = []
    for uid, preds in by_user.items():
        u = users.get(uid)
        name = f"{u.first_name} {u.last_name}" if u else str(uid)
        if preds and "match_id" in preds[0]:
            entries.append(
                {
                    "user_id": uid,
                    "user_name": name,
                    "submitted": True,
                    "predictions": [
                        {
                            "match_id": p["match_id"],
                            "score1": p.get("score1"),
                            "score2": p.get("score2"),
                        }
                        for p in preds
                    ],
                }
            )
        else:
            entries.append({"user_id": uid, "user_name": name, "submitted": True, "predictions": None})

    return RoundPredictionsView(
        round_id=round_id,
        deadline_passed=now >= deadline,
        matches=match_out,
        entries=entries,
    )
