# Scoring Logic

Contest scoring rules, bonuses, tie-breakers, and engine implementation.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Configuration Source](#configuration-source)
- [Engine Architecture](#engine-architecture)
- [Base Points](#base-points)
- [Bonuses](#bonuses)
- [Computation Order](#computation-order)
- [Per-Round Rank](#per-round-rank)
- [Tie-Breakers and Final Standings](#tie-breakers-and-final-standings)
- [Scoring Persistence](#scoring-persistence)
- [Validation Constraints](#validation-constraints)
- [Prediction Absence Rule](#prediction-absence-rule)

## Implementation Status [UPDATED]

| Layer | Status |
|-------|--------|
| Rules stored in DB (`contests.rules_json`) | ✅ Seeded via [CONFIG.md](CONFIG.md) |
| Pure scoring engine (`src/scoring/`) | ✅ Stage 1.1 — implemented and verified (90/90) |
| Scoring persistence (`src/services/scoring_persistence.py`) | ✅ Stage 1.2 — implemented and verified (90/90) |
| Leaderboard service (`src/services/leaderboard_service.py`) | ✅ Stage 1.3 — aggregates scores + tie-break [NEW] |
| API endpoints (`/leaderboard`, `/results`) | ✅ Stage 1.3 — see [API_GUIDE.md](API_GUIDE.md) [UPDATED] |

## Configuration Source [UPDATED]

Default values from `docs/test_data/config/contest_defaults.json`, persisted by `src/scripts/seed.py` into `contests.rules_json`.

Runtime access path:

```
contests.rules_json → ScoringRules accessor → score_round() → Score rows in DB
```

See [DB_REFERENCE.md](DB_REFERENCE.md) for the `scores` table schema.

## Engine Architecture [NEW]

The scoring engine is a **pure Python module** with no database or I/O dependencies. All numeric constants are read from the `rules` dict via `ScoringRules`.

| File | Role |
|------|------|
| `src/scoring/types.py` | Input/output dataclasses: `MatchResult`, `UserPrediction`, `UserRoundScore`, `StandingRow`, `Category` enum |
| `src/scoring/rules.py` | `ScoringRules` — typed accessor over `rules_json`; no magic numbers in engine code |
| `src/scoring/engine.py` | `score_round(results, predictions, participant_ids, rules) → dict[user_id, UserRoundScore]` |
| `src/scoring/standings.py` | `build_standings(per_user_rounds, manual_overrides) → list[StandingRow]` |

### Key types

```python
@dataclass(frozen=True)
class UserRoundScore:
    user_id: int
    base_points: int
    count_exact_high: int   # exclusive hit counts (frequency, not points)
    count_exact: int
    count_diff: int
    count_outcome: int
    correct_outcomes: int   # base_points >= 4
    bonus1: int
    bonus2: int
    bonus3: int
    total_without_bonus3: int   # base + bonus1 + bonus2
    total_with_bonus3: int      # + bonus3
    round_rank: int             # dense rank within the round
    per_match: tuple[MatchScore, ...]

@dataclass
class StandingRow:
    user_id: int
    total_points: int
    exact_scores_count: int       # sum of exact_high + exact across rounds
    total_without_bonuses: int    # sum of base_points only
    correct_diffs_count: int
    exact_high_count: int; exact_count: int; diff_count: int; outcome_count: int
    total_predictions: int
    rank: int
    tiebreaker_status: str | None  # "manual_override" when manual key decided order
```

## Base Points [UPDATED]

One exclusive category per match. `sign(x) = 1 / 0 / -1`.

| Category | Key | Points | Condition |
|----------|-----|--------|-----------|
| `EXACT_HIGH` | `exact_high_score` | 16 | `p==r` AND (`abs(r1-r2) >= 3` OR `r1+r2 > 3`) |
| `EXACT` | `exact_score` | 12 | `p==r`, not high |
| `DIFF` | `diff_plus_outcome` | 8 | `sign(p1-p2)==sign(r1-r2)` AND same absolute diff |
| `OUTCOME` | `outcome_only` | 4 | `sign(p1-p2)==sign(r1-r2)` only |
| `MISS` | `miss` | 0 | Otherwise |

**Examples:**
- `2:1` predicted, `2:1` result → `EXACT` (12 pts; diff=1, sum=3 — not high)
- `3:0` predicted, `3:0` result → `EXACT_HIGH` (16 pts; diff=3 ≥ 3)
- `2:1` predicted, `3:2` result → `DIFF` (8 pts; both +1)
- `2:0` predicted, `3:0` result → `OUTCOME` (4 pts; same sign, different diff)
- `0:0` predicted, `0:0` result → `EXACT` (12 pts; 0:0 is a real score, not absence)

Configurable via `rules_json.scoring_rules.base_points`.

## Bonuses [UPDATED]

Applied on top of base points. See [CONFIG.md](CONFIG.md) for seed defaults.

### Bonus 1 — Unique correct outcome (`bonus_1_unique_multiplier_pct`)

- **Scope:** Per match, summed over the round.
- **Condition:** Exactly one participant predicted the outcome (HOME/DRAW/AWAY) that actually occurred. That participant gets `int(base_pts * pct / 100)`.
- **Uniqueness:** On the **outcome** (1/X/2), NOT on the exact score.
- **Default multiplier:** `200.0` → bonus = 2 × base points for that match.
- **Guard:** User must have actually predicted that match (absence = no bonus, no penalty).

### Bonus 2 — Series of correct outcomes (`bonus_2_thresholds`)

- **Scope:** Per round.
- **Condition:** Count of matches where `base_points >= 4` (outcome guessed correctly).
- **Default thresholds** (highest applicable wins):

| Min correct outcomes | Bonus points |
|---------------------|--------------|
| 6 | 8 |
| 7 | 12 |
| 8 | 16 |

### Bonus 3 — Round rank + high-score bonus (`bonus_3_rank_points`)

- **Scope:** Per round.
- **Ranking basis:** `basis = base + bonus1 + bonus2` (without bonus3 itself).
- **Guard:** `base_points == 0` → `bonus3 = 0` (no rank, no extra).
- **Rank:** By **distinct** `basis` values descending; tied users share a place.

| Place | Bonus points |
|-------|--------------|
| 1st | 12 |
| 2nd | 8 |
| 3rd | 4 |

- **Extra:** `+4` if `basis >= bonus_3_base_threshold_extra` (default 50).
- `bonus3 = rank_pts + extra`

**Worked example (Round 1):**
- starchenkov_c: basis=56 → place 1 → 12 + extra(+4) = **16**
- shutov: basis=44 → place 2 → 8 (no extra) = **8**
- kuznetsov: basis=36 → place 3 (tied with russkov) → 4 = **4**
- russkov: basis=36 → place 3 (tied) → 4 = **4**

## Computation Order [NEW]

Per round, strictly in sequence:
1. Base points + category counters per (user, match)
2. Bonus 1 (requires all users' predictions for uniqueness check per match)
3. Bonus 2 (requires `correct_outcomes` count per user)
4. Bonus 3 (requires `basis = base + bonus1 + bonus2` for ALL users → ranking)
5. Totals: `total_without_bonus3 = base + bonus1 + bonus2`; `total_with_bonus3 = + bonus3`
6. Dense round rank by `total_with_bonus3`

On VOID or result change: re-run the full round in one atomic transaction.

## Per-Round Rank [NEW]

`round_rank` uses **dense ranking** by `total_with_bonus3` descending:
- Equal totals → same rank
- Next distinct lower total → rank + 1 (not rank + count_of_ties)
- Example: totals 30, 20, 20, 10 → ranks **1, 2, 2, 3**
- No tie-breakers at round level (tie-breakers apply only to final standings)
- Zero-prediction participants are included and rank last

## Tie-Breakers and Final Standings [UPDATED]

`build_standings()` in `src/scoring/standings.py`. Applied in sequence — each next key breaks ties from all previous:

1. `total_points DESC` — sum of `total_with_bonus3` across all rounds
2. `exact_scores_count DESC` — sum of `count_exact_high + count_exact`
3. `total_without_bonuses DESC` — sum of `base_points` only (no bonuses)
4. `correct_diffs_count DESC` — sum of `count_diff`
5. `manual_override DESC` — `contest_participants.exceptional_tiebreak_points` (admin-set per contest; default 0) [UPDATED]

**Before → After:** Criterion 5 was on `users.exceptional_tiebreak_points` (Stage 1.2.1). Stage 1.4 moved it to `contest_participants.exceptional_tiebreak_points` — per-user **per-contest**, updatable by ADMIN at any time (even when contest is locked). `LeaderboardService` loads participants for the contest and passes `manual_overrides` to `build_standings()`.

`tiebreaker_status = "manual_override"` is set on rows whose position was decided by criterion 5.

Leaderboard API responses include `exceptional_tiebreak_points` per row. See [API_GUIDE.md](API_GUIDE.md#endpoints-reference).

> Bonuses affect `total_points` (criterion 1) only; they are excluded from criteria 2–4.

**Verified tie-break examples (rounds 1–9 aggregate):**
- shutov (320 pts) vs kurakov (320 pts) → shutov wins by `exact_scores_count` 7 > 5
- volchenko (232 pts) vs serov (232 pts) → volchenko wins by `exact_scores_count` 5 > 4

## Scoring Persistence [NEW]

`src/services/scoring_persistence.py` bridges the pure engine and the database.

```python
async def calculate_round(session, round_id) -> int   # CLOSED → CALCULATED
async def recalculate_round(session, round_id) -> int # re-run after VOID/result change
```

**Flow:**
1. Load FINISHED matches (non-NULL scores; VOID/SCHEDULED excluded) + all predictions + all participant IDs from DB.
2. Convert to engine types (`MatchResult`, `UserPrediction`).
3. Call `score_round(results, predictions, participant_ids, rules=contest.rules_json)`.
4. Map `UserRoundScore` → `Score` DB row (including `count_*` columns).
5. Upsert all rows in **one atomic transaction**.
6. Transition round `CLOSED → CALCULATED`.

`recalculate_round` deletes existing `Score` rows for the round first, then re-inserts — also atomic.

## Validation Constraints [NEW]

From `rules_json.constraints` (seeded defaults):

| Key | Default | Meaning |
|-----|---------|---------|
| `allow_partial_prediction_save` | `false` | Batch-only: all matches or none |
| `require_all_matches_per_round` | `true` | Every round match must be predicted |
| `score_validation_range` | `[0, 20]` | Enforced at DB CHECK — see [DB_REFERENCE.md](DB_REFERENCE.md) |
| `max_teams_per_round_usage` | `1` | Team appears at most once per round |

Structural limits from `contest_structure`:

| Key | Default | Meaning |
|-----|---------|---------|
| `deadline_rule_hours` | `24` | **Change lockout only** [UPDATED]: on an `ACTIVE` round, supervisor may PATCH deadline only while `now <= current_deadline - N hours`. Does **not** require deadline to be N hours before first kickoff. |
| `max_score_value` | `20` | Max match score (also enforced at API/DB) |

**Before → After (2026-06-27):** Deadline **placement** at create/PATCH is independent of `deadline_rule_hours`: must satisfy `now < deadline < earliest_match`. The 24h value gates **editing** an existing deadline on active rounds (`assert_deadline_change_allowed` in `round_service.py`). See [API_GUIDE.md — round_service](API_GUIDE.md#round_servicepy-updated).

Round-robin validation (when `is_round_robin=true`):

- `matches_per_round == total_teams / 2`
- `total_rounds == (total_teams - 1) * 2`

## Prediction Absence Rule [UPDATED]

**Before → After:** Rules existed in spec only; now enforced by engine and persistence layer.

| Scenario | Correct representation |
|----------|------------------------|
| Player predicts `0:0` | Row with `score1=0, score2=0` |
| Player did not predict | **No row** in `predictions` |
| Player gets points for match | Only if prediction row exists and result matches |

- `score_round()` uses only explicit prediction rows; absence is never treated as `0:0`.
- Verified: serov has 0 prediction rows in round 4 and scores 0 for that round.
- Never insert NULL or 0 as a sentinel for a missing prediction.
