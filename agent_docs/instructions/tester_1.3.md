# Tester Instructions — Stage 1.3: API Integration & Triggers

> Status gate: @Coder `READY_FOR_TEST` for 1.3. Tests/reports English; user verdict
> Russian. Contracts: `api_v1.yaml`, `leaderboard_tiebreakers.md`, `bonus_rules.md`.
> Reference data: `docs/test_data/contracted/`.

## 1. Objective
End-to-end HTTP validation: auth/RBAC, batch/deadline/privacy over the API, the
`calculate` trigger, and that public leaderboard/results served via HTTP reproduce
the contracted reference. Use `httpx.AsyncClient` against the ASGI app.

## 2. Scope — files you may create
```
tests/api/conftest.py                # ASGI client, isolated DB, loaded contracted data, auth helpers
tests/api/test_auth_rbac_1_3.py
tests/api/test_predictions_flow_1_3.py
tests/api/test_calculate_leaderboard_1_3.py
# Manual two-phase verification (see §6) — standalone runnable scripts, NOT pytest:
tests/manual/verify_via_api.py       # SCRIPT 1: drives ONLY HTTP endpoints, NO knowledge of reference CSVs
tests/manual/compare_db_vs_reference.py  # SCRIPT 2: READ-ONLY compare of DB rows vs contracted CSVs
tests/manual/README.md               # how to run both scripts by hand + DBeaver checkpoint + canary test
```
Isolated test DB seeded via the 1.2 loader. Create test users with known passwords
(a USER, a SUPERVISOR, an ADMIN) — hash via the app's security module; do NOT modify `src/`.

## 3. Auth & RBAC (`[AUTH-*]`, `[RBAC-*]`)
- `[AUTH-LOGIN]` valid creds → 200 + token; bad creds → 401.
- `[AUTH-TEMP]` user with `is_temp_password=true` is restricted to change-password/me
  (other protected route → 403); after change-password the flag clears and access opens.
- `[RBAC-USER]` USER cannot call a SUPERVISOR endpoint (e.g. `POST /admin/rounds`) → 403.
- `[RBAC-PUB]` public GET leaderboard/results without token → 200.
- `[RBAC-ADMIN]` `POST /admin/recalculate` allowed only for ADMIN.

## 4. Predictions over HTTP (`[API-PRED-*]`)
- `[API-PRED-PARTIAL]` `POST /rounds/{id}/predictions` with 7/8 → 400.
- `[API-PRED-FULL]` 8/8 to an ACTIVE round before deadline → 200, `saved_count=8`.
- `[API-PRED-RANGE]` score `21` → 422; `0` accepted.
- `[API-PRED-DEADLINE]` POST after deadline / non-ACTIVE round → 403.
- `[API-PRED-PRIVACY]` `GET /rounds/{id}/predictions` before deadline → requester sees own
  scores, others only `submitted` flag; after deadline → all scores visible.

## 5. Calculate trigger + leaderboard correctness (`[API-CALC-*]`, `[API-LB-*]`)
This is the integration-level repeat of the math, now THROUGH the API:
- `[API-CALC]` `POST /admin/rounds/{id}/calculate` (rounds 1–9) → 200, status `CALCULATED`,
  `users_scored` correct.
- `[API-RESULTS]` `GET /rounds/{id}/results` per-user per-match points + bonuses match
  `expected_scores.csv` (join by id): `total == expected_total`, `bonus1+bonus2 == expected_bonus1`,
  `bonus3 == expected_bonus3`. Expect 90/90 across rounds 1–9.
- `[API-LB-GLOBAL]` `GET /leaderboard` after calculating all rounds reproduces
  `leaderboard.csv` EXACTLY: `rank` order, `total_points`, `total_without_bonuses`,
  `total_bonuses`, and the count columns (`exact_high_count/exact_count/diff_count/outcome_count`),
  `total_predictions` (serov=64). Confirm tie-break pairs (shutov>kurakov, volchenko>serov).
- `[API-VOID]` `PATCH /admin/matches/{id}/status` VOID after calculation → recalculation
  triggered; `GET /leaderboard` reflects the change atomically (no half-updated state).
- `[API-CACHE]` public GET leaderboard/results carry `Cache-Control` + `ETag`; the predictions
  submit endpoint does not.
- `[API-OVERRIDE]` `POST /admin/leaderboard/{round_id}/override` persists manual priorities and
  changes ordering only when all 4 primary keys tie (construct/inspect a synthetic tie).

