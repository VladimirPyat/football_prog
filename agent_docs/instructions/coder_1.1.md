# Coder Instructions — Stage 1.1: Scoring Engine (pure math)

> Status gate: proceed only when `agent_docs/progress/stage_1.md` shows
> `INSTRUCTIONS_READY`. Language: code/comments in English; user report in Russian.
> Source contracts (re-read before coding):
> - `agent_docs/dataflow/scoring_flow.md` (base points, NULL semantics)
> - `agent_docs/contracts/bonus_rules.md` (bonus 1/2/3, VERIFIED 89/89)
> - `agent_docs/contracts/leaderboard_tiebreakers.md` (ranking + tie-breakers)

## 1. Objective
Implement a **pure, deterministic scoring engine** — NO database, NO FastAPI, NO
I/O. Input = plain Python data structures; output = dataclasses. All numeric
values, thresholds and multipliers come from a `rules` dict (the shape of
`contest_settings.rules_json` / `contest_defaults.json`). **No magic numbers.**

This is the module we verified at length; correctness is paramount.

## 2. Scope — files you may create/modify
```
src/scoring/__init__.py          # public exports
src/scoring/types.py             # input/output dataclasses + enums
src/scoring/rules.py             # typed accessor over rules_json (values only)
src/scoring/engine.py            # base points, bonuses, per-round rank
src/scoring/standings.py         # cross-round aggregation + tie-break ordering
tests/unit/test_scoring_engine.py   # your unit tests (see §6)
```
Do NOT touch `src/database/`, `src/api/`, migrations, or `docs/`. Do NOT add
dependencies (stdlib only: `dataclasses`, `enum`, `math`).

## 3. Input / output data model (`src/scoring/types.py`)
```python
class Category(StrEnum):
    EXACT_HIGH = "exact_high"; EXACT = "exact"; DIFF = "diff"
    OUTCOME = "outcome"; MISS = "miss"

@dataclass(frozen=True)
class MatchResult:
    match_id: int
    score1: int | None      # None/absent => not finished/void => excluded
    score2: int | None
    is_scorable: bool        # True only for FINISHED with both scores not None

@dataclass(frozen=True)
class UserPrediction:
    user_id: int
    match_id: int
    score1: int              # 0..max; 0 is a REAL value
    score2: int

@dataclass(frozen=True)
class MatchScore:
    match_id: int
    category: Category
    base_points: int
    bonus1_points: int       # unique-correct-outcome bonus for THIS match

@dataclass(frozen=True)
class UserRoundScore:
    user_id: int
    base_points: int
    count_exact_high: int
    count_exact: int
    count_diff: int
    count_outcome: int
    correct_outcomes: int    # matches with base_points >= 4
    bonus1: int
    bonus2: int
    bonus3: int
    total_without_bonus3: int  # base + bonus1 + bonus2
    total_with_bonus3: int     # total_without_bonus3 + bonus3
    round_rank: int            # DENSE rank by total_with_bonus3 (ties share)
    per_match: tuple[MatchScore, ...]
```
Engine entrypoint:
```python
def score_round(
    results: list[MatchResult],
    predictions: list[UserPrediction],
    participant_ids: list[int],   # ALL users to rank (incl. zero-prediction ones)
    rules: dict,
) -> dict[int, UserRoundScore]: ...
```

## 4. Base points (per match) — see scoring_flow.md §1
`sign(x) = 1 if x>0 else -1 if x<0 else 0`. For a scorable match:
1. `EXACT_HIGH` (`base_points.exact_high_score`): p1==r1 and p2==r2 and (`abs(r1-r2)>=3` or `r1+r2>3`)
2. `EXACT` (`base_points.exact_score`): p1==r1 and p2==r2 and not high
3. `DIFF` (`base_points.diff_plus_outcome`): sign(p1-p2)==sign(r1-r2) and abs(p1-p2)==abs(r1-r2)
4. `OUTCOME` (`base_points.outcome_only`): sign(p1-p2)==sign(r1-r2)
5. `MISS` (0)
**NULL/absence rule (critical):** a user with no prediction row for a match scores
nothing for it. NEVER treat absence as `0:0`. Compare predictions explicitly; do
not use `dict.get(match_id, 0)`. Non-scorable matches (not finished / VOID /
score None) are skipped for everyone.

Counters: `count_exact_high/exact/diff/outcome` = number of matches in each
EXCLUSIVE category. `correct_outcomes` = count of matches with `base_points >= 4`.

## 5. Bonuses — see bonus_rules.md (this is the verified spec)
**Bonus 1** (per match, summed): for each scorable match, among ALL participants
who submitted a prediction, group by predicted outcome `sign(p1-p2)`. If exactly
ONE participant predicted the outcome that actually occurred, that participant
gets `bonus1_points = int(base_points_for_match * bonus_1_unique_multiplier_pct / 100)`.
Uniqueness is on the OUTCOME (1/X/2), not the exact score. Use integer truncation
(`int(...)`, i.e. floor for non-negative).

