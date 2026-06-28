# Scoring Flow & Tie-breakers

## 1. Overview
This document defines the exact logic for calculating points for user predictions based on match results. The logic is immutable and reads numerical values from `contest_settings`.

## 2. Base Points Calculation
For each match, exactly ONE of the following base point categories is awarded (priority order: Exact > Diff > Outcome).

Let `pred1`, `pred2` be the predicted scores.
Let `res1`, `res2` be the actual match scores.
Let `pred_diff = pred1 - pred2` and `res_diff = res1 - res2`.
Let `sum_goals = res1 + res2`.

1. **Exact High Score (`exact_high_score`: 16 pts)**
   - Condition: `pred1 == res1` AND `pred2 == res2` AND (`abs(res_diff) >= 3` OR `sum_goals > 3`)
2. **Exact Score (`exact_score`: 12 pts)**
   - Condition: `pred1 == res1` AND `pred2 == res2` AND NOT Exact High Score
3. **Diff + Outcome (`diff_plus_outcome`: 8 pts)**
   - Condition: `sign(pred_diff) == sign(res_diff)` AND `abs(pred_diff) == abs(res_diff)` AND NOT Exact Score
4. **Outcome Only (`outcome_only`: 4 pts)**
   - Condition: `sign(pred_diff) == sign(res_diff)` AND NOT Diff + Outcome AND NOT Exact Score
5. **Miss (`miss`: 0 pts)**
   - Condition: Any other case.

*Note: `sign(x)` returns 1 for x>0, -1 for x<0, and 0 for x=0.*

## 3. Bonuses Calculation
Bonuses are calculated per round and added on top of base points.

1. **Bonus 1: Unique Prediction (`bonus1`)**
   - Condition: If `count_users_with_this_exact_prediction == 1` for a specific match.
   - Value: `base_points_earned_for_this_match * (bonus_1_unique_multiplier_pct / 100)`.
   - Example: 100% multiplier means doubling the base points.

2. **Bonus 2: Series of Correct Outcomes (`bonus2`)**
   - Condition: Count the number of matches in the round where the user earned >= 4 pts (`correct_outcomes`).
   - Value: Match `correct_outcomes` against `bonus_2_thresholds` (e.g., 6 -> 8 pts, 7 -> 12 pts, 8 -> 16 pts). Take the highest applicable threshold.

3. **Bonus 3: Round Leaderboard Rank (`bonus3`)**
   - Condition: Rank users in the round by `base_total` (sum of base points + Bonus 1, but NOT Bonus 2 and Bonus 3).
   - Value: 
     - 1st place -> 12 pts
     - 2nd place -> 8 pts
     - 3rd place -> 4 pts
   - Note: Users with the same `base_total` share the rank. If `base_total == 0`, Bonus 3 is NOT awarded.
   - Extra Trigger: If `base_total >= bonus_3_base_threshold_extra` (e.g., 50), add `bonus_3_extra_points` (e.g., 4 pts).

## 4. Tie-breaking Rules (Global Leaderboard)
When ranking users globally or per round, if `total_points` is equal, apply the following fallbacks in order:

1. `total_points DESC`
2. `exact_scores_count DESC` (Count of ALL exact scores, both high and normal)
3. `total_without_bonuses DESC` (Sum of base points ONLY, excluding Bonus 1, 2, 3)
4. `correct_diffs_count DESC` (Count of matches where Diff + Outcome was awarded)
5. `manual_override` (Supervisor manual decision, very rare)

## 5. VOID Matches
If a match status is set to `VOID`:
- All base points for this match = 0.
- Bonus 1 for this match = 0.
- Bonus 2 and Bonus 3 must be recalculated for the round based on the remaining valid matches.

## 6. Postponed matches & supplementary rounds (ДопТур)

> **Status:** CONTRACT (Stage 2.3+). Scoring engine defers Bonus 2/3 per
> `agent_docs/contracts/bonus_rules.md` — Deferred bonuses.

### 6.1 Logical tour

Scoring for a regular round **R** includes:

1. Matches with `match.round_id = R.id`.
2. Matches with `match.origin_round_id = R.id` (played in a supplementary / free tour).

Supplementary rounds (`rounds.kind = SUPPLEMENTARY`) are **operational containers** for
rescheduling; they are **not** separate scoring rounds.

### 6.2 Persistence (`scores` table — unchanged schema)

- One row per `(user_id, origin_round_id)` — **no new table**.
- Base points accumulate in that row as each match in the logical tour finishes.
- `bonus1` per match is applied when that match's base is known.
- `bonus2`, `bonus3`, `total_without_bonus3`, `total_with_bonus3` are **final only when**
  all non-excluded matches in the logical tour are terminal (`FINISHED`, or excluded).

### 6.3 Settlement timeline

```
Regular tour R: main matches FINISHED → close R → calculate
  → write base (+ bonus1) for finished main matches
  → if any POSTPONED / SCHEDULED postponed match remains → bonuses_pending

Later: POSTPONED → free tour → ДопТур D → match FINISHED
  → add base (+ bonus1) to scores(round_id=R)
  → when no pending matches left → recompute bonus2, bonus3 for R
```

### 6.4 Canceled matches

`CANCELED` (and `VOID`) matches are **excluded** from the logical tour for bonus
thresholds — they neither contribute to `correct_outcomes` nor block bonus settlement.
Rare case: technical defeat / disciplinary cancel.

### 6.5 Client visibility

`GET /contests/{id}/rounds/{round_id}/leaderboard` for the **origin** round returns:

| Field | Meaning |
|-------|---------|
| `bonuses_pending` | `true` while Bonus 2/3 are not final |
| `bonuses_pending_message` | e.g. «Бонусы тура будут рассчитаны после сыгранных перенесённых матчей…» |

UI must show this note on admin results / leaderboard preview while pending.

**Cross-page UI matrix:** [admin_ui_status_matrix.md](admin_ui_status_matrix.md) §11–§12.