## 6. Manual two-phase verification (mandatory for Stage 1 sign-off)
A human-in-the-loop flow on top of the automated pytest. Goal: prove the system writes
CORRECT data to a REAL database, with a manual DBeaver checkpoint, and an independent
read-only reference comparison. The two scripts MUST be separate processes.

### SCRIPT 1 — `tests/manual/verify_via_api.py` ("verify the CODE")
- Talks to the running app **exclusively through HTTP endpoints** that @Coder built
  (login, submit predictions / load, `POST /admin/rounds/{id}/calculate`, `GET /results`,
  `GET /leaderboard`). It uses the SAME database the app writes to.
- It MUST NOT import, open, or reference ANY file under `docs/test_data/` — it has zero
  knowledge that canonical CSVs exist. Hard rule: no `expected_*.csv`, no `leaderboard.csv`.
- It only checks **internal self-consistency** of what the code produced, e.g.:
  - calculate rounds 1–9 → every round ends `CALCULATED`, `users_scored > 0`;
  - for every result row: `total == base + bonus1 + bonus2 + bonus3`;
  - `16·count_exact_high + 12·count_exact + 8·count_diff + 4·count_outcome == base`;
  - leaderboard `rank` is monotonic and consistent with the documented tiebreak ordering;
  - `total_without_bonuses + total_bonuses == total_points` per user.
- Output: a short PASS/FAIL on code self-consistency. It does NOT decide correctness vs
  the contest history — that is Script 2's job.

### MANUAL STOP — user inspects the DB in DBeaver
After Script 1 passes, **HALT and ask the user** to open DBeaver and visually confirm the
`scores` / leaderboard rows that were actually persisted. Do not run Script 2 until the
user explicitly confirms. State this stop clearly in the report.

### SCRIPT 2 — `tests/manual/compare_db_vs_reference.py` ("compare DB vs reference")
- **READ-ONLY**: opens a DB connection and the contracted CSVs, compares, and prints a
  discrepancy report. It MUST NOT write to the DB, MUST NOT modify `src/`, MUST NOT call
  any mutating endpoint, MUST NOT re-run calculate or re-load data.
- Joins strictly by id (`login → user_id`, `short_name → team_id`); names only for
  human-readable diff lines.
- Compares persisted DB rows against `expected_scores.csv` (per-round: base, bonus1(=b1+b2),
  bonus3, total, rank, `count_*`) and `leaderboard.csv` (aggregates, counts, tiebreak order).
- Output: a discrepancy report — for each mismatch print `(user_id, round, column, db_value,
  reference_value)`. Zero discrepancies ⇒ DB reproduces the contest history.

### Manual run (document verbatim in `tests/manual/README.md`)
```
# 0. start the app against an isolated DB and load contracted data via the 1.2 loader
# 1. self-consistency of the code (no reference knowledge):
uv run python tests/manual/verify_via_api.py --base-url http://localhost:8000
# 2. >>> STOP: inspect the scores/leaderboard tables in DBeaver, then confirm <<<
# 3. independent read-only comparison DB vs canonical CSVs:
uv run python tests/manual/compare_db_vs_reference.py --reference docs/test_data/contracted/
```

### CANARY (proves Script 2 truly compares two sources)
Document this as an explicit, repeatable check: edit a value in a **reference** file
(e.g. change one prediction in `predictions.csv`, or one number in `expected_scores.csv`)
WITHOUT recomputing/reloading the DB, then re-run **only Script 2**. It MUST now report a
discrepancy. If Script 2 still passes after a deliberate reference edit, the comparison is
fake → treat as a Stage-1 blocker. (Revert the reference edit afterwards.)

## 7. Automated execution & report
```
uv run pytest tests/api/ -v
# optionally full suite: uv run pytest tests/ -v
```
- **PASS** → `agent_docs/reports/test_1.3.md` (Russian) with [TEST-ID] table; confirm the
  roadmap success criteria for Stage 1 ("API passes contract tests, calc matches historical
  data, transactions atomic"); append `STATUS: TEST_PASS` to `progress/stage_1.md`.
- **FAIL** → per `[TEST-ID]` expected vs actual (HTTP status, body, ids/numbers) + fix for
  @Coder; append `STATUS: TEST_FAIL`. Never edit `src/`.

## 8. Verdict to user (Russian)
Этап 1.3, PASS/FAIL, покрытие (auth/RBAC, batch/privacy, calculate→90/90, leaderboard→10/10,
VOID-атомарность, кэш), результат двух-скриптовой ручной проверки (script1 self-consistency,
ручная остановка на DBeaver, script2 сверка БД↔эталон + canary), дефекты с `[TEST-ID]`,
и общий статус готовности Этапа 1.
