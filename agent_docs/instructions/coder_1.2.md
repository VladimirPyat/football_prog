# Coder Instructions — Stage 1.2: Setup, Deadlines & Data Loader

> Status gate: `agent_docs/progress/stage_1.md` = `INSTRUCTIONS_READY`, and 1.1 is
> `TEST_PASS` (this stage depends on the engine). Code/comments English; user report Russian.
> Contracts: `agent_docs/contracts/db_schema.md`, `dataflow/scoring_flow.md`,
> `contracts/leaderboard_tiebreakers.md`. Source data: `docs/test_data/contracted/`
> (read-only), config `docs/test_data/config/contest_defaults.json` (read-only).

## 1. Objective
Build the data/persistence layer around the pure engine (1.1): a CSV loader (by id,
config-driven), Round/Match status machines with the 24h rule, batch-only prediction
saving with strict NULL≠0 semantics, and the atomic round scoring/VOID recalculation
service. **No FastAPI here** (that is 1.3). No magic numbers — read limits from
`contest_settings`.

## 2. Scope — files you may create/modify
```
config/test_data_loader.json         # NEW: loader format/mapping config (see §3)
src/scripts/load_test_data.py        # NEW: CSV -> DB loader (id-based)
src/services/__init__.py
src/services/round_service.py        # status machine + 24h rule
src/services/match_service.py        # result entry, status changes, VOID
src/services/prediction_service.py   # batch-only, NULL!=0, deadline, privacy filter
src/services/scoring_persistence.py  # DB round data -> engine.score_round -> upsert scores (atomic)
src/database/models.py               # EXTEND scores with count columns (see §4)
alembic/versions/<new>_scores_counts.py   # migration for the new columns
tests/unit/test_services_1_2.py      # your unit tests (§8)
```
Reuse `src/scoring/` (1.1), `src/database/{models,engine,base}.py`,
`config/settings.py`. Do NOT add packages without approval (loader uses stdlib `csv`).

## 3. Loader config (`config/test_data_loader.json`) — keep mapping OUT of code
The user requires mapping/format to live in config, and all verification to be by
**id** (names only for display). Define at least:
```json
{
  "data_dir": "docs/test_data/contracted",
  "files": {
    "teams":       {"name": "teams.csv",       "delimiter": ","},
    "users":       {"name": "users.csv",        "delimiter": ";"},
    "matches":     {"name": "matches.csv",      "delimiter": ";"},
    "predictions": {"name": "predictions.csv",  "delimiter": ";"}
  },
  "user_name_split": {"strategy": "last_name_only"},   // last_name = full_name; first_name = ""
  "datetime": {"format": "%d.%m.%Y|%H:%M", "timezone": "UTC"},
  "default_user_role": "USER"
}
```
Loader behavior:
- Build in-memory maps `short_name -> team_id`, `login -> user_id`,
  `(round_number, home_short, away_short) -> match_id`. Persist by id; never rely on names as keys.
- `teams.csv` has NO id and uses comma; create `Team(name=full_name, short_name=short_name)`.
- `users.csv`: `full_name` → split per config (`last_name_only`: `last_name=full_name`,
  `first_name=""`); `is_temp_password` from CSV; role from config.
- `matches.csv`: parse `scheduled_at` with the configured format/timezone into
  `DateTime(timezone=True)`. Round 10 rows have empty `actual_score1/2` + `status=SCHEDULED`
  → store `score1=score2=NULL`. Finished rows store real integer scores (incl. 0).
- `rounds`: create one `Round` per `round_number`; `matches_count` = number of matches;
  `deadline` = (earliest match datetime in the round) − `deadline_rule_hours` (from
  `contest_settings`); set status `CLOSED` for finished rounds 1–9, `ACTIVE` for round 10
  (so deadline/batch tests have an open round). Document this choice in a comment.
- `predictions.csv`: insert a `Prediction` row ONLY where a line exists.
  **Absence = no row** (serov round 4 must have zero rows). NEVER write a 0:0 placeholder.
- Idempotency: support a `--reset` flag (truncate loaded tables) so reloads are clean.
  On success print `✅ Data loaded successfully` and exit 0; on any row failing
  validation, fail loudly with the offending row (no silent skips).

## 4. Schema extension — store counts in `scores` (REQUIRED, flagged deviation)
The documented leaderboard display (`docs/03_user_scenarios.md`) and tie-breakers
(`leaderboard_tiebreakers.md`) need per-category **frequencies**, which the current
`scores` table does not hold. Add four columns:
```
count_exact_high : INTEGER NOT NULL DEFAULT 0
count_exact      : INTEGER NOT NULL DEFAULT 0
count_diff       : INTEGER NOT NULL DEFAULT 0
count_outcome    : INTEGER NOT NULL DEFAULT 0
```
- Update `src/database/models.py` `Score` and create an Alembic migration
  (`uv run alembic revision --autogenerate` then review; ensure upgrade+downgrade clean).
