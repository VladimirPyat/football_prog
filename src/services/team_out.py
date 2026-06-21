"""Helpers for TeamOut serialization with resolved logo URLs."""

from __future__ import annotations

from config.settings import Settings, get_settings
from database.models import Team
from schemas.contest import TeamOut
from services.team_logo_service import resolve_team_logo_url


def team_to_out(team: Team, settings: Settings | None = None) -> TeamOut:
    """Build TeamOut with default logo URL when DB value is NULL."""
    cfg = settings or get_settings()
    base = TeamOut.model_validate(team)
    return base.model_copy(update={"logo_url": resolve_team_logo_url(team.logo_url, cfg)})
