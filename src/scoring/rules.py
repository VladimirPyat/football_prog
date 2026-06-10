"""Typed accessor over the rules_json dict.

All numeric scoring constants are read through this class; nothing is hardcoded
in the engine or standings modules.
"""

from __future__ import annotations


class ScoringRules:
    """Wraps the ``scoring_rules`` section of contest_defaults / contest_settings."""

    def __init__(self, rules_json: dict) -> None:
        self._r = rules_json

    # ------------------------------------------------------------------ base points

    @property
    def exact_high_score(self) -> int:
        return int(self._r["scoring_rules"]["base_points"]["exact_high_score"])

    @property
    def exact_score(self) -> int:
        return int(self._r["scoring_rules"]["base_points"]["exact_score"])

    @property
    def diff_plus_outcome(self) -> int:
        return int(self._r["scoring_rules"]["base_points"]["diff_plus_outcome"])

    @property
    def outcome_only(self) -> int:
        return int(self._r["scoring_rules"]["base_points"]["outcome_only"])

    @property
    def miss(self) -> int:
        return int(self._r["scoring_rules"]["base_points"]["miss"])

    # ------------------------------------------------------------------ bonus 1

    @property
    def bonus_1_unique_multiplier_pct(self) -> float:
        return float(
            self._r["scoring_rules"]["bonuses"]["bonus_1_unique_multiplier_pct"]
        )

    # ------------------------------------------------------------------ bonus 2

    @property
    def bonus_2_thresholds(self) -> list[dict]:
        """List of {min_correct_outcomes: int, points: int}, ascending order."""
        return list(self._r["scoring_rules"]["bonuses"]["bonus_2_thresholds"])

    # ------------------------------------------------------------------ bonus 3

    @property
    def bonus_3_rank_points(self) -> dict[str, int]:
        """Keys: '1st', '2nd', '3rd'."""
        return dict(self._r["scoring_rules"]["bonuses"]["bonus_3_rank_points"])

    @property
    def bonus_3_base_threshold_extra(self) -> int:
        return int(
            self._r["scoring_rules"]["bonuses"]["bonus_3_base_threshold_extra"]
        )

    @property
    def bonus_3_extra_points(self) -> int:
        return int(self._r["scoring_rules"]["bonuses"]["bonus_3_extra_points"])
