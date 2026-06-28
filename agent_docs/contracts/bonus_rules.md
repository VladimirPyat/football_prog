# Bonus Calculation Rules (VERIFIED) — Stage 1

> Status: VERIFIED against `docs/test_data/contracted/` — the algorithm below
> reproduces `expected_total` for **89/89** user-rounds (rounds 1–9) and
> `expected_bonus3` for 89/89. All numeric values come from
> `contest_settings.rules_json.scoring_rules.bonuses` (seeded from
> `contest_defaults.json`). Hard-code only the structure, never the numbers.
>
> Prereq: base points per match are already computed (see
> `agent_docs/dataflow/scoring_flow.md` §1, also verified 89/89). Only FINISHED
> matches with non-NULL scores are scored. A missing prediction = no row =
> excluded (never treated as 0:0).

Config snapshot (current `contest_defaults.json`):
```
bonus_1_unique_multiplier_pct : 200.0
bonus_2_thresholds            : [{6 -> 8}, {7 -> 12}, {8 -> 16}]
bonus_3_rank_points           : {1st: 12, 2nd: 8, 3rd: 4}
bonus_3_base_threshold_extra  : 50
bonus_3_extra_points          : 4
```

Definitions used below:
- `outcome(p1,p2)` = sign(p1 - p2) → HOME (1), DRAW (0), AWAY (-1).
- `base_m(user)` = base points the user earned on match `m` (0/4/8/12/16).
- A match is a **correct outcome** for a user if `base_m(user) >= 4`
  (i.e. outcome guessed; includes diff and exact).

---

## BONUS 1 — Unique correct outcome (per match, summed over the round)

Rule: For a given match, if **exactly one** participant predicted the outcome
(HOME/DRAW/AWAY) that actually happened, that single participant gets a bonus of
`bonus_1_unique_multiplier_pct %` of the base points they earned on that match.
Summed across all such matches in the round.

```
for each finished match m in round:
    actual_outcome = outcome(result1_m, result2_m)
    predictors = [u for u in users if u predicted m and outcome(u.pred) == actual_outcome]
    if len(predictors) == 1:
        u = predictors[0]                       # earned base_m(u) >= 4 by definition
        bonus1[u] += int(base_m(u) * bonus_1_unique_multiplier_pct / 100)
```
Notes:
- Uniqueness is over the **outcome** (1/X/2), NOT the exact score.
- Only the winning outcome matters; players who uniquely predicted a wrong
  outcome get nothing.
- With 200% the bonus equals `2 × base_m`.

### Worked examples (Round 1)
- **shutov**, Дин–Балт: predicted 2:2 (DRAW), result 1:1 (DRAW) → base = 8 (diff).
  Only shutov predicted a draw on this match → bonus1 += 8 × 2 = **16**.
- **starchenkov_c**, Орен–ЦСКА: predicted 1:1 (DRAW), result 0:0 (DRAW) → base = 8.
  Only draw-predictor → bonus1 += 8 × 2 = **16**.
- **kuznetsov**, Ахм–Руб: predicted 0:1 (AWAY), result 0:2 (AWAY) → base = 4 (outcome).
  Only away-predictor → bonus1 += 4 × 2 = **8**.
- **volchenko**, Лок–Сочи: predicted 2:0 (HOME), result 3:0 (HOME) → base = 4,
  but several others also predicted HOME → NOT unique → bonus1 += 0.

---

## BONUS 2 — Series of correct outcomes (per round)

Rule: Count `correct_outcomes` = number of matches in the round where the user
earned `base_m >= 4` (includes outcome, diff, exact). Map to the highest
applicable threshold.

```
n = count(matches with base_m >= 4)
bonus2 = 0
for t in bonus_2_thresholds (ascending): if n >= t.min: bonus2 = t.points
# 6 -> 8, 7 -> 12, 8 -> 16
```

### Worked example (Round 3)
- **kuznetsov** guessed 6 correct outcomes (incl. diffs/exact) → bonus2 = **8**.
- **starchenkov_c** guessed 6 correct outcomes → bonus2 = **8**.

> FIXTURE QUIRK (important for @Tester): in `expected_scores.csv` the Bonus 2
> amount is folded INTO the `expected_bonus1` column, and the `expected_bonus2`
> column is always 0. Therefore verify as:
> `engine.bonus1 + engine.bonus2 == expected_bonus1` and `expected_bonus2 == 0`,
> or simply verify `expected_total`. The engine MUST still store bonus1 and
> bonus2 separately with correct semantics.

---

## BONUS 3 — Round ranking + high-score bonus (per round)