**Bonus 2** (per round): `n = correct_outcomes`. Walk `bonus_2_thresholds` and take
the highest `points` whose `min_correct_outcomes <= n` (0 if none).

**Bonus 3** (per round): `basis(u) = base + bonus1 + bonus2`.
- If `base_points(u) == 0` → `bonus3 = 0` (no rank, no extra).
- Rank by DISTINCT `basis` value descending: place 1→`bonus_3_rank_points["1st"]`,
  2→`["2nd"]`, 3→`["3rd"]`, else 0. Players sharing a `basis` value share the place
  and ALL get its points.
- Plus `bonus_3_extra_points` if `basis >= bonus_3_base_threshold_extra`.
- `bonus3 = rank_points + extra`.

`total_without_bonus3 = base + bonus1 + bonus2`; `total_with_bonus3 = + bonus3`.

## 6. Per-round rank (`round_rank`)
DENSE ranking by `total_with_bonus3` descending: equal totals share the same rank,
the next distinct total gets the immediately following integer (1,2,3,3,4,...).
**No tie-breakers at round level** (tie-breakers apply only to final standings, §7).
Include zero-prediction participants (they rank last with total 0).

## 7. Final standings (`src/scoring/standings.py`)
```python
def build_standings(
    per_user_rounds: dict[int, list[UserRoundScore]],
    manual_overrides: dict[int, int] | None,  # user_id -> priority (higher=better)
) -> list[StandingRow]: ...
```
Aggregate per user across rounds: `total_points = Σ total_with_bonus3`;
`exact_scores_count = Σ(count_exact_high + count_exact)`;
`total_without_bonuses = Σ base_points`; `correct_diffs_count = Σ count_diff`;
also expose aggregated counts (`exact_high_count`, `exact_count`, `diff_count`,
`outcome_count`) and `total_predictions`.
Order by, strictly in sequence (all DESC):
`total_points` → `exact_scores_count` → `total_without_bonuses` →
`correct_diffs_count` → `manual_override priority (default 0)`.
Assign 1-based ranks; set `tiebreaker_status = "manual_override"` for any user whose
final order depended on the manual key. Read tie-break order from
`rules["tiebreakers"]` (don't hardcode the chain if avoidable).

## 8. MANDATORY unit tests (`tests/unit/test_scoring_engine.py`)
Edge-heavy (≈80% edge / 20% happy). At minimum:
- **Base categories**: one test each for exact_high (e.g. 3:0, 2:2 with sum>3),
  exact (1:0), diff (2:1 vs 3:2), outcome (2:0 vs 3:0), miss. Assert category + points.
- **Boundaries**: score `0:0` is a valid prediction and can win points (e.g. exact
  0:0 when result 0:0 → exact, NOT high). Verify `max_score_value` not hardcoded.
- **NULL/absence**: a user missing a prediction for a match earns 0 for it and the
  match is excluded from his `correct_outcomes`; absence must NOT be read as 0:0
  (construct a case where 0:0 would falsely score and assert it does NOT).
- **Bonus 1**: unique correct outcome → ×2 of base (use 200% from rules); shared
  outcome → 0; unique but WRONG outcome → 0; multiple unique matches sum.
- **Bonus 2**: thresholds 5→0, 6→8, 7→12, 8→16.
- **Bonus 3**: place 1/2/3 points; tie on basis → all tied get the place points
  (replicate Round-1 kuznetsov/russkov 36/36 → both +4 pattern is in 1.1 tester,
  here use a synthetic tie); `basis>=50` adds extra; `base==0` → bonus3 0.
- **Round rank**: dense ranking with a 3-way tie.
- **Standings tie-break**: two users equal on total but different exact_scores_count
  → higher exact ranks first; full chain down to manual_override.
- Run: `uv run pytest tests/unit/test_scoring_engine.py -v` → all green.

## 9. Acceptance criteria
- Engine is pure (no imports from `src/database`, `fastapi`, no file/network I/O).
- All values sourced from `rules` dict; nothing hardcoded.
- Unit tests pass. (Row-by-row CSV cross-check is @Tester's job in `tester_1.1.md`.)

## 10. Handoff
Append to `agent_docs/progress/stage_1.md`:
```
## YYYY-MM-DD — Coder (1.1)
- STATUS: READY_FOR_TEST
- Files: <paths>
- Verified: uv run pytest tests/unit/test_scoring_engine.py -v -> N passed
```
Then report to the user in Russian and point to `tester_1.1.md`.
