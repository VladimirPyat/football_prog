"""
Stage 1.1 cross-check: scoring engine vs contracted reference data.

Mandatory assertions:
  [SC-BASE], [SC-B1B2], [SC-B3], [SC-TOTAL], [SC-RANK], [SC-COUNTS] — 90 rows each
  [LB-COUNT], [LB-TOTALS], [LB-RANK] — 10 users
  [EDGE-NULL], [EDGE-ZERO], [EDGE-TIE], [EDGE-VOID] — synthetic cases

All per-round tests iterate over all 90 rows from expected_scores.csv.
On failure the assert message includes user login and round number.
"""

from __future__ import annotations

import pytest

from src.scoring.engine import score_round
from src.scoring.standings import build_standings
from src.scoring.types import MatchResult, UserPrediction, UserRoundScore, StandingRow

from tests.scoring.conftest import (
    ExpectedScoreRow,
    LeaderboardRow,
    UserRow,
)


# ===========================================================================
# [SC-COUNTS] SAFETY GATE — must pass before per-row count assertions
# ===========================================================================


class TestScCountsGate:
    """Verify every fixture row satisfies 16*eh + 12*ex + 8*di + 4*ou == base_pts."""

    def test_counts_gate_all_rows(self, expected_score_rows: list[ExpectedScoreRow]) -> None:
        """[SC-COUNTS] Gate: arithmetic consistency of count columns in fixture."""
        failures: list[str] = []
        for row in expected_score_rows:
            computed = (
                16 * row.count_exact_high
                + 12 * row.count_exact
                + 8 * row.count_diff
                + 4 * row.count_outcome
            )
            if computed != row.expected_base_pts:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"16*{row.count_exact_high}+12*{row.count_exact}+"
                    f"8*{row.count_diff}+4*{row.count_outcome}={computed} "
                    f"!= expected_base_pts={row.expected_base_pts}"
                )
        assert not failures, (
            "[SC-COUNTS] BLOCKED: data inconsistent — fixture count columns don't sum to "
            "expected_base_pts (see agent_docs/reports/count_fix_reference.md):\n"
            + "\n".join(failures)
        )


# ===========================================================================
# Per-round assertions (90 rows)
# ===========================================================================


