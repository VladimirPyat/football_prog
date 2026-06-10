"""Unit tests for the pure scoring engine.

Coverage: ~80% edge cases / ~20% happy path.
All numeric constants come from synthetic TEST_RULES dicts — never hardcoded.
"""

from __future__ import annotations

import pytest

from src.scoring.engine import score_round
from src.scoring.standings import build_standings
from src.scoring.types import Category, MatchResult, StandingRow, UserPrediction


# --------------------------------------------------------------------------- fixtures


TEST_RULES = {
    "scoring_rules": {
        "base_points": {
            "exact_high_score": 16,
            "exact_score": 12,
            "diff_plus_outcome": 8,
            "outcome_only": 4,
            "miss": 0,
        },
        "bonuses": {
            "bonus_1_unique_multiplier_pct": 200.0,
            "bonus_2_thresholds": [
                {"min_correct_outcomes": 6, "points": 8},
                {"min_correct_outcomes": 7, "points": 12},
                {"min_correct_outcomes": 8, "points": 16},
            ],
            "bonus_3_rank_points": {"1st": 12, "2nd": 8, "3rd": 4},
            "bonus_3_base_threshold_extra": 50,
            "bonus_3_extra_points": 4,
        },
    },
    "tiebreakers": {
        "priority_order": [
            "total_points DESC",
            "exact_scores_count DESC",
            "total_without_bonuses DESC",
            "correct_diffs_count DESC",
            "manual_override",
        ]
    },
    "constraints": {"max_score_value": 20},
}


def _result(match_id: int, s1: int, s2: int) -> MatchResult:
    return MatchResult(match_id=match_id, score1=s1, score2=s2, is_scorable=True)


def _pred(uid: int, match_id: int, s1: int, s2: int) -> UserPrediction:
    return UserPrediction(user_id=uid, match_id=match_id, score1=s1, score2=s2)


def _score_single(result: MatchResult, prediction: UserPrediction):
    """Helper: score one user on one match."""
    scores = score_round(
        results=[result],
        predictions=[prediction],
        participant_ids=[prediction.user_id],
        rules=TEST_RULES,
    )
    uid = prediction.user_id
    assert len(scores[uid].per_match) == 1
    return scores[uid].per_match[0]


# ============================================================ BASE CATEGORIES


class TestBaseCategories:
    def test_exact_high_large_diff(self):
        """3:0 result, predict 3:0 → EXACT_HIGH (abs diff 3 ≥ 3)."""
        ms = _score_single(_result(1, 3, 0), _pred(1, 1, 3, 0))
        assert ms.category == Category.EXACT_HIGH
        assert ms.base_points == TEST_RULES["scoring_rules"]["base_points"]["exact_high_score"]

    def test_exact_high_high_sum(self):
        """2:2 result, predict 2:2 → EXACT_HIGH (sum 4 > 3)."""
        ms = _score_single(_result(1, 2, 2), _pred(1, 1, 2, 2))
        assert ms.category == Category.EXACT_HIGH
        assert ms.base_points == 16

    def test_exact_normal(self):
        """1:0 result, predict 1:0 → EXACT (sum=1 ≤ 3, diff=1 < 3)."""
        ms = _score_single(_result(1, 1, 0), _pred(1, 1, 1, 0))
        assert ms.category == Category.EXACT
        assert ms.base_points == 12

    def test_diff(self):
        """2:1 result, predict 3:2 → DIFF (same sign, same abs diff=1)."""
        ms = _score_single(_result(1, 2, 1), _pred(1, 1, 3, 2))
        assert ms.category == Category.DIFF
        assert ms.base_points == 8

    def test_outcome_only(self):
        """3:0 result, predict 2:0 → OUTCOME (same sign HOME, different diff)."""
        ms = _score_single(_result(1, 3, 0), _pred(1, 1, 2, 0))
        assert ms.category == Category.OUTCOME
        assert ms.base_points == 4

    def test_miss(self):
        """1:0 result, predict 0:1 → MISS (opposite sign)."""
        ms = _score_single(_result(1, 1, 0), _pred(1, 1, 0, 1))
        assert ms.category == Category.MISS
        assert ms.base_points == 0


