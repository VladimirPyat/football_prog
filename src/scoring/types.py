"""Input/output dataclasses and enums for the scoring engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Category(StrEnum):
    EXACT_HIGH = "exact_high"
    EXACT = "exact"
    DIFF = "diff"
    OUTCOME = "outcome"
    MISS = "miss"


@dataclass(frozen=True)
class MatchResult:
    match_id: int
    score1: int | None  # None => not finished / void => excluded from scoring
    score2: int | None
    is_scorable: bool  # True only when FINISHED and both scores are not None


@dataclass(frozen=True)
class UserPrediction:
    user_id: int
    match_id: int
    score1: int  # 0 is a real value, not a sentinel
    score2: int


@dataclass(frozen=True)
class MatchScore:
    match_id: int
    category: Category
    base_points: int
    bonus1_points: int  # unique-correct-outcome bonus earned on this match


@dataclass(frozen=True)
class UserRoundScore:
    user_id: int
    base_points: int
    count_exact_high: int
    count_exact: int
    count_diff: int
    count_outcome: int
    correct_outcomes: int  # matches where base_points >= 4
    bonus1: int
    bonus2: int
    bonus3: int
    total_without_bonus3: int  # base + bonus1 + bonus2
    total_with_bonus3: int  # total_without_bonus3 + bonus3
    round_rank: int  # DENSE rank by total_with_bonus3 (ties share the same rank)
    per_match: tuple[MatchScore, ...]


@dataclass
class StandingRow:
    user_id: int
    total_points: int
    exact_scores_count: int  # sum of (count_exact_high + count_exact) across all rounds
    total_without_bonuses: int  # sum of base_points only (no bonuses)
    correct_diffs_count: int  # sum of count_diff across rounds
    exact_high_count: int
    exact_count: int
    diff_count: int
    outcome_count: int
    total_predictions: int  # total prediction rows across all scored rounds
    rank: int
    tiebreaker_status: str | None  # "manual_override" when manual key decided order
