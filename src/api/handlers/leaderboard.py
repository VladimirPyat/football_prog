"""Shared handlers for leaderboard and results responses."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.leaderboard import LeaderboardOut, RoundResultsOut
from services.leaderboard_service import (
    get_global_leaderboard,
    get_round_leaderboard,
    get_round_results,
)


async def get_global_leaderboard_response(
    session: AsyncSession, contest_id: int
) -> LeaderboardOut:
    data = await get_global_leaderboard(session, contest_id)
    return LeaderboardOut.model_validate(data)


async def get_round_leaderboard_response(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    *,
    viewer_role: str | None = None,
) -> LeaderboardOut:
    data = await get_round_leaderboard(session, contest_id, round_id, viewer_role=viewer_role)
    return LeaderboardOut.model_validate(data)


async def get_round_results_response(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    *,
    viewer_role: str | None = None,
) -> RoundResultsOut:
    data = await get_round_results(session, contest_id, round_id, viewer_role=viewer_role)
    return RoundResultsOut.model_validate(data)
