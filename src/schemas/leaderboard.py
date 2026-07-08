"""Pydantic schemas for leaderboard and results."""

from __future__ import annotations

from pydantic import BaseModel


class ScoreDetailOut(BaseModel):
    user_id: int
    user_name: str
    points_base: int
    bonus1: int
    bonus2: int
    bonus3: int
    total_without_bonus3: int
    total_bonus_points: int
    total_with_bonus3: int
    correct_outcomes: int
    rank: int
    predictions_count: int
    exceptional_tiebreak_points: int = 0
    tiebreaker_status: str | None = None
    count_exact_high: int = 0
    count_exact: int = 0
    count_diff: int = 0
    count_outcome: int = 0


class LeaderboardOut(BaseModel):
    contest_id: int | None = None
    round_id: int | None = None
    round_number: int | None = None
    bonuses_pending: bool = False
    bonuses_pending_message: str | None = None
    leaderboard: list[ScoreDetailOut]


class MatchPointsOut(BaseModel):
    match_id: int
    base_points: int | None


class RoundResultRowOut(BaseModel):
    user_id: int
    user_name: str
    points: list[MatchPointsOut]
    bonus1: int
    bonus2: int
    bonus3: int | None = None
    total_without_bonus3: int
    total: int
    correct_outcomes: int


class RoundResultsOut(BaseModel):
    round_id: int
    matches: list[dict]
    results: list[RoundResultRowOut]