class TestPerRoundScores:
    """Cross-check all 90 (user, round) rows from expected_scores.csv."""

    def _get(
        self,
        engine_results: dict,
        row: ExpectedScoreRow,
    ) -> UserRoundScore:
        return engine_results[row.round_number][row.user_id]

    # ------------------------------------------------------------------

    def test_sc_base_all_rows(
        self,
        engine_results: dict,
        expected_score_rows: list[ExpectedScoreRow],
    ) -> None:
        """[SC-BASE] engine.base_points == expected_base_pts for 90/90 rows."""
        failures: list[str] = []
        for row in expected_score_rows:
            eng = self._get(engine_results, row)
            if eng.base_points != row.expected_base_pts:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"engine={eng.base_points} expected={row.expected_base_pts}"
                )
        assert not failures, "[SC-BASE] Failures:\n" + "\n".join(failures)

    def test_sc_b1b2_all_rows(
        self,
        engine_results: dict,
        expected_score_rows: list[ExpectedScoreRow],
    ) -> None:
        """[SC-B1B2] engine.bonus1+bonus2 == expected_bonus1 AND expected_bonus2==0, 90/90."""
        failures: list[str] = []
        for row in expected_score_rows:
            eng = self._get(engine_results, row)
            engine_b1b2 = eng.bonus1 + eng.bonus2
            if engine_b1b2 != row.expected_bonus1:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"engine bonus1+bonus2={engine_b1b2} expected={row.expected_bonus1}"
                )
            if row.expected_bonus2 != 0:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"fixture expected_bonus2={row.expected_bonus2} should always be 0"
                )
        assert not failures, "[SC-B1B2] Failures:\n" + "\n".join(failures)

    def test_sc_b3_all_rows(
        self,
        engine_results: dict,
        expected_score_rows: list[ExpectedScoreRow],
    ) -> None:
        """[SC-B3] engine.bonus3 == expected_bonus3 for 90/90 rows."""
        failures: list[str] = []
        for row in expected_score_rows:
            eng = self._get(engine_results, row)
            if eng.bonus3 != row.expected_bonus3:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"engine={eng.bonus3} expected={row.expected_bonus3}"
                )
        assert not failures, "[SC-B3] Failures:\n" + "\n".join(failures)

    def test_sc_total_all_rows(
        self,
        engine_results: dict,
        expected_score_rows: list[ExpectedScoreRow],
    ) -> None:
        """[SC-TOTAL] engine.total_with_bonus3 == expected_total for 90/90 rows."""
        failures: list[str] = []
        for row in expected_score_rows:
            eng = self._get(engine_results, row)
            if eng.total_with_bonus3 != row.expected_total:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"engine={eng.total_with_bonus3} expected={row.expected_total}"
                )
        assert not failures, "[SC-TOTAL] Failures:\n" + "\n".join(failures)

    def test_sc_rank_all_rows(
        self,
        engine_results: dict,
        expected_score_rows: list[ExpectedScoreRow],
    ) -> None:
        """[SC-RANK] engine.round_rank == expected_rank (dense), 90/90 rows."""
        failures: list[str] = []
        for row in expected_score_rows:
            eng = self._get(engine_results, row)
            if eng.round_rank != row.expected_rank:
                failures.append(
                    f"  {row.login} round {row.round_number}: "
                    f"engine={eng.round_rank} expected={row.expected_rank}"
                )
        assert not failures, "[SC-RANK] Failures:\n" + "\n".join(failures)

    def test_sc_counts_all_rows(
        self,
        engine_results: dict,
        expected_score_rows: list[ExpectedScoreRow],
    ) -> None:
        """[SC-COUNTS] engine count_* == fixture count_* for 90/90 rows."""
        failures: list[str] = []
        for row in expected_score_rows:
            eng = self._get(engine_results, row)
            if eng.count_exact_high != row.count_exact_high:
                failures.append(
                    f"  {row.login} r{row.round_number} count_exact_high: "
                    f"engine={eng.count_exact_high} expected={row.count_exact_high}"
                )
            if eng.count_exact != row.count_exact:
                failures.append(
                    f"  {row.login} r{row.round_number} count_exact: "
                    f"engine={eng.count_exact} expected={row.count_exact}"
                )
            if eng.count_diff != row.count_diff:
                failures.append(
                    f"  {row.login} r{row.round_number} count_diff: "
                    f"engine={eng.count_diff} expected={row.count_diff}"
                )
            if eng.count_outcome != row.count_outcome:
                failures.append(
                    f"  {row.login} r{row.round_number} count_outcome: "
                    f"engine={eng.count_outcome} expected={row.count_outcome}"
                )
        assert not failures, "[SC-COUNTS] Failures:\n" + "\n".join(failures)

    def test_serov_round4_zero_predictions(
        self,
        engine_results: dict,
        login_to_uid: dict[str, int],
    ) -> None:
        """serov has NO predictions in round 4 — all scores must be 0, rank must be present."""
        uid = login_to_uid["serov"]
        eng = engine_results[4][uid]
        assert eng.base_points == 0, f"serov r4 base_points: {eng.base_points} != 0"
        assert eng.bonus1 == 0, f"serov r4 bonus1: {eng.bonus1} != 0"
        assert eng.bonus2 == 0, f"serov r4 bonus2: {eng.bonus2} != 0"
        assert eng.bonus3 == 0, f"serov r4 bonus3: {eng.bonus3} != 0"
        assert eng.total_with_bonus3 == 0, f"serov r4 total: {eng.total_with_bonus3} != 0"
        # Rank must be a valid positive integer (no KeyError / zero rank)
        assert eng.round_rank >= 1, f"serov r4 round_rank invalid: {eng.round_rank}"
        # No per_match entries (no predictions submitted)
        assert len(eng.per_match) == 0, f"serov r4 per_match should be empty, got {len(eng.per_match)}"


# ===========================================================================
# Leaderboard assertions (10 users)
# ===========================================================================


