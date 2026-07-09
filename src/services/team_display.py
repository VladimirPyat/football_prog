"""Team label helpers for match API payloads."""

from __future__ import annotations

import logging

from database.models import Team

logger = logging.getLogger(__name__)


def _team_name(teams: dict[int, Team], team_id: int) -> str:
    team = teams.get(team_id)
    if team is None:
        logger.warning("team name missing team_id=%s — using id as fallback", team_id)
        return str(team_id)
    return team.name


def _team_short_name(teams: dict[int, Team], team_id: int) -> str:
    team = teams.get(team_id)
    if team is None:
        logger.warning("team short_name missing team_id=%s — using id as fallback", team_id)
        return str(team_id)
    return team.short_name


def match_team_fields(teams: dict[int, Team], team1_id: int, team2_id: int) -> dict[str, str]:
    """Full and short display names for a match pair."""
    return {
        "team1": _team_name(teams, team1_id),
        "team2": _team_name(teams, team2_id),
        "team1_short": _team_short_name(teams, team1_id),
        "team2_short": _team_short_name(teams, team2_id),
    }