# ============================================================ BOUNDARY CASES


class TestBoundaries:
    def test_zero_zero_exact_not_high(self):
        """0:0 is a valid exact prediction; abs diff=0, sum=0 → EXACT, not EXACT_HIGH."""
        ms = _score_single(_result(1, 0, 0), _pred(1, 1, 0, 0))
        assert ms.category == Category.EXACT
        assert ms.base_points == 12

    def test_exact_high_threshold_2_0_is_only_exact(self):
        """2:0: abs diff=2 < 3 AND sum=2 ≤ 3 → EXACT, NOT EXACT_HIGH."""
        ms = _score_single(_result(1, 2, 0), _pred(1, 1, 2, 0))
        assert ms.category == Category.EXACT

    def test_exact_high_threshold_3_0_is_high(self):
        """3:0: abs diff=3 ≥ 3 → EXACT_HIGH (tests the OR boundary)."""
        ms = _score_single(_result(1, 3, 0), _pred(1, 1, 3, 0))
        assert ms.category == Category.EXACT_HIGH

    def test_max_score_value_not_hardcoded(self):
        """Engine must use rules dict values, not hardcoded constants.

        A synthetic rules dict with a different point scale must produce
        the scaled points, not the default 16/12/8/4.
        """
        custom_rules = {
            "scoring_rules": {
                "base_points": {
                    "exact_high_score": 5,
                    "exact_score": 3,
                    "diff_plus_outcome": 2,
                    "outcome_only": 1,
                    "miss": 0,
                },
                "bonuses": {
                    "bonus_1_unique_multiplier_pct": 100.0,
                    "bonus_2_thresholds": [],
                    "bonus_3_rank_points": {"1st": 0, "2nd": 0, "3rd": 0},
                    "bonus_3_base_threshold_extra": 999,
                    "bonus_3_extra_points": 0,
                },
            },
            "tiebreakers": {"priority_order": []},
            "constraints": {"max_score_value": 5},
        }
        scores = score_round(
            results=[_result(1, 3, 0)],
            predictions=[_pred(1, 1, 3, 0)],
            participant_ids=[1],
            rules=custom_rules,
        )
        # EXACT_HIGH in custom rules = 5
        assert scores[1].base_points == 5


# ============================================================ NULL / ABSENCE


class TestNullAbsence:
    def test_absent_user_earns_zero_not_treated_as_0_0(self):
        """User A has NO prediction; user B predicts 0:0 correctly.

        Result is 0:0, so 0:0 would score EXACT (12 pts).
        A must earn 0 and NOT be falsely credited with B's correct prediction.
        """
        result = _result(1, 0, 0)
        pred_b = _pred(uid=2, match_id=1, s1=0, s2=0)

        scores = score_round(
            results=[result],
            predictions=[pred_b],
            participant_ids=[1, 2],
            rules=TEST_RULES,
        )

        assert scores[1].base_points == 0
        assert scores[1].correct_outcomes == 0
        assert len(scores[1].per_match) == 0

        assert scores[2].base_points == 12
        # EXACT earns 12 pts ≥ 4 → counted as correct_outcome
        assert scores[2].correct_outcomes == 1

    def test_absence_is_not_0_0_prediction(self):
        """Construct a case where treating absence as 0:0 would yield points.

        Result 0:0; user has NO prediction → must earn 0 (not EXACT 12 pts).
        """
        result = _result(99, 0, 0)

        scores = score_round(
            results=[result],
            predictions=[],  # no one predicted
            participant_ids=[5],
            rules=TEST_RULES,
        )

        assert scores[5].base_points == 0
        assert len(scores[5].per_match) == 0

    def test_non_scorable_match_excluded(self):
        """Match with is_scorable=False is skipped for all users."""
        void_match = MatchResult(match_id=1, score1=None, score2=None, is_scorable=False)
        pred = _pred(uid=1, match_id=1, s1=1, s2=0)

        scores = score_round(
            results=[void_match],
            predictions=[pred],
            participant_ids=[1],
            rules=TEST_RULES,
        )

        assert scores[1].base_points == 0
        assert len(scores[1].per_match) == 0


