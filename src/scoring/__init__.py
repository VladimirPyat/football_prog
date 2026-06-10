"""Scoring engine — pure, deterministic, no I/O."""

from src.scoring.engine import score_round
from src.scoring.standings import build_standings
from src.scoring.types import (
    Category,
    MatchResult,
    MatchScore,
    StandingRow,
    UserPrediction,
    UserRoundScore,
)

__all__ = [
    "Category",
    "MatchResult",
    "MatchScore",
    "StandingRow",
    "UserPrediction",
    "UserRoundScore",
    "score_round",
    "build_standings",
]
