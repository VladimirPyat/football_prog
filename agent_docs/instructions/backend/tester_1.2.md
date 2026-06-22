# Tester Instructions — Stage 1.2: Loader, Deadlines, Batch, Persistence

> Status gate: @Coder `READY_FOR_TEST` for 1.2 in `agent_docs/progress/stage_1.md`.
> Tests/reports English; user verdict Russian. Reference data: `docs/test_data/contracted/`.
> Contracts: `db_schema.md`, `dataflow/scoring_flow.md`, `leaderboard_tiebreakers.md`,
> `bonus_rules.md`.

## 1. Objective
Validate the persistence layer on a REAL database (SQLite test DB): the loader maps
correctly by id, the status machines + 24h rule + batch rules behave, NULL≠0 is
honored, and `calculate_round` persists scores that match the contracted reference.

## 2. Scope — files you may create
```
tests/integration/test_loader_1_2.py
tests/integration/test_deadline_batch_1_2.py
tests/integration/test_calculate_persistence_1_2.py
tests/integration/conftest.py        # isolated test DB + migrations + loader fixtures
```
Use an isolated test database (apply `alembic upgrade head` or `Base.metadata.create_all`
in a fixture). Do NOT modify `src/`. Prefer real contracted data over mocks.

## 3. Loader integrity (`[LD-*]`)
- `[LD-COUNT]` After `load_test_data.py --reset`: 16 teams, 10 users, rounds 1–10,
  72 finished matches (9×8) + 8 scheduled (round 10). Verify **by id-based queries**.
- `[LD-NULL]` Round 10 matches have `score1 IS NULL AND score2 IS NULL`, status SCHEDULED.
- `[LD-ABSENCE]` `serov` has 0 prediction rows in round 4; total prediction rows per
  (user, finished round) is a multiple of `matches_per_round`, and equals 8 except
  serov/round4 = 0. No 0:0 placeholder rows exist for missing predictions.
- `[LD-MAP]` `short_name`→team_id and `login`→user_id are unique and complete; a spot
  match (e.g. round1 Дин–Балт) resolves to the correct team ids and result 1:1.
- `[LD-IDEMPOTENT]` Running the loader twice with `--reset` yields identical row counts.

## 4. Deadlines, statuses, batch (`[DL-*]`, `[ST-*]`, `[BT-*]`)
- `[DL-24H-FAIL]` Changing a round deadline to ≥ (first_match − 24h) → domain error
  (will be 400 at API level). `[DL-24H-OK]` a deadline 3 days before → accepted.
- `[ST-ILLEGAL]` Illegal status transition (e.g. `PUBLISHED → ACTIVE`) rejected.
- `[ST-LOCK]` Activating the first round sets `contest_settings.is_locked = TRUE`.
- `[BT-PARTIAL]` Submitting 7/8 predictions → rejected (400-class); DB unchanged.
- `[BT-FULL]` 8/8 saved atomically; re-submitting duplicate `(user,round,match)` → IntegrityError.
- `[BT-ZERO]` `0:0` is accepted and stored as a real prediction (not absence).
- `[BT-DEADLINE]` Submitting to a round whose deadline passed / not ACTIVE → rejected (403-class).

## 5. Persistence correctness vs reference (`[CALC-*]`) — the key cross-check
- `[CALC-ROUND]` For each finished round 1–9, call `calculate_round`, then read the
  persisted `Score` rows and compare to `docs/test_data/contracted/expected_scores.csv`
  (join by user_id) with EXACT equality:
  `total_with_bonus3 == expected_total`, `bonus1 + bonus2 == expected_bonus1`
  (and `expected_bonus2 == 0`), `bonus3 == expected_bonus3`,
  `points_exact+points_diff+points_outcome == expected_base_pts`. Expect 90/90.
- `[CALC-COUNTS]` Aggregate persisted `count_*` across rounds per user and compare to
  `leaderboard.csv` (`exact_high_count/exact_count/diff_count/outcome_count`) — 10/10.
- `[CALC-COUNTS-ROW]` Compare persisted per-round `count_*` (from the `scores` rows) to the
  per-round `count_*` columns of `expected_scores.csv` (join by user_id), exact equality, 90/90.
  NOTE: fixture `count_*` corrected & re-verified 2026-06-11 (90/90, see BLOCKED.md) — this
  assertion is ACTIVE. Keep the safety-gate: assert every fixture row satisfies
  `16·count_exact_high + 12·count_exact + 8·count_diff + 4·count_outcome == expected_base_pts`;
  if the gate ever fails (fixture regressed), report `[CALC-COUNTS-ROW] BLOCKED: data
  inconsistent` and do NOT skip silently. Never weaken the assertion once the gate passes.
- `[CALC-ATOMIC]` `calculate_round` is transactional: simulate a failure mid-calc
  (e.g. patch to raise) and assert NO partial `Score` rows are committed for the round.
- `[CALC-VOID]` After calculating a round, VOID one match → `recalculate_round` runs in
  one transaction and the affected users' scores change consistently (base of that match → 0,
  bonuses for the round recomputed).

## 6. Execution & report
```
uv run alembic upgrade head
uv run pytest tests/integration/ -v
```
- **PASS** → `agent_docs/reports/test_1.2.md` (Russian) with the [TEST-ID] table and
  the 90/90 + 10/10 confirmation; append `STATUS: TEST_PASS` to `progress/stage_1.md`.
- **FAIL** → per `[TEST-ID]`: expected vs actual (ids + numbers + DB state) and the fix
  required from @Coder; append `STATUS: TEST_FAIL`. Never edit `src/`.

## 7. Verdict to user (Russian)
Этап 1.2, PASS/FAIL, ключевые проверки (loader by id, 24h, batch/NULL, calculate 90/90,
counts 10/10, атомарность/VOID), дефекты с `[TEST-ID]`, следующий шаг.