# ============================================================ BONUS 1


class TestBonus1:
    def test_unique_correct_outcome_gets_double_base(self):
        """Single user predicts correct outcome → bonus1 = 2 × base (200%)."""
        result = _result(1, 2, 0)  # HOME win
        pred_a = _pred(uid=1, match_id=1, s1=3, s2=0)  # HOME → OUTCOME (4 pts)

        scores = score_round(
            results=[result],
            predictions=[pred_a],
            participant_ids=[1],
            rules=TEST_RULES,
        )

        assert scores[1].base_points == 4
        # 4 × 200% = 8
        assert scores[1].bonus1 == 8
        assert scores[1].per_match[0].bonus1_points == 8

    def test_two_users_same_outcome_no_bonus(self):
        """Two users both predict the correct outcome → no bonus1 for either."""
        result = _result(1, 2, 0)  # HOME
        pred_a = _pred(uid=1, match_id=1, s1=1, s2=0)  # HOME
        pred_b = _pred(uid=2, match_id=1, s1=3, s2=1)  # HOME

        scores = score_round(
            results=[result],
            predictions=[pred_a, pred_b],
            participant_ids=[1, 2],
            rules=TEST_RULES,
        )

        assert scores[1].bonus1 == 0
        assert scores[2].bonus1 == 0

    def test_unique_but_wrong_outcome_no_bonus(self):
        """User uniquely predicts the WRONG outcome → bonus1 = 0."""
        result = _result(1, 2, 0)  # HOME win
        pred_a = _pred(uid=1, match_id=1, s1=0, s2=1)  # AWAY (wrong)

        scores = score_round(
            results=[result],
            predictions=[pred_a],
            participant_ids=[1],
            rules=TEST_RULES,
        )

        assert scores[1].bonus1 == 0

    def test_unique_bonus_sums_across_matches(self):
        """Two matches where the user is the sole correct predictor → bonus1 sums."""
        r1 = _result(1, 2, 0)  # HOME
        r2 = _result(2, 0, 1)  # AWAY
        # User 1: predicts HOME on M1 (OUTCOME 4), AWAY on M2 (OUTCOME 4) — both unique
        # User 2: predicts DRAW on both → wrong outcome (no DRAW bonus for either match)
        p1a = _pred(uid=1, match_id=1, s1=1, s2=0)  # HOME
        p1b = _pred(uid=1, match_id=2, s1=0, s2=2)  # AWAY
        p2a = _pred(uid=2, match_id=1, s1=1, s2=1)  # DRAW (wrong)
        p2b = _pred(uid=2, match_id=2, s1=0, s2=0)  # DRAW (wrong)

        scores = score_round(
            results=[r1, r2],
            predictions=[p1a, p1b, p2a, p2b],
            participant_ids=[1, 2],
            rules=TEST_RULES,
        )

        # User 1 alone predicts HOME on M1 → bonus1 = 2×4=8
        # User 1 alone predicts AWAY on M2 → bonus1 = 2×4=8
        assert scores[1].bonus1 == 16
        assert scores[2].bonus1 == 0

    def test_bonus1_based_on_exact_high_base(self):
        """User uniquely predicts correct outcome with EXACT_HIGH base → bonus1 = 2×16."""
        result = _result(1, 3, 0)  # HOME, large diff
        pred_a = _pred(uid=1, match_id=1, s1=3, s2=0)  # EXACT_HIGH (16 pts)
        # User 2 predicts AWAY (wrong outcome)
        pred_b = _pred(uid=2, match_id=1, s1=0, s2=2)

        scores = score_round(
            results=[result],
            predictions=[pred_a, pred_b],
            participant_ids=[1, 2],
            rules=TEST_RULES,
        )

        assert scores[1].base_points == 16
        assert scores[1].bonus1 == 32  # int(16 × 200 / 100) = 32