class TestLeaderboard:

    def test_lb_count_all_users(
        self,
        per_user_rounds: dict,
        leaderboard_rows: list[LeaderboardRow],
    ) -> None:
        """[LB-COUNT] Σ count_* columns match leaderboard.csv for 10/10 users."""
        failures: list[str] = []
        for lb in leaderboard_rows:
            rounds = per_user_rounds[lb.user_id]
            agg_eh = sum(r.count_exact_high for r in rounds)
            agg_ex = sum(r.count_exact for r in rounds)
            agg_di = sum(r.count_diff for r in rounds)
            agg_ou = sum(r.count_outcome for r in rounds)

            for field, engine_val, expected_val in [
                ("exact_high_count", agg_eh, lb.exact_high_count),
                ("exact_count", agg_ex, lb.exact_count),
                ("diff_count", agg_di, lb.diff_count),
                ("outcome_count", agg_ou, lb.outcome_count),
            ]:
                if engine_val != expected_val:
                    failures.append(
                        f"  {lb.login} {field}: engine={engine_val} expected={expected_val}"
                    )
        assert not failures, "[LB-COUNT] Failures:\n" + "\n".join(failures)

    def test_lb_totals_all_users(
        self,
        per_user_rounds: dict,
        standings: list[StandingRow],
        leaderboard_rows: list[LeaderboardRow],
    ) -> None:
        """[LB-TOTALS] Aggregate base, bonuses, total, predictions match leaderboard.csv."""
        standing_by_uid = {s.user_id: s for s in standings}
        failures: list[str] = []
        for lb in leaderboard_rows:
            rounds = per_user_rounds[lb.user_id]
            row = standing_by_uid[lb.user_id]

            # total_without_bonuses
            agg_base = sum(r.base_points for r in rounds)
            if agg_base != lb.total_without_bonuses:
                failures.append(
                    f"  {lb.login} total_without_bonuses: engine={agg_base} expected={lb.total_without_bonuses}"
                )

            # total_bonuses = Σ(bonus1 + bonus2 + bonus3)
            agg_bonuses = sum(r.bonus1 + r.bonus2 + r.bonus3 for r in rounds)
            if agg_bonuses != lb.total_bonuses:
                failures.append(
                    f"  {lb.login} total_bonuses: engine={agg_bonuses} expected={lb.total_bonuses}"
                )

            # total_points
            agg_total = sum(r.total_with_bonus3 for r in rounds)
            if agg_total != lb.total_points:
                failures.append(
                    f"  {lb.login} total_points: engine={agg_total} expected={lb.total_points}"
                )

            # total_predictions (from StandingRow)
            if row.total_predictions != lb.total_predictions:
                failures.append(
                    f"  {lb.login} total_predictions: engine={row.total_predictions} expected={lb.total_predictions}"
                )

        assert not failures, "[LB-TOTALS] Failures:\n" + "\n".join(failures)

    def test_lb_rank_order(
        self,
        standings: list[StandingRow],
        leaderboard_rows: list[LeaderboardRow],
    ) -> None:
        """[LB-RANK] build_standings() order and ranks match leaderboard.csv, including tie-break pairs."""
        standing_by_uid = {s.user_id: s for s in standings}
        lb_by_uid = {lb.user_id: lb for lb in leaderboard_rows}

        failures: list[str] = []
        for uid, row in standing_by_uid.items():
            expected_rank = lb_by_uid[uid].rank
            if row.rank != expected_rank:
                failures.append(
                    f"  {lb_by_uid[uid].login}: engine rank={row.rank} expected={expected_rank}"
                )

        # Explicit tie-break pair verification
        shutov_uid = next(uid for uid, lb in lb_by_uid.items() if lb.login == "shutov")
        kurakov_uid = next(uid for uid, lb in lb_by_uid.items() if lb.login == "kurakov")
        volchenko_uid = next(uid for uid, lb in lb_by_uid.items() if lb.login == "volchenko")
        serov_uid = next(uid for uid, lb in lb_by_uid.items() if lb.login == "serov")

        shutov_row = standing_by_uid[shutov_uid]
        kurakov_row = standing_by_uid[kurakov_uid]
        volchenko_row = standing_by_uid[volchenko_uid]
        serov_row = standing_by_uid[serov_uid]

        # Both pairs must have equal total_points
        assert shutov_row.total_points == kurakov_row.total_points == 320, (
            f"[LB-RANK] shutov/kurakov total_points mismatch: "
            f"shutov={shutov_row.total_points} kurakov={kurakov_row.total_points}"
        )
        assert volchenko_row.total_points == serov_row.total_points == 232, (
            f"[LB-RANK] volchenko/serov total_points mismatch: "
            f"volchenko={volchenko_row.total_points} serov={serov_row.total_points}"
        )

        # Tiebreak: shutov above kurakov by exact_scores_count
        assert shutov_row.exact_scores_count > kurakov_row.exact_scores_count, (
            f"[LB-RANK] shutov exact_scores_count={shutov_row.exact_scores_count} "
            f"should be > kurakov={kurakov_row.exact_scores_count}"
        )
        assert shutov_row.rank < kurakov_row.rank, (
            f"[LB-RANK] shutov rank={shutov_row.rank} should be < kurakov rank={kurakov_row.rank}"
        )

        # Tiebreak: volchenko above serov by exact_scores_count
        assert volchenko_row.exact_scores_count > serov_row.exact_scores_count, (
            f"[LB-RANK] volchenko exact_scores_count={volchenko_row.exact_scores_count} "
            f"should be > serov={serov_row.exact_scores_count}"
        )
        assert volchenko_row.rank < serov_row.rank, (
            f"[LB-RANK] volchenko rank={volchenko_row.rank} should be < serov rank={serov_row.rank}"
        )

        assert not failures, "[LB-RANK] Rank mismatches:\n" + "\n".join(failures)

    def test_lb_serov_predictions_count(
        self,
        standings: list[StandingRow],
        login_to_uid: dict[str, int],
    ) -> None:
        """[LB-TOTALS] serov has exactly 64 total_predictions (no round-4 predictions)."""
        serov_uid = login_to_uid["serov"]
        row = next(r for r in standings if r.user_id == serov_uid)
        assert row.total_predictions == 64, (
            f"serov total_predictions={row.total_predictions} expected=64"
        )

    def test_lb_others_predictions_count(
        self,
        standings: list[StandingRow],
        login_to_uid: dict[str, int],
    ) -> None:
        """[LB-TOTALS] all users except serov have exactly 72 total_predictions."""
        serov_uid = login_to_uid["serov"]
        failures: list[str] = []
        for row in standings:
            if row.user_id == serov_uid:
                continue
            if row.total_predictions != 72:
                failures.append(
                    f"  user_id={row.user_id} total_predictions={row.total_predictions} expected=72"
                )
        assert not failures, "[LB-TOTALS] Non-serov prediction count failures:\n" + "\n".join(failures)