- This is an additive, backward-compatible change. Note it in your handoff so @Planner
  syncs `contracts/db_schema.md`.

## 5. Scoring persistence (`src/services/scoring_persistence.py`)
```python
async def calculate_round(session, round_id) -> int   # returns users_scored
async def recalculate_round(session, round_id) -> int  # used after result/VOID change
```
- Load the round's scorable matches (`FINISHED`, non-NULL scores; VOID/SCHEDULED excluded),
  all predictions for the round, and the full participant list.
- Convert to engine types and call `src/scoring/engine.score_round(...)` with
  `rules = contest_settings.rules_json`.
- Upsert one `Score` row per participant: map `UserRoundScore` →
  `points_exact = exact_high+exact base pts`, `points_diff`, `points_outcome`,
  `bonus1/2/3`, `total_without_bonus3`, `total_with_bonus3`, `correct_outcomes`,
  and the four `count_*` columns.
- **Atomic**: entire round upsert in ONE transaction (`async with session.begin()`).
  On recalculation, overwrite existing rows for the round.
- Status transition: `calculate_round` moves round `CLOSED → CALCULATED`. Reject if
  round not in a calculable status (raise a domain error; do not silently no-op).

## 6. Round / Match services
`round_service.py`:
- Status machine `DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED`; reject illegal
  transitions with explicit domain errors.
- **24h rule**: `deadline` must be `< earliest_match_datetime − deadline_rule_hours`
  (hours from `contest_settings`). Reject deadline changes when
  `now > earliest_match_datetime − deadline_rule_hours`. All datetimes timezone-aware.
- Activating the first round sets `contest_settings.is_locked = TRUE`.

`match_service.py`:
- `set_result(match_id, score1, score2)`: validate `0..max_score_value` (from settings),
  set `FINISHED`. `change_status(match_id, VOID|POSTPONED|CANCELED)`. On `VOID` of a match
  in a CALCULATED round → call `recalculate_round` (atomic).

`prediction_service.py`:
- `submit_batch(user_id, round_id, items)`: require EXACTLY `matches_per_round` items
  covering all of the round's matches → else raise (maps to 400 in 1.3). Reject if
  `now >= deadline` or round not `ACTIVE` (maps to 403). Save all rows in ONE transaction
  (all-or-nothing). Each score validated `0..max_score_value`; **0 is valid**.
- `visible_predictions(round_id, viewer)`: before deadline → only viewer's own scores +
  "submitted" flags for others (ADMIN only sees all); after deadline → everyone's scores.

## 7. NULL / absence invariants (critical, enforce everywhere)
- A missing prediction is the ABSENCE of a row. Never insert NULL/0 as a sentinel.
- Never read a missing prediction as `0:0`. Scoring already excludes absent rows (1.1).

## 8. MANDATORY unit tests (`tests/unit/test_services_1_2.py`)
≈80% edge. At minimum:
- **Loader**: after load, counts by id — 16 teams, 10 users, 9×8 finished + 8 scheduled
  matches; serov has 0 predictions in round 4; round 10 matches have NULL scores;
  `short_name`/`login` maps are unique. Reload with `--reset` is idempotent.
- **Deadline/24h**: setting deadline ≥ (first_match − 24h) is rejected; valid deadline accepted.
- **Batch**: 7/8 items → reject; 8/8 → saved atomically; `0:0` accepted as real; submit
  after deadline → rejected; partial DB state never persists on failure.
- **NULL**: absence stays absence; no 0:0 placeholder is ever written.
- **Status machine**: illegal transition rejected; first activation locks settings.
- **calculate_round** on a loaded finished round persists `Score` rows whose totals equal
  the engine output (spot-check ≥1 round); VOID a match → `recalculate_round` changes scores atomically.
- Run: `uv run alembic upgrade head` (exit 0) then
  `uv run pytest tests/unit/test_services_1_2.py -v` → green.

## 9. Acceptance criteria
- `uv run python src/scripts/load_test_data.py --reset` → `✅ Data loaded successfully`, exit 0.
- Migration upgrades/downgrades cleanly; `scores` has the four count columns.
- All limits/format read from config/`contest_settings`; nothing hardcoded.
- Unit tests pass. (Row-by-row reference cross-check on the loaded DB is @Tester, 1.2.)

## 10. Handoff
Append to `agent_docs/progress/stage_1.md`:
```
## YYYY-MM-DD — Coder (1.2)
- STATUS: READY_FOR_TEST
- Files: <paths> (note: scores schema extended with count_* + migration)
- Verified: alembic upgrade head (0); loader exit 0; pytest tests/unit/test_services_1_2.py -> N passed
```
Report to user in Russian (mention the `scores` count_* extension) and point to `tester_1.2.md`.