# ============================================================ BONUS 2


class TestBonus2:
    def _make_n_correct_outcomes(self, n: int, uid: int = 1) -> tuple:
        """Create n scorable HOME matches where uid predicts HOME correctly."""
        results = [_result(i + 1, 1, 0) for i in range(n)]
        preds = [_pred(uid=uid, match_id=i + 1, s1=1, s2=0) for i in range(n)]
        return results, preds

    def test_5_correct_no_bonus(self):
        """n=5 correct outcomes → bonus2 = 0 (below threshold of 6)."""
        results, preds = self._make_n_correct_outcomes(5)
        scores = score_round(results, preds, [1], TEST_RULES)
        assert scores[1].correct_outcomes == 5
        assert scores[1].bonus2 == 0

    def test_6_correct_bonus_8(self):
        """n=6 correct outcomes → bonus2 = 8."""
        results, preds = self._make_n_correct_outcomes(6)
        scores = score_round(results, preds, [1], TEST_RULES)
        assert scores[1].correct_outcomes == 6
        assert scores[1].bonus2 == 8

    def test_7_correct_bonus_12(self):
        """n=7 correct outcomes → bonus2 = 12."""
        results, preds = self._make_n_correct_outcomes(7)
        scores = score_round(results, preds, [1], TEST_RULES)
        assert scores[1].correct_outcomes == 7
        assert scores[1].bonus2 == 12

    def test_8_correct_bonus_16(self):
        """n=8 correct outcomes → bonus2 = 16 (highest threshold)."""
        results, preds = self._make_n_correct_outcomes(8)
        scores = score_round(results, preds, [1], TEST_RULES)
        assert scores[1].correct_outcomes == 8
        assert scores[1].bonus2 == 16


# ============================================================ BONUS 3


