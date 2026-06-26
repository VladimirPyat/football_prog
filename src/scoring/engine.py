"""Pure scoring engine — no database, no I/O.

Entry point: :func:`score_round`.
All numeric constants are sourced from the ``rules`` dict via :class:`ScoringRules`.
"""

from __future__ import annotations

from src.scoring.rules import ScoringRules
from src.scoring.types import (
    Category,
    MatchResult,
    MatchScore,
    UserPrediction,
    UserRoundScore,
)

# --------------------------------------------------------------------------- helpers


def _sign(x: int) -> int:
    """Return 1 / 0 / -1 for positive / zero / negative x."""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _categorize(
    r1: int, r2: int, p1: int, p2: int, sr: ScoringRules
) -> tuple[Category, int]:
    """Return (Category, base_points) for a single prediction vs a known result."""
    if p1 == r1 and p2 == r2:
        # EXACT_HIGH: predicted exactly AND the match was high-stakes
        # (large goal difference OR high-scoring game)
        if abs(r1 - r2) >= 3 or r1 + r2 > 3:
            return Category.EXACT_HIGH, sr.exact_high_score
        return Category.EXACT, sr.exact_score

    pred_sign = _sign(p1 - p2)
    res_sign = _sign(r1 - r2)

    if pred_sign == res_sign:
        # DIFF: correct sign AND same absolute goal difference (but NOT exact score)
        if abs(p1 - p2) == abs(r1 - r2):
            return Category.DIFF, sr.diff_plus_outcome
        # OUTCOME: correct sign only
        return Category.OUTCOME, sr.outcome_only

    return Category.MISS, sr.miss


def _compute_bonus2(n_correct: int, sr: ScoringRules) -> int:
    """Return bonus 2 for a given count of correct outcomes in a round."""
    bonus2 = 0
    for threshold in sr.bonus_2_thresholds:
        if n_correct >= threshold["min_correct_outcomes"]:
            bonus2 = threshold["points"]
    return bonus2


# --------------------------------------------------------------------------- engine


