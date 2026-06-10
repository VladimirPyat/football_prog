# Scoring Flow & Tie-breakers (Stage 1) — DRAFT

> Status: DRAFT for review. The **base points** section is VERIFIED against
> `docs/test_data/contracted/` (89/89 user-rounds reproduce `expected_base_pts`).
> The **bonuses** section is BLOCKED — documented rules do not reproduce the
> reference `expected_bonus*` / `expected_total`. See `agent_docs/reports/BLOCKED.md`.
> All numeric values, thresholds and multipliers are read from
> `contest_settings.rules_json` (seeded from `contest_defaults.json`). Only the
> structure of the rules is hard-coded, never the values.

## 0. Inputs & NULL semantics (CRITICAL)
- A prediction exists only if there is a `predictions` row for `(user_id, match_id)`.
- A missing prediction = NO row = excluded from scoring. NEVER treat missing as `0:0`.
- `0` is a valid predicted/actual goal count. Scoring must check `IS NOT NULL`,
  never `!= 0` and never `dict.get('score', 0)`.
- Only matches with `status = FINISHED` and non-NULL `score1/score2` are scored.
  `VOID` / `SCHEDULED` / `CANCELED` / `POSTPONED` contribute 0 and are excluded
  from "correct outcomes" counts.

## 1. Base Points — VERIFIED
For each scored match, exactly ONE category is awarded. Priority: Exact > Diff > Outcome.

```
pred_diff = pred1 - pred2
res_diff  = res1  - res2
sum_goals = res1  + res2
sign(x)   = 1 if x>0 ; -1 if x<0 ; 0 if x==0
```

1. exact_high_score (16): pred1==res1 AND pred2==res2 AND (abs(res_diff) >= 3 OR sum_goals > 3)
2. exact_score      (12): pred1==res1 AND pred2==res2 AND NOT exact_high_score
3. diff_plus_outcome (8): sign(pred_diff)==sign(res_diff) AND abs(pred_diff)==abs(res_diff) AND NOT exact
4. outcome_only      (4): sign(pred_diff)==sign(res_diff) AND NOT diff_plus_outcome AND NOT exact
5. miss              (0): otherwise

Values come from `rules_json.scoring_rules.base_points`.

**Verification:** a reference implementation of the above reproduces
`expected_base_pts` for all 89 user-rounds in rounds 1–9. This is the golden
invariant for Stage 1 base-scoring tests.

### Per-match category counters (engine output)
The engine SHOULD record, per match, which exclusive category was awarded, and
derive per-round:
- `count_exact_high` = # matches awarded category 1
- `count_exact`      = # matches awarded category 2
- `count_diff`       = # matches awarded category 3
- `count_outcome`    = # matches awarded category 4
- `correct_outcomes` = # matches with base >= 4 (categories 1..4) — used by Bonus 2

> NOTE: `leaderboard.csv` count columns are correct (engine aggregates match 10/10).
> The per-round `count_*` columns in `expected_scores.csv` were inconsistent (52/90);
> the user corrects the 38 rows per `agent_docs/reports/count_fix_reference.md`. Engine
> counters are EXCLUSIVE (one category per match); after correction they are cross-checked
> per-row by @Tester (gated on `16·eh+12·ex+8·di+4·ou == expected_base_pts`).

## 2. Bonuses — VERIFIED (see `agent_docs/contracts/bonus_rules.md`)
Resolved with user clarification (2026-06-10). The full algorithm with worked
examples lives in `agent_docs/contracts/bonus_rules.md` and reproduces
`expected_total` 89/89 and `expected_bonus3` 89/89. Summary:

- **Bonus 1** — unique correct **OUTCOME** (1/X/2, not exact score): if exactly one
  participant predicted the outcome that occurred, that user gets
  `base_match_points * bonus_1_unique_multiplier_pct / 100` (×2 at 200%). Summed over the round.
- **Bonus 2** — by `correct_outcomes` (matches with base ≥ 4): 6→8, 7→12, 8→16 (highest threshold).
- **Bonus 3** — basis = `base + bonus1 + bonus2`. Rank by distinct basis desc:
  1st→12, 2nd→8, 3rd→4 (ties share place, all get the points); plus
  `bonus_3_extra_points` if `basis >= bonus_3_base_threshold_extra`; nothing if `base_total == 0`.

> FIXTURE QUIRK: in `expected_scores.csv` Bonus 2 is folded into the
> `expected_bonus1` column (`expected_bonus2` is always 0). Verify via
> `engine.bonus1 + engine.bonus2 == expected_bonus1` or via `expected_total`.

## 3. Tie-breaking (global / per-round leaderboard)
Order from `rules_json.tiebreakers.priority_order`:
1. total_points DESC
2. exact_scores_count DESC (count of ALL exact, high + normal)
3. total_without_bonuses DESC (sum of base points only; excl. B1/B2/B3)
4. correct_diffs_count DESC (count of diff_plus_outcome matches)
5. manual_override (Supervisor decision via override endpoint; `tiebreaker_status`)

Bonuses affect `total_points` only; they are excluded from criteria 2–4.

## 4. VOID matches
On `status = VOID`:
- All base points for the match = 0; Bonus 1 for the match = 0.
- Bonus 2 / Bonus 3 recomputed for the round over remaining valid matches.
- Recalculation is atomic (single transaction) for ALL users in the round.

## 5. Transactionality
- `POST /admin/rounds/{id}/calculate`: compute and upsert `scores` for all
  participants in one transaction; round `CLOSED -> CALCULATED`.
- Any VOID/result change after calculation re-runs the round calc atomically.