class TestBonus3:
    def _make_scores(self, base1: int, base2: int, base3: int) -> dict:
        """Create a scenario where user 1/2/3 have given base totals.

        Achieves desired base points by using EXACT predictions on 1:0 matches
        (12 pts each) and OUTCOME predictions on 2:0 matches (4 pts each).
        Both correct_outcomes are kept < 6 to avoid bonus2 interference.
        Keeps all three predictions unique on different outcomes to avoid bonus1.
        """
        # We'll build base via EXACT (1:0) matches only.
        # base must be divisible cleanly; we'll use 12 and 4 increments.
        # For the test, we pre-build results and predictions to hit desired bases.
        raise NotImplementedError("Use the manual helper approach")

    def test_three_distinct_places_with_extra(self):
        """Three users with basis 56, 52, 44 → places 1, 2, 3.

        basis 56 ≥ 50 → extra=4; bonus3 = 12+4 = 16
        basis 52 ≥ 50 → extra=4; bonus3 = 8+4  = 12
        basis 44 < 50 → extra=0; bonus3 = 4+0  = 4
        """
        # 5 matches result 1:0 + 1 result 2:1
        # User 1: predicts 1:0 on M1-M4 (EXACT 12 each=48), 3:2 on M5 (DIFF 8) = 56 base
        # User 2: predicts 1:0 on M1-M4 (48), 2:0 on M5 (OUTCOME 4) = 52 base
        # User 3: predicts 1:0 on M1-M3 (36), 3:2 on M5 (DIFF 8) = 44 base
        #         (skips M4 — no prediction)
        #
        # All have <6 correct_outcomes → bonus2=0, bonus1=0 (multiple HOME predictors).
        # So basis == base.
        results = [
            _result(1, 1, 0),
            _result(2, 1, 0),
            _result(3, 1, 0),
            _result(4, 1, 0),
            _result(5, 2, 1),
        ]
        preds = [
            # User 1
            _pred(1, 1, 1, 0),
            _pred(1, 2, 1, 0),
            _pred(1, 3, 1, 0),
            _pred(1, 4, 1, 0),
            _pred(1, 5, 3, 2),  # DIFF
            # User 2
            _pred(2, 1, 1, 0),
            _pred(2, 2, 1, 0),
            _pred(2, 3, 1, 0),
            _pred(2, 4, 1, 0),
            _pred(2, 5, 2, 0),  # OUTCOME on M5 (HOME, diff=2 vs result diff=1 → OUTCOME)
            # User 3
            _pred(3, 1, 1, 0),
            _pred(3, 2, 1, 0),
            _pred(3, 3, 1, 0),
            # no prediction on M4
            _pred(3, 5, 3, 2),  # DIFF
        ]

        scores = score_round(results, preds, [1, 2, 3], TEST_RULES)

        assert scores[1].base_points == 56
        assert scores[2].base_points == 52
        assert scores[3].base_points == 44

        # No bonus1 (multiple HOME predictors on M1-M4), no bonus2 (5 correct each <6)
        assert scores[1].bonus1 == 0
        assert scores[1].bonus2 == 0
        assert scores[2].bonus1 == 0
        assert scores[2].bonus2 == 0

        # basis = base
        assert scores[1].bonus3 == 16  # place 1 (12) + extra (4)
        assert scores[2].bonus3 == 12  # place 2 (8) + extra (4)
        assert scores[3].bonus3 == 4   # place 3 (4) + no extra

    def test_tie_on_basis_same_place_points(self):
        """Two users with identical basis both receive 3rd-place bonus points."""
        # Users 1 and 2 each have 36 base; user 3 has 80 (place 1), user 4 has 60 (place 2).
        # Users 1 & 2 share 3rd place → both get 4 pts.
        # 36 < 50 → no extra.
        results = [
            _result(i + 1, 1, 0) for i in range(7)
        ]  # 7 × 1:0 results

        def _home_preds(uid: int, n: int) -> list[UserPrediction]:
            return [_pred(uid, i + 1, 1, 0) for i in range(n)]

        preds = (
            _home_preds(10, 7)  # 7 × EXACT(12) = 84 — but correct_outcomes=7 → bonus2=12
            # To keep bonus2 zero, use fewer than 6 correct outcomes
            # Redesign: use EXACT on 3 matches only
        )
        # Simpler approach: fewer matches, all EXACT, no bonus2
        results = [_result(i + 1, 1, 0) for i in range(5)]

        # User 10: 5 × EXACT = 60, correct=5 < 6, bonus2=0, basis=60 → place 1 (no tie)
        # User 11: 4 × EXACT + 1 miss = 48, basis=48 → place 2
        # User 12: 3 × EXACT = 36 < 50, basis=36 → place 3 (tied)
        # User 13: 3 × EXACT = 36 < 50, basis=36 → place 3 (tied with 12)
        preds = (
            [_pred(10, i + 1, 1, 0) for i in range(5)]
            + [_pred(11, i + 1, 1, 0) for i in range(4)]
            + [_pred(12, i + 1, 1, 0) for i in range(3)]
            + [_pred(13, i + 1, 1, 0) for i in range(3)]
        )

        scores = score_round(results, preds, [10, 11, 12, 13], TEST_RULES)

        assert scores[10].base_points == 60
        assert scores[11].base_points == 48
        assert scores[12].base_points == 36
        assert scores[13].base_points == 36

        # 36 < 50 → no extra; tied 3rd place → 4 pts each
        assert scores[12].bonus3 == 4
        assert scores[13].bonus3 == 4

        # 60 ≥ 50 → extra=4; place 1 → 12+4=16
        assert scores[10].bonus3 == 16
        # 48 < 50 → no extra; place 2 → 8
        assert scores[11].bonus3 == 8

    def test_base_zero_no_bonus3(self):
        """User with base_points == 0 must always get bonus3 == 0."""
        result = _result(1, 1, 0)
        pred_wrong = _pred(uid=7, match_id=1, s1=0, s2=1)  # MISS
        pred_right = _pred(uid=8, match_id=1, s1=1, s2=0)  # EXACT

        scores = score_round(
            results=[result],
            predictions=[pred_wrong, pred_right],
            participant_ids=[7, 8],
            rules=TEST_RULES,
        )

        assert scores[7].base_points == 0
        assert scores[7].bonus3 == 0

    def test_extra_at_exact_threshold(self):
        """basis == bonus_3_base_threshold_extra (50) still earns extra points."""
        # 4 EXACT (48) + 1 DIFF (8) = 56 for user 1 → ≥50 extra
        # Use a clean scenario: 5 matches, user predicts exactly to get 50 base
        # 3 EXACT (36) + 1 DIFF (8) + ... 36+8=44; 4 EXACT (48)+1 DIFF (8)=56 (>50)
        # To get exactly 50 is hard; use 50 via different path:
        # 2 EXACT_HIGH (32) + 1 EXACT (12) + ... = 44. Hmm.
        # Use 3 EXACT (36) + 1 EXACT_HIGH (16) - no wait 52.
        # 4 EXACT (48) + OUTCOME (4) = 52... still not 50.
        # Let's use custom rules with threshold 52 instead.
        custom_rules = {
            "scoring_rules": {
                "base_points": {
                    "exact_high_score": 16,
                    "exact_score": 12,
                    "diff_plus_outcome": 8,
                    "outcome_only": 4,
                    "miss": 0,
                },
                "bonuses": {
                    "bonus_1_unique_multiplier_pct": 200.0,
                    "bonus_2_thresholds": [],
                    "bonus_3_rank_points": {"1st": 12, "2nd": 8, "3rd": 4},
                    "bonus_3_base_threshold_extra": 52,  # custom threshold
                    "bonus_3_extra_points": 4,
                },
            },
            "tiebreakers": {"priority_order": []},
            "constraints": {"max_score_value": 20},
        }
        # User 1: 4 EXACT (48) + 1 OUTCOME (4) = 52 base = threshold → gets extra
        # User 2: 4 EXACT (48) = 48 base < threshold → no extra
        results = [_result(i + 1, 1, 0) for i in range(4)] + [_result(5, 2, 0)]
        preds = (
            [_pred(1, i + 1, 1, 0) for i in range(4)]
            + [_pred(1, 5, 1, 0)]  # OUTCOME on M5 (1:0 vs 2:0 → correct sign, diff≠diff)
            + [_pred(2, i + 1, 1, 0) for i in range(4)]
            # User 2 skips M5
        )
        scores = score_round(results, preds, [1, 2], rules=custom_rules)

        assert scores[1].base_points == 52
        assert scores[2].base_points == 48

        # basis == 52 == threshold → extra applies
        # place 1 (highest) → 12 + 4 = 16
        assert scores[1].bonus3 == 16
        # basis == 48 < 52 → no extra; place 2 → 8
        assert scores[2].bonus3 == 8