def score_round(
    results: list[MatchResult],
    predictions: list[UserPrediction],
    participant_ids: list[int],
    rules: dict,
) -> dict[int, UserRoundScore]:
    """Score one round for all participants.

    Parameters
    ----------
    results:
        All match results for the round (scorable and non-scorable).
    predictions:
        All user predictions for the round.  A missing prediction row means
        the user did NOT submit — it is NEVER treated as 0:0.
    participant_ids:
        Full participant list, including users who submitted no predictions.
    rules:
        The contest rules dict (shape of contest_defaults.json).

    Returns
    -------
    dict mapping user_id → UserRoundScore.
    """
    sr = ScoringRules(rules)

    # Index only scorable matches
    scorable: dict[int, MatchResult] = {
        r.match_id: r for r in results if r.is_scorable
    }

    # Index predictions — absence of key means user did NOT predict that match
    pred_index: dict[tuple[int, int], UserPrediction] = {
        (p.user_id, p.match_id): p for p in predictions
    }

    all_uids: list[int] = list(participant_ids)

    # ------------------------------------------------------------------ step 1
    # Base category and points per (user_id, match_id).
    # Only populated when the user explicitly submitted a prediction.
    base_map: dict[tuple[int, int], tuple[Category, int]] = {}

    for match_id, result in scorable.items():
        for uid in all_uids:
            pred = pred_index.get((uid, match_id))
            if pred is not None:
                cat, pts = _categorize(
                    result.score1,  # type: ignore[arg-type]
                    result.score2,  # type: ignore[arg-type]
                    pred.score1,
                    pred.score2,
                    sr,
                )
                base_map[(uid, match_id)] = (cat, pts)

    # ------------------------------------------------------------------ step 2
    # Bonus 1: unique correct-outcome predictor per match.
    # bonus1_match[(uid, match_id)] = bonus earned on that specific match
    bonus1_match: dict[tuple[int, int], int] = {}
    bonus1_user: dict[int, int] = {uid: 0 for uid in all_uids}

    for match_id, result in scorable.items():
        actual_outcome = _sign(result.score1 - result.score2)  # type: ignore[operator]

        # Participants who predicted this match AND predicted the winning outcome
        correct_predictors: list[int] = [
            uid
            for uid in all_uids
            if (uid, match_id) in base_map
            and _sign(
                pred_index[(uid, match_id)].score1
                - pred_index[(uid, match_id)].score2
            )
            == actual_outcome
        ]

        if len(correct_predictors) == 1:
            uid = correct_predictors[0]
            base_pts = base_map[(uid, match_id)][1]
            b1 = int(base_pts * sr.bonus_1_unique_multiplier_pct / 100)
            bonus1_match[(uid, match_id)] = b1
            bonus1_user[uid] += b1

    # ------------------------------------------------------------------ step 3
    # Aggregate per-user base totals and category counters.
    base_totals: dict[int, int] = {uid: 0 for uid in all_uids}
    count_eh: dict[int, int] = {uid: 0 for uid in all_uids}
    count_ex: dict[int, int] = {uid: 0 for uid in all_uids}
    count_di: dict[int, int] = {uid: 0 for uid in all_uids}
    count_ou: dict[int, int] = {uid: 0 for uid in all_uids}
    correct_outs: dict[int, int] = {uid: 0 for uid in all_uids}

    for (uid, _match_id), (cat, pts) in base_map.items():
        base_totals[uid] += pts
        if cat == Category.EXACT_HIGH:
            count_eh[uid] += 1
        elif cat == Category.EXACT:
            count_ex[uid] += 1
        elif cat == Category.DIFF:
            count_di[uid] += 1
        elif cat == Category.OUTCOME:
            count_ou[uid] += 1
        if pts >= sr.outcome_only:
            correct_outs[uid] += 1

    # ------------------------------------------------------------------ step 4
    # Bonus 2: series of correct outcomes.
    bonus2_user: dict[int, int] = {
        uid: _compute_bonus2(correct_outs[uid], sr) for uid in all_uids
    }

    # ------------------------------------------------------------------ step 5
    # Bonus 3: ranking + high-score extra.
    # basis = base + bonus1 + bonus2
    basis: dict[int, int] = {
        uid: base_totals[uid] + bonus1_user[uid] + bonus2_user[uid]
        for uid in all_uids
    }

    # Guard: users with base_total == 0 are excluded from ranking
    eligible: list[int] = [uid for uid in all_uids if base_totals[uid] > 0]

    rank_pts_cfg = sr.bonus_3_rank_points
    rank_pts_by_place: dict[int, int] = {
        1: rank_pts_cfg.get("1st", 0),
        2: rank_pts_cfg.get("2nd", 0),
        3: rank_pts_cfg.get("3rd", 0),
    }

    # Rank by DISTINCT basis values descending
    distinct_basis: list[int] = sorted(
        {basis[uid] for uid in eligible}, reverse=True
    )
    # Map each distinct value to its 1-based place
    place_of: dict[int, int] = {v: i + 1 for i, v in enumerate(distinct_basis)}

    bonus3_user: dict[int, int] = {uid: 0 for uid in all_uids}
    for uid in eligible:
        place = place_of[basis[uid]]
        rank_pts = rank_pts_by_place.get(place, 0)
        extra = (
            sr.bonus_3_extra_points
            if basis[uid] >= sr.bonus_3_base_threshold_extra
            else 0
        )
        bonus3_user[uid] = rank_pts + extra

    # ------------------------------------------------------------------ step 6
    # Build per-match MatchScore objects (only for matches user predicted).
    per_match_map: dict[int, list[MatchScore]] = {uid: [] for uid in all_uids}
    for (uid, match_id), (cat, pts) in base_map.items():
        per_match_map[uid].append(
            MatchScore(
                match_id=match_id,
                category=cat,
                base_points=pts,
                bonus1_points=bonus1_match.get((uid, match_id), 0),
            )
        )

    # ------------------------------------------------------------------ step 7
    # Totals and dense round_rank by total_with_bonus3 descending.
    totals_wb3: dict[int, int] = {
        uid: base_totals[uid] + bonus1_user[uid] + bonus2_user[uid] + bonus3_user[uid]
        for uid in all_uids
    }
    totals_wob3: dict[int, int] = {
        uid: base_totals[uid] + bonus1_user[uid] + bonus2_user[uid]
        for uid in all_uids
    }

    # Dense ranking: rank(u) = 1 + count of DISTINCT total values strictly higher.
    # Equal totals share the same rank; the next distinct lower total gets rank+1.
    # Example: 30,20,20,10 → 1,2,2,3  (not 1,2,2,4)
    distinct_totals: set[int] = set(totals_wb3.values())
    round_rank_of: dict[int, int] = {
        uid: 1 + sum(1 for v in distinct_totals if v > totals_wb3[uid])
        for uid in all_uids
    }

    return {
        uid: UserRoundScore(
            user_id=uid,
            base_points=base_totals[uid],
            count_exact_high=count_eh[uid],
            count_exact=count_ex[uid],
            count_diff=count_di[uid],
            count_outcome=count_ou[uid],
            correct_outcomes=correct_outs[uid],
            bonus1=bonus1_user[uid],
            bonus2=bonus2_user[uid],
            bonus3=bonus3_user[uid],
            total_without_bonus3=totals_wob3[uid],
            total_with_bonus3=totals_wb3[uid],
            round_rank=round_rank_of[uid],
            per_match=tuple(per_match_map[uid]),
        )
        for uid in all_uids
    }