Ranking basis: `basis(u) = base_total(u) + bonus1(u) + bonus2(u)`
(i.e. points WITH bonus 1 and 2, but WITHOUT bonus 3 itself).

```
# Part A: high-score bonus
extra(u) = bonus_3_extra_points if basis(u) >= bonus_3_base_threshold_extra else 0

# Part B: rank bonus (by DISTINCT basis value, descending)
place(u) = rank of basis(u) among distinct basis values (1 = highest)
rank_pts(u) = 12 if place==1 ; 8 if place==2 ; 4 if place==3 ; else 0
# TIES: all users sharing the same basis value share the same place and ALL
#       receive that place's points.

bonus3(u) = rank_pts(u) + extra(u)

# Guard: if base_total(u) == 0  ->  bonus3(u) = 0  (no rank, no extra)
```

### Worked examples
**Round 3** (basis with bonus1+bonus2):
- **starchenkov_c**: place 1 → 12, basis ≥ 50 → +4 = **16**.
- **kuznetsov**: place 2 → 8, basis ≥ 50 → +4 = **12**.
- **russkov**: place 3 → 4 (basis < 50) = **4**.

**Round 1** (tie example):
- **kuznetsov** basis = 36 and **russkov** basis = 36 → tie for 3rd place →
  BOTH receive **4** (neither reaches 50, so no +4).
- **starchenkov_c** basis = 56 → place 1 (12) + ≥50 (4) = **16**.
- **shutov** basis = 44 → place 2 (8), < 50 → no extra = **8**.

---

## Order of computation (per round, atomic)
1. Base points per match (and `correct_outcomes`).
2. Bonus 1 (needs all users' predictions per match for uniqueness).
3. Bonus 2 (needs `correct_outcomes`).
4. Bonus 3 (needs `basis = base + bonus1 + bonus2` for ALL users → ranking).
5. Totals: `total_with_bonus3 = base + bonus1 + bonus2 + bonus3`;
   `total_without_bonus3 = base + bonus1 + bonus2`.

On VOID / result change, re-run the whole round in one transaction.

---

## Deferred bonuses — postponed matches & supplementary rounds (Stage 2.3+)

> **Status:** CONTRACT — engine implementation follows in a later stage.
> **Related:** `agent_docs/contracts/scoring_flow.md` §6,
> `agent_docs/contracts/contest_lifecycle_flow.md` §4,
> `matches.origin_round_id`, `rounds.kind = SUPPLEMENTARY`.

### Logical tour

A **logical tour** is the scoring unit keyed by the **origin** (regular) round `R_id`:

- all matches still in `R_id`, plus
- all matches with `origin_round_id = R_id` (moved to ДопТур / supplementary rounds).

`scores` rows remain **`UNIQUE (user_id, round_id)` with `round_id = R_id`** — no separate
score row for supplementary rounds. Base points from a postponed match are added to the
**same** `scores` row when the match is played in ДопТур.

### When base points vs bonuses are settled

| Phase | What is written to `scores` for `R_id` |
|-------|----------------------------------------|
| Main matches finished, tour `CLOSED` → `calculate` | **Base points** (+ per-match Bonus 1) for every **FINISHED** match in the logical tour that has a result so far. **Bonus 2 and Bonus 3 are NOT final** if bonuses are pending. |
| Postponed match played in ДопТур → result entered | **Add** base (+ Bonus 1) for that match into the existing `scores` row for `R_id`. |
| All non-excluded matches in logical tour terminal | **Recompute Bonus 2 and Bonus 3** for `R_id` in the same `scores` row; clear pending state. |

### Excluded matches (do not block bonuses)

Matches with status **`CANCELED`** or **`VOID`** are **removed from the logical tour**
for bonus purposes (e.g. technical defeat). They do not count toward `correct_outcomes`
and are not waited on.

Matches still **`POSTPONED`** or **`SCHEDULED`** (including in ДопТур) **block** Bonus 2/3.

### API / UI

`GET …/rounds/{origin_round_id}/leaderboard` includes:

- `bonuses_pending: true` while any logical-tour match is `POSTPONED` or `SCHEDULED`
  (excluding only `CANCELED`/`VOID`);
- `bonuses_pending_message` — human-readable note for supervisors and participants.

While `bonuses_pending`, UI shows that **bonuses will be calculated later**; displayed
`bonus2` / `bonus3` / `total_with_bonus3` may be provisional or zero until final pass.

**Admin UI matrix (visibility, predictions, deferred bonuses):** [admin_ui_status_matrix.md](admin_ui_status_matrix.md)