# ============================================================ ROUND RANK


class TestRoundRank:
    def test_dense_ranking(self):
        """totals 30, 20, 20, 10 → ranks 1, 2, 2, 3 (dense: next distinct gets rank+1, not rank+count)."""
        # Use custom rules with no bonuses to control total_with_bonus3 == base
        zero_bonus_rules = {
            "scoring_rules": {
                "base_points": {
                    "exact_high_score": 30,
                    "exact_score": 20,
                    "diff_plus_outcome": 10,
                    "outcome_only": 10,
                    "miss": 0,
                },
                "bonuses": {
                    "bonus_1_unique_multiplier_pct": 0.0,
                    "bonus_2_thresholds": [],
                    "bonus_3_rank_points": {"1st": 0, "2nd": 0, "3rd": 0},
                    "bonus_3_base_threshold_extra": 9999,
                    "bonus_3_extra_points": 0,
                },
            },
            "tiebreakers": {"priority_order": []},
            "constraints": {"max_score_value": 30},
        }
        # M1 result 3:0 (exact_high=30), M2 result 2:0, M3 result 1:0
        # U1: predicts 3:0 on M1 → 30 pts  (total 30)
        # U2 & U3: predict 1:0 on M2 → 20 pts each (total 20)
        # U4: predicts 2:1 on M3 → MISS (wrong outcome: 2:1 is HOME, 1:0 is HOME)
        #     Wait, 1:0 HOME, 2:1 HOME → same sign → need a DIFF or OUTCOME
        # Let me redesign: use distinct results per match
        # M1: result 3:0 → U1 predicts 3:0 → EXACT_HIGH(30)
        # M2: result 1:0 → U2,U3 predict 1:0 → EXACT(20)
        # M3: result 2:0 → U4 predicts 0:2 → MISS(0) ← wait, need 10 points for U4
        # Better: U4 predicts 2:0 on M3 → EXACT(20)? No, I need total=10.
        # Let me reuse M1 for U4: U4 predicts 2:0 on M1 → OUTCOME(10)? Yes!
        # But then U1 gets EXACT_HIGH(30) and U4 gets OUTCOME(10) on the same match.
        results = [_result(1, 3, 0), _result(2, 1, 0)]
        preds = [
            _pred(1, 1, 3, 0),  # EXACT_HIGH → 30
            _pred(2, 2, 1, 0),  # EXACT → 20
            _pred(3, 2, 1, 0),  # EXACT → 20
            _pred(4, 1, 2, 0),  # OUTCOME on M1 (HOME) → 10
        ]
        scores = score_round(results, preds, [1, 2, 3, 4], rules=zero_bonus_rules)

        assert scores[1].total_with_bonus3 == 30
        assert scores[2].total_with_bonus3 == 20
        assert scores[3].total_with_bonus3 == 20
        assert scores[4].total_with_bonus3 == 10

        assert scores[1].round_rank == 1
        assert scores[2].round_rank == 2
        assert scores[3].round_rank == 2
        assert scores[4].round_rank == 3  # dense: next distinct value gets rank 3, not 4

    def test_zero_prediction_user_ranks_last(self):
        """User with no predictions gets total=0 and round_rank = last."""
        result = _result(1, 1, 0)
        pred = _pred(uid=1, match_id=1, s1=1, s2=0)

        scores = score_round(
            results=[result],
            predictions=[pred],
            participant_ids=[1, 99],  # 99 has no predictions
            rules=TEST_RULES,
        )

        assert scores[99].total_with_bonus3 == 0
        assert scores[99].round_rank > scores[1].round_rank


