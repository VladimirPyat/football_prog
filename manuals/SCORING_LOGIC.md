# Scoring Logic

Contest scoring rules, bonuses, tie-breakers, and validation constraints.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Configuration Source](#configuration-source)
- [Base Points](#base-points)
- [Bonuses](#bonuses)
- [Tie-Breakers](#tie-breakers)
- [Validation Constraints](#validation-constraints)
- [Prediction Absence Rule](#prediction-absence-rule)

## Implementation Status [NEW]

| Layer | Status |
|-------|--------|
| Rules stored in DB (`contest_settings.rules_json`) | ✅ Seeded via [CONFIG.md](CONFIG.md) |
| `ScoringService` (runtime calculation) | ❌ Stage 1 — not implemented |
| API endpoints (`/leaderboard`, `/results`) | ❌ Stage 1 — see [API_GUIDE.md](API_GUIDE.md) |

This document describes the **configured rules** loaded at seed time. Calculation logic will read these values from `rules_json` at runtime (Stage 1).

## Configuration Source [NEW]

Default values from `docs/test_data/config/contest_defaults.json`, persisted by `src/scripts/seed.py` into `contest_settings.rules_json`.

Access path at runtime (planned):

```
contest_settings.rules_json → ScoringService → scores table
```

See [DB_REFERENCE.md](DB_REFERENCE.md) for the `scores` table schema.

## Base Points [NEW]

Priority: **Exact > Diff > Outcome**. Only one base type per match.

| Rule key | Points | Condition |
|----------|--------|-----------|
| `exact_high_score` | 16 | Exact match AND (`abs(goal_diff) >= 3` OR `total_goals > 3`) |
| `exact_score` | 12 | Exact match, not high-score |
| `diff_plus_outcome` | 8 | Same goal difference sign and magnitude |
| `outcome_only` | 4 | Same outcome (home win / draw / away win) |
| `miss` | 0 | No match |

**Examples:**

- Prediction `2:1`, result `2:1` → 12 (exact)
- Prediction `2:1`, result `3:2` → 8 (diff + outcome, both +1)
- Prediction `1:0`, result `0:0` → 0 (miss)

Configurable via `rules_json.scoring_rules.base_points`.

## Bonuses [NEW]

Applied on top of base points. See [CONFIG.md](CONFIG.md) for seed defaults.

### Bonus 1 — Unique prediction (`bonus_1_unique_multiplier_pct`)

- **Type:** Percentage of base points for the match
- **Condition:** Exact score predicted by only one participant in that match
- **Default:** `200.0` (200% multiplier)

### Bonus 2 — Correct outcome streak (`bonus_2_thresholds`)

- **Type:** Fixed points by threshold
- **Condition:** Count of matches in the round where at least outcome was guessed (≥4 base points)
- **Default thresholds:**

| Min correct outcomes | Points |
|---------------------|--------|
| 6 | 8 |
| 7 | 12 |
| 8 | 16 |

### Bonus 3 — Round rank (`bonus_3_rank_points`)

- **Type:** Fixed points by leaderboard position
- **Ranking basis:** `base_total` without bonuses 2 and 3
- **Default:**

| Place | Points |
|-------|--------|
| 1st | 12 |
| 2nd | 8 |
| 3rd | 4 |

- Tied scores receive the bonus for the tied rank.
- No bonus 3 if `base_total == 0`.
- Extra trigger: `+4` if `base_total_without_b2_b3 >= 50` (`bonus_3_base_threshold_extra` / `bonus_3_extra_points`).

## Tie-Breakers [NEW]

Final leaderboard ranking when `total_points` are equal. Order from `rules_json.tiebreakers.priority_order`:

1. `total_points DESC`
2. `exact_scores_count DESC` (all exact scores, including high)
3. `total_without_bonuses DESC` (base points only)
4. `correct_diffs_count DESC`
5. `manual_override` — Supervisor assigns priority (fallback)

> Bonuses affect `total_points` only; they are excluded from criteria 2–4.

## Validation Constraints [NEW]

From `rules_json.constraints` (seeded defaults):

| Key | Default | Meaning |
|-----|---------|---------|
| `allow_partial_prediction_save` | `false` | Batch-only: all matches or none |
| `require_all_matches_per_round` | `true` | Every round match must be predicted |
| `score_validation_range` | `[0, 20]` | Enforced at DB CHECK — see [DB_REFERENCE.md](DB_REFERENCE.md) |
| `max_teams_per_round_usage` | `1` | Team appears at most once per round |

Structural limits from `contest_structure`:

| Key | Default |
|-----|---------|
| `deadline_rule_hours` | `24` |
| `max_score_value` | `20` |

Round-robin validation (when `is_round_robin=true`):

- `matches_per_round == total_teams / 2`
- `total_rounds == (total_teams - 1) * 2`

## Prediction Absence Rule [NEW]

**Before → After:** Rules existed in spec only. Stage 0 DB now enforces score validity; absence semantics are tested.

| Scenario | Correct representation |
|----------|------------------------|
| Player predicts `0:0` | Row with `score1=0, score2=0` |
| Player did not predict | **No row** in `predictions` |
| Player gets points for match | Only if prediction row exists and matches result |

A player without a prediction row must receive **0 points** for that match when scoring runs (Stage 1). Never infer absence from `0` or default NULL rows.
