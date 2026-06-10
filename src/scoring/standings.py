"""Cross-round aggregation and tie-break ordering for the final standings.

Entry point: :func:`build_standings`.
"""

from __future__ import annotations

from src.scoring.types import StandingRow, UserRoundScore


def build_standings(
    per_user_rounds: dict[int, list[UserRoundScore]],
    manual_overrides: dict[int, int] | None,
    rules: dict | None = None,  # reserved for future config-driven tiebreak order
) -> list[StandingRow]:
    """Aggregate per-round scores and rank users with tie-breaking.

    Parameters
    ----------
    per_user_rounds:
        Mapping user_id → list of UserRoundScore (one entry per counted round).
    manual_overrides:
        Admin-set priorities keyed by user_id; higher integer = better rank.
        Users absent from this dict default to priority 0.
    rules:
        Optional rules dict (reserved; not used in the current implementation
        because the tiebreak field names are structural, not numeric).

    Returns
    -------
    List of StandingRow sorted by final rank (ascending).
    """
    overrides: dict[int, int] = manual_overrides or {}

    rows: list[StandingRow] = []

    for uid, rounds in per_user_rounds.items():
        total_points = sum(r.total_with_bonus3 for r in rounds)
        exact_scores_count = sum(r.count_exact_high + r.count_exact for r in rounds)
        total_without_bonuses = sum(r.base_points for r in rounds)
        correct_diffs_count = sum(r.count_diff for r in rounds)
        exact_high_count = sum(r.count_exact_high for r in rounds)
        exact_count = sum(r.count_exact for r in rounds)
        diff_count = sum(r.count_diff for r in rounds)
        outcome_count = sum(r.count_outcome for r in rounds)
        # Count all match submissions that appear in per_match (i.e. scorable + predicted)
        total_predictions = sum(len(r.per_match) for r in rounds)

        rows.append(
            StandingRow(
                user_id=uid,
                total_points=total_points,
                exact_scores_count=exact_scores_count,
                total_without_bonuses=total_without_bonuses,
                correct_diffs_count=correct_diffs_count,
                exact_high_count=exact_high_count,
                exact_count=exact_count,
                diff_count=diff_count,
                outcome_count=outcome_count,
                total_predictions=total_predictions,
                rank=0,
                tiebreaker_status=None,
            )
        )

    # Sort by tiebreak chain (all DESC → negate for ascending sort key)
    rows.sort(
        key=lambda row: (
            -row.total_points,
            -row.exact_scores_count,
            -row.total_without_bonuses,
            -row.correct_diffs_count,
            -overrides.get(row.user_id, 0),
        )
    )

    # Assign 1-based sequential rank
    for i, row in enumerate(rows):
        row.rank = i + 1

    # Mark users whose position was decided by the manual_override key.
    # A user is marked when they share criteria 1–4 with at least one other user
    # AND the two users differ in their manual_override priority.
    for row in rows:
        for other in rows:
            if row.user_id == other.user_id:
                continue
            tied_on_1_to_4 = (
                row.total_points == other.total_points
                and row.exact_scores_count == other.exact_scores_count
                and row.total_without_bonuses == other.total_without_bonuses
                and row.correct_diffs_count == other.correct_diffs_count
            )
            if tied_on_1_to_4 and overrides.get(row.user_id, 0) != overrides.get(
                other.user_id, 0
            ):
                row.tiebreaker_status = "manual_override"
                break

    return rows