# ============================================================ STANDINGS TIE-BREAK


class TestStandings:
    def _make_round(
        self,
        uid: int,
        base: int = 0,
        eh: int = 0,
        ex: int = 0,
        di: int = 0,
        ou: int = 0,
    ):
        """Build a minimal UserRoundScore with controlled aggregation fields."""
        from src.scoring.types import UserRoundScore

        return UserRoundScore(
            user_id=uid,
            base_points=base,
            count_exact_high=eh,
            count_exact=ex,
            count_diff=di,
            count_outcome=ou,
            correct_outcomes=eh + ex + di + ou,
            bonus1=0,
            bonus2=0,
            bonus3=0,
            total_without_bonus3=base,
            total_with_bonus3=base,
            round_rank=1,
            per_match=(),
        )

    def test_tiebreak_by_exact_scores_count(self):
        """Same total_points; user with more exact_scores_count ranks higher."""
        rounds = {
            1: [self._make_round(1, base=100, eh=2, ex=3)],  # exact_scores = 5
            2: [self._make_round(2, base=100, eh=1, ex=2)],  # exact_scores = 3
        }
        rows = build_standings(rounds, manual_overrides=None)
        by_uid = {r.user_id: r for r in rows}
        assert by_uid[1].rank < by_uid[2].rank

    def test_tiebreak_by_total_without_bonuses(self):
        """Same total_points, same exact_scores; higher base wins."""
        rounds = {
            1: [self._make_round(1, base=80, eh=1, ex=2)],
            2: [self._make_round(2, base=60, eh=1, ex=2)],
        }
        rows = build_standings(rounds, manual_overrides=None)
        by_uid = {r.user_id: r for r in rows}
        assert by_uid[1].rank < by_uid[2].rank

    def test_tiebreak_by_correct_diffs_count(self):
        """Same total, exact_scores, base; higher diff_count wins."""
        rounds = {
            1: [self._make_round(1, base=80, eh=1, ex=2, di=5)],
            2: [self._make_round(2, base=80, eh=1, ex=2, di=3)],
        }
        rows = build_standings(rounds, manual_overrides=None)
        by_uid = {r.user_id: r for r in rows}
        assert by_uid[1].rank < by_uid[2].rank

    def test_manual_override_breaks_full_tie(self):
        """All criteria 1–4 equal; manual_override decides."""
        rounds = {
            1: [self._make_round(1, base=80, eh=1, ex=2, di=3)],
            2: [self._make_round(2, base=80, eh=1, ex=2, di=3)],
        }
        rows = build_standings(rounds, manual_overrides={2: 1})  # user 2 gets priority
        by_uid = {r.user_id: r for r in rows}

        assert by_uid[2].rank < by_uid[1].rank
        assert by_uid[2].tiebreaker_status == "manual_override"
        assert by_uid[1].tiebreaker_status == "manual_override"

    def test_no_manual_override_no_status(self):
        """Users with distinct totals have tiebreaker_status=None."""
        rounds = {
            1: [self._make_round(1, base=100)],
            2: [self._make_round(2, base=50)],
        }
        rows = build_standings(rounds, manual_overrides=None)
        for row in rows:
            assert row.tiebreaker_status is None

    def test_full_tiebreak_chain(self):
        """Verify ordering through criteria 1 → 2 → 3 → 4 → manual."""
        rounds = {
            # Criteria 1 winner
            10: [self._make_round(10, base=200, eh=3, ex=3, di=5)],
            # Criteria 2 winner (same total as 20)
            20: [self._make_round(20, base=100, eh=0, ex=4, di=2)],  # exact=4
            21: [self._make_round(21, base=100, eh=0, ex=2, di=2)],  # exact=2
            # Criteria 3 winner (same total & exact as 30)
            30: [self._make_round(30, base=90, eh=1, ex=1, di=2)],
            31: [self._make_round(31, base=70, eh=1, ex=1, di=2)],
            # Criteria 4 winner (same total, exact, base as 40)
            40: [self._make_round(40, base=80, eh=1, ex=1, di=6)],
            41: [self._make_round(41, base=80, eh=1, ex=1, di=2)],
            # Manual override (everything equal)
            50: [self._make_round(50, base=60, eh=0, ex=1, di=1)],
            51: [self._make_round(51, base=60, eh=0, ex=1, di=1)],
        }
        rows = build_standings(rounds, manual_overrides={51: 1})
        by_uid = {r.user_id: r for r in rows}

        assert by_uid[10].rank == 1
        assert by_uid[20].rank < by_uid[21].rank
        assert by_uid[30].rank < by_uid[31].rank
        assert by_uid[40].rank < by_uid[41].rank
        assert by_uid[51].rank < by_uid[50].rank
        assert by_uid[51].tiebreaker_status == "manual_override"
        assert by_uid[50].tiebreaker_status == "manual_override"

    def test_aggregation_across_rounds(self):
        """Totals are correctly aggregated across multiple rounds."""
        rounds = {
            1: [
                self._make_round(1, base=40, eh=1, ex=2, di=3, ou=1),
                self._make_round(1, base=30, eh=0, ex=1, di=2, ou=2),
            ],
        }
        rows = build_standings(rounds, manual_overrides=None)
        row = rows[0]

        assert row.total_points == 70
        assert row.total_without_bonuses == 70
        assert row.exact_high_count == 1
        assert row.exact_count == 3
        assert row.exact_scores_count == 4
        assert row.diff_count == 5
        assert row.correct_diffs_count == 5
        assert row.outcome_count == 3