# ===========================================================================
# Edge / boundary tests (synthetic data, no CSV)
# ===========================================================================


RULES_STUB = {
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
    }
}


class TestEdgeCases:

    def test_edge_null_missing_prediction_awards_no_points(self) -> None:
        """[EDGE-NULL] User with no prediction row scores 0 even when result is 0:0."""
        results = [MatchResult(match_id=1, score1=0, score2=0, is_scorable=True)]
        # user_id=1 has a prediction; user_id=2 does NOT
        predictions = [UserPrediction(user_id=1, match_id=1, score1=0, score2=0)]
        scores = score_round(results, predictions, participant_ids=[1, 2], rules=RULES_STUB)

        # user_id=2 had no prediction → must score 0
        assert scores[2].base_points == 0, "Missing prediction should earn 0 base points"
        assert scores[2].bonus1 == 0
        assert scores[2].total_with_bonus3 == 0
        assert len(scores[2].per_match) == 0, "No per_match entry for user with no prediction"

        # Sanity: user_id=1 DID predict 0:0 → EXACT (not EXACT_HIGH), earns 12 pts
        assert scores[1].base_points == 12, "0:0 exact prediction should earn 12 (EXACT)"

    def test_edge_zero_exact_not_high(self) -> None:
        """[EDGE-ZERO] 0:0 prediction vs 0:0 result → EXACT (not EXACT_HIGH), earns 12 pts."""
        results = [MatchResult(match_id=1, score1=0, score2=0, is_scorable=True)]
        predictions = [UserPrediction(user_id=1, match_id=1, score1=0, score2=0)]
        scores = score_round(results, predictions, participant_ids=[1], rules=RULES_STUB)

        s = scores[1]
        assert s.base_points == 12, f"0:0 vs 0:0: expected EXACT=12, got {s.base_points}"
        assert s.count_exact == 1, "Should be counted as EXACT"
        assert s.count_exact_high == 0, "Should NOT be counted as EXACT_HIGH"

    def test_edge_tie_dense_rank_three_way(self) -> None:
        """[EDGE-TIE] Three users with equal total → all share rank 1 (dense ranking)."""
        # One match, 3 users all predict correctly the same score
        results = [MatchResult(match_id=1, score1=1, score2=0, is_scorable=True)]
        predictions = [
            UserPrediction(user_id=1, match_id=1, score1=1, score2=0),
            UserPrediction(user_id=2, match_id=1, score1=1, score2=0),
            UserPrediction(user_id=3, match_id=1, score1=1, score2=0),
        ]
        scores = score_round(results, predictions, participant_ids=[1, 2, 3], rules=RULES_STUB)

        ranks = {uid: scores[uid].round_rank for uid in [1, 2, 3]}
        assert ranks[1] == ranks[2] == ranks[3], (
            f"Three-way tie should share same dense rank, got {ranks}"
        )
        assert ranks[1] == 1, f"Top dense rank should be 1, got {ranks[1]}"

    def test_edge_tie_tiebreak_in_standings(self) -> None:
        """[EDGE-TIE] Two users equal total_with_bonus3, different exact_scores_count → standings order."""
        # Build two fake round scores
        def make_round(uid: int, base: int, b1: int, b3: int, exact_high: int, exact: int) -> UserRoundScore:
            return UserRoundScore(
                user_id=uid,
                base_points=base,
                count_exact_high=exact_high,
                count_exact=exact,
                count_diff=0,
                count_outcome=0,
                correct_outcomes=exact_high + exact,
                bonus1=b1,
                bonus2=0,
                bonus3=b3,
                total_without_bonus3=base + b1,
                total_with_bonus3=base + b1 + b3,
                round_rank=1,
                per_match=(),
            )

        # Both users end up at 100 total_with_bonus3 across 1 round
        # uid=1 has 3 exact scores; uid=2 has 1 exact score
        per_user: dict[int, list[UserRoundScore]] = {
            1: [make_round(1, base=90, b1=0, b3=10, exact_high=0, exact=3)],
            2: [make_round(2, base=90, b1=0, b3=10, exact_high=0, exact=1)],
        }
        rows = build_standings(per_user, manual_overrides=None)
        uid_to_rank = {r.user_id: r.rank for r in rows}

        assert uid_to_rank[1] < uid_to_rank[2], (
            f"User with more exact scores should rank higher: uid1 rank={uid_to_rank[1]} uid2 rank={uid_to_rank[2]}"
        )

    def test_edge_void_non_scorable_contributes_zero(self) -> None:
        """[EDGE-VOID] Match with is_scorable=False contributes 0 to everyone, excluded from correct_outcomes."""
        results = [
            MatchResult(match_id=1, score1=2, score2=1, is_scorable=False),  # VOID
            MatchResult(match_id=2, score1=1, score2=0, is_scorable=True),
        ]
        predictions = [
            UserPrediction(user_id=1, match_id=1, score1=2, score2=1),  # would be EXACT on void
            UserPrediction(user_id=1, match_id=2, score1=2, score2=3),  # MISS on scorable
        ]
        scores = score_round(results, predictions, participant_ids=[1], rules=RULES_STUB)

        s = scores[1]
        # Void match contributes 0; only match_id=2 counts (MISS → 0 pts)
        assert s.base_points == 0, f"Void match + MISS should yield 0 base pts, got {s.base_points}"
        # per_match must NOT include the void match
        assert all(ms.match_id != 1 for ms in s.per_match), (
            "Void match should not appear in per_match"
        )
        assert s.correct_outcomes == 0, "Void match should not count toward correct_outcomes"
