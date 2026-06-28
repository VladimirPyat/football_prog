# Tester Instructions — Stage 1.14: Dev Fixture Data Fix

> **Status gate:** @Coder `READY_FOR_TEST` for 1.14 data fix.
> **Coder spec:** `agent_docs/instructions/coder_1.14_data_fix.md`
> **Prerequisite:** Stage 1.2 loader + `dev_setup.py`; `bootstrap_users.py` after `load_test_data --reset`.
> **Report:** `agent_docs/reports/test_1.14_data_fix.md` (NEW — Russian summary + PASS/FAIL table)
> **Strategy:** SQL verification + contracted score compare + pytest regression + API smoke + E2E profile flag. **Do not modify** `src/` unless new blocker.

---

## 1. Objective

Verify `finalize_dev_fixture.py` and extended `dev_setup.py` flags produce the **manual dev profile** for contest `id=1` without breaking pytest isolation.

| ID | Area | Summary |
|----|------|---------|
| **D1** | Rounds 1–9 | `PUBLISHED` + **10** `scores` rows each (90 total) |
| **D2** | Round 10 | `CALCULATED` + **10** `scores` rows; **not** `PUBLISHED` |
| **D3** | Round 11 | `CLOSED` + **0** `scores`; deadline passed (ref. **2026-06-27**) |
| **D4** | Contract | Rounds 1–9 `scores` values ≡ `expected_scores.csv` (90/90) |
| **D5** | Regression | `test_calculate_persistence_1_2.py` still passes on **fresh** DB (no finalize in pytest path) |
| **D6** | E2E profile | `--ensure-running-only --e2e` restores round 10 **ACTIVE** for prediction tests |
| **D7** | Docs | `manuals/DEV_SETUP.md` matches actual fixture table |

**Non-goals:**

- Supervisor UI per-status panels → `tester_2.3.1_fix_rounds.md`
- Public leaderboard `PUBLISHED`-only gate → `tester_2.3.1_fix_rounds.md`
- Changing round status enum values in DB/API

---

## 2. Test environment — three profiles

Distinguish profiles; **never** run finalize on pytest isolated DB unless the test explicitly boots dev_setup.

### 2.1 Manual dev profile (primary for this stage)

Full bootstrap — what human QA uses after Coder ships:

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
# or full: uv run python src/scripts/dev_setup.py --run  (if Coder wires finalize into default --run)
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

**Expected contest `id=1` state after finalize (manual profile):**

| Round | `status` | `scores` rows |
|-------|----------|---------------|
| 1–9 | `PUBLISHED` | 10 each |
| 10 | `CALCULATED` | 10 |
| 11 | `CLOSED` | 0 |

### 2.2 Pytest isolated DB (regression — must NOT break)

Pytest uses fresh DB via fixtures (`load_test_data --reset` **without** `finalize_dev_fixture`). Integration tests call `calculate_round` themselves from `CLOSED` rounds 1–9.

```bash
uv run pytest tests/integration/test_calculate_persistence_1_2.py -v
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
```

**Pass:** exit 0; rounds 1–9 start as `CLOSED` with **0** scores in test DB.

### 2.3 E2E profile (`--e2e`)

Prediction / ACTIVE-round E2E must not see round 10 as `CALCULATED`:

```bash
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
```

**Expected:** round 10 `ACTIVE`, future deadline, **0** scores on round 10; rounds 1–9 may stay `CLOSED` (finalize skipped) per Coder §6.2.

Verify via SQL or `GET /api/v1/contests/1/rounds` — document actual behaviour in report.

### 2.4 Repair-only path (optional)

If DB already bootstrapped but fixture wrong:

```bash
uv run python src/scripts/dev_setup.py --finalize-fixture-only
```

Idempotent re-run must not duplicate `scores` rows.

---

## 3. Scope — files you may create/modify

```
tests/scripts/test_finalize_dev_fixture_1_14.py   # NEW — recommended (Coder may add; extend if gaps)
tests/integration/test_dev_fixture_1_14.py        # ALT location if integration-style
agent_docs/reports/test_1.14_data_fix.md          # NEW — verdict report
```

Reuse helpers from `tests/api/reference_compare.py` (`load_expected_scores`, `compare_scores_to_expected`, `build_score_lookup`).

**Do NOT modify:** `docs/`, `src/` (backend bugs → `agent_docs/reports/BLOCKED.md`).

---

## 4. SQL verification — mandatory

Run against SQLite (or project DB) after **manual profile** bootstrap (§2.1).

### 4.1 `[FIXTURE-STATUS-COUNTS]` Round status + score row counts

```sql
SELECT r.number, r.status, r.deadline,
       (SELECT COUNT(*) FROM scores s WHERE s.round_id = r.id) AS score_rows,
       (SELECT COUNT(*) FROM matches m WHERE m.round_id = r.id) AS match_rows
FROM rounds r
WHERE r.contest_id = 1
ORDER BY r.number;
```

**Pass criteria:**

| `number` | `status` | `score_rows` | `match_rows` |
|----------|----------|--------------|--------------|
| 1–9 | `PUBLISHED` | 10 | 10 |
| 10 | `CALCULATED` | 10 | 8 (per CSV) |
| 11 | `CLOSED` | 0 | 8 |

Tag per-round failures: `[FIXTURE-1-9-PUBLISHED]`, `[FIXTURE-10-CALCULATED]`, `[FIXTURE-11-CLOSED]`.

### 4.2 `[FIXTURE-11-DEADLINE]` Round 11 deadline passed

Assert `rounds.number = 11` has `deadline < now()` (reference date **2026-06-27** UTC in Coder spec). Matches on `date_time` for round 11 should be afternoon **2026-06-27**, `status = SCHEDULED`, `score1/score2 IS NULL`.

### 4.3 `[FIXTURE-10-NOT-PUBLISHED]`

```sql
SELECT status FROM rounds WHERE contest_id = 1 AND number = 10;
```

→ `CALCULATED`, **not** `PUBLISHED`.

### 4.4 `[FIXTURE-TOTAL-SCORES]`

```sql
SELECT COUNT(*) FROM scores s
JOIN rounds r ON s.round_id = r.id
WHERE r.contest_id = 1;
```

→ **100** (90 from rounds 1–9 + 10 from round 10).

---

## 5. Contract verification — `expected_scores.csv`

### 5.1 `[FIXTURE-SCORES-1-9]` Values match contracted reference (90/90)

For rounds **1–9 only**, compare DB `scores` to `docs/test_data/contracted/expected_scores.csv` (delimiter `;`).

**Option A — pytest (recommended):**

```python
# tests/scripts/test_finalize_dev_fixture_1_14.py
# After dev_setup manual profile in fixture:
# matched, mismatches = compare_scores_to_expected(...)
# assert matched == 90 and not mismatches
```

**Option B — one-off script in report:**

Use `tests/api/reference_compare.py` helpers; list first 5 mismatches on FAIL.

**Fields to compare** (per `reference_compare.py`): `points_exact`, `points_diff`, `points_outcome`, `bonus_clean_sheet`, `bonus_goals`, `count_exact`, `count_diff`, `count_outcome`, `total_points` (and any columns Coder's helper checks).

Tag: `[FIXTURE-SCORES-1-9]` PASS = 90/90 matched, 0 mismatches.

### 5.2 `[FIXTURE-SCORES-10]` Round 10 scores exist (no CSV contract)

Assert 10 rows exist; values non-null totals. No 90-row CSV for round 10 — spot-check one user has `total_points >= 0`.

---

## 6. Pytest regression — mandatory

### 6.1 `[REGRESS-CALC-PERSIST]` Integration calculate path unchanged

```bash
uv run pytest tests/integration/test_calculate_persistence_1_2.py -v
```

**Pass:** all green. Test DB must **not** pre-populate `scores` for rounds 1–9 (test drives `calculate_round`).

### 6.2 `[REGRESS-CALC-LB]` API calculate/leaderboard suite

```bash
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
```

### 6.3 `[REGRESS-SCORING-CONTRACT]` Engine vs CSV (independent of fixture)

```bash
uv run pytest tests/scoring/test_contracted_scores.py -v
```

### 6.4 `[SCRIPT-FINALIZE-IDEMPOTENT]` New script test (if you add §3 file)

| Tag | Assert |
|-----|--------|
| `[SCRIPT-FINALIZE-IDEMPOTENT]` | Run `finalize_dev_fixture` twice → still 100 score rows, no duplicate `(user_id, round_id)` |
| `[SCRIPT-FINALIZE-PROFILE-MANUAL]` | After manual orchestrator → SQL §4.1 table |
| `[SCRIPT-FINALIZE-PROFILE-E2E]` | After `--e2e` → round 10 `ACTIVE`, not `CALCULATED` |

---

## 7. API smoke — after manual profile (§2.1)

Backend on `:8000`. Use supervisor token from login smoke (no password in report).

### 7.1 `[API-ROUNDS-LIST]`

`GET /api/v1/contests/1/rounds` → includes rounds 1–11; statuses match §4.1.

### 7.2 `[API-GLOBAL-LB]`

`GET /api/v1/contests/1/leaderboard` → `200`; leaderboard length > 0 (aggregates **PUBLISHED** rounds 1–9 only after 2.3.1; until then document actual behaviour).

### 7.3 `[API-ROUND-10-SUPERVISOR]`

`GET /api/v1/contests/1/rounds/{round10_id}/leaderboard` with **supervisor** JWT:

- After 2.3.1: **200** (CALCULATED preview allowed for supervisor).
- Before 2.3.1: document whether 200 or 403 — note in report.

### 7.4 `[API-ROUND-11-CLOSED]`

Public / user token on round 11 leaderboard or results → **403** or stub payload (per current API); round 11 has no scores.

### 7.5 `[API-PUBLISH-ROUND-10]` (manual smoke, optional)

`POST …/rounds/{round10_id}/publish` as supervisor → round 10 becomes `PUBLISHED`; public LB may then include tour 10 (after 2.3.1 gate). **Revert** via reload if testing in shared DB, or note one-way mutation in report.

---

## 8. E2E profile — round 10 ACTIVE restoration

### 8.1 `[E2E-PROFILE-ACTIVE-R10]`

After §2.3 bootstrap:

1. SQL or API: round 10 `status === 'ACTIVE'`.
2. `deadline` in the future.
3. `scores` count for round 10 = **0** (E2E profile skips finalize on 10).

If `frontend/e2e/fixtures/adminApi.ts` has `ensureRound10Active()` or `reloadLoadedContestFixture()`:

```bash
cd frontend
# Backend on :8000 from E2E profile
npm run test:e2e -- supervisor_24h_rule.spec.ts supervisor_active_round.spec.ts
```

**Pass:** specs that depend on ACTIVE round 10 still pass (or document pre-existing failures unrelated to 1.14).

### 8.2 Playwright teardown (if E2E run)

See **§10** and `tester_2.1.md` §2.5 — mandatory `[E2E-TEARDOWN]` after any Playwright run.

---

## 9. Documentation audit

| ID | Check |
|----|-------|
| `[DOC-DEV-SETUP]` | `manuals/DEV_SETUP.md` — table: 1–9 `PUBLISHED`, 10 `CALCULATED`, 11 `CLOSED` after finalize |
| `[DOC-STATUS-REF]` | `manuals/STATUS_REFERENCE.md` — dev fixture round numbers + visibility note |
| `[DOC-MANUAL-SCORING]` | `manuals/MANUAL_SCORING_VERIFICATION.md` — expects 100 score rows after dev finalize |

---

## 10. Playwright teardown (when E2E executed)

> **Reference:** `tester_2.1.md` §2.5 — mandatory after **every** E2E run.

1. Ensure `playwright test` / `npm run test:e2e` has **fully exited** (no hung worker).
2. Verify ports free:

```bash
uv run python src/scripts/dev_setup.py --check-ports
```

→ exit **0** required.

3. If ports busy — kill orphans (`next dev`, headless Chromium), re-run `--check-ports`.
4. **Warn:** do not leave `next dev` or Playwright workers running — blocks `:3000` for `dev_setup --run-only`.
5. Local runs: `reuseExistingServer: !process.env.CI` in `playwright.config.ts` — still run §2.5 after local E2E.

| Tag | Pass criteria |
|-----|---------------|
| `[E2E-TEARDOWN]` | `--check-ports` exit 0; no orphan `next` / headless Chromium on `:3000` |

Consider documenting `globalTeardown` or `e2e/README.md` pattern in report if Coder adds one.

---

## 11. Linting (before handoff)

```bash
uv run ruff check src/ tests/
uv run mypy src/
```

If you added test files only under `tests/scripts/`, include them in ruff scope.

---

## 12. Execution order

```bash
# 1. Pytest regression FIRST (isolated DB — no finalize)
uv run pytest tests/integration/test_calculate_persistence_1_2.py \
  tests/api/test_calculate_leaderboard_1_4.py \
  tests/scoring/test_contracted_scores.py -v

# 2. Manual dev profile bootstrap
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
# 2b. SQL §4 + contract §5
# 2c. API smoke §7

# 3. Optional: new script tests
uv run pytest tests/scripts/test_finalize_dev_fixture_1_14.py -v

# 4. E2E profile §2.3
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
# 4b. E2E subset §8.1 (if backend + frontend up)
cd frontend && npm run test:e2e -- supervisor_24h_rule.spec.ts supervisor_active_round.spec.ts

# 5. Teardown (if step 4 ran)
uv run python src/scripts/dev_setup.py --check-ports

# 6. Lint
uv run ruff check src/ tests/

# 7. Doc audit §9 (read-only)
```

**Handoff order:** `TEST_PASS` here → recommended before full manual matrix in `tester_2.3.1_fix_rounds.md` (needs round 10 `CALCULATED`, round 11 `CLOSED`).

---

## 13. Report template — `agent_docs/reports/test_1.14_data_fix.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[FIXTURE-1-9-PUBLISHED]` | PASS/FAIL | |
| `[FIXTURE-10-CALCULATED]` | PASS/FAIL | |
| `[FIXTURE-11-CLOSED]` | PASS/FAIL | |
| `[FIXTURE-11-DEADLINE]` | PASS/FAIL | |
| `[FIXTURE-10-NOT-PUBLISHED]` | PASS/FAIL | |
| `[FIXTURE-TOTAL-SCORES]` | PASS/FAIL | count=100 |
| `[FIXTURE-SCORES-1-9]` | PASS/FAIL | 90/90 |
| `[FIXTURE-SCORES-10]` | PASS/FAIL | |
| `[REGRESS-CALC-PERSIST]` | PASS/FAIL | |
| `[REGRESS-CALC-LB]` | PASS/FAIL | |
| `[REGRESS-SCORING-CONTRACT]` | PASS/FAIL | |
| `[SCRIPT-FINALIZE-*]` | PASS/FAIL/SKIP | |
| `[API-ROUNDS-LIST]` | PASS/FAIL | |
| `[API-GLOBAL-LB]` | PASS/FAIL | |
| `[API-ROUND-10-SUPERVISOR]` | PASS/FAIL | |
| `[API-ROUND-11-CLOSED]` | PASS/FAIL | |
| `[E2E-PROFILE-ACTIVE-R10]` | PASS/FAIL/SKIP | |
| `[E2E-TEARDOWN]` | PASS/FAIL/SKIP | only if E2E ran |
| `[DOC-DEV-SETUP]` | PASS/FAIL | |
| `[DOC-STATUS-REF]` | PASS/FAIL | |
| `[DOC-MANUAL-SCORING]` | PASS/FAIL | |

**Verdict:** `TEST_PASS` / `TEST_FAIL` with blockers for @Coder.

On **TEST_PASS:**

- Dev fixture ready for supervisor manual QA and `tester_2.3.1_fix_rounds.md` full matrix.
- Append to `agent_docs/progress/stage_1.md` (or stage file Coder uses):

```
## YYYY-MM-DD — Tester (1.14 data fix)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_1.14_data_fix.md
- Fixture: rounds 1–9 PUBLISHED (90 scores), 10 CALCULATED (10), 11 CLOSED (0)
- Regression: test_calculate_persistence_1_2.py OK
- Next: tester_2.3.1_fix_rounds.md (after coder_2.3.1 READY_FOR_TEST)
```

---

## 14. Acceptance mapping (Coder §9)

| Criterion | Test ID |
|-----------|---------|
| After full `dev_setup`, SQL §7.1 matches | `[FIXTURE-1-9-PUBLISHED]`, `[FIXTURE-10-CALCULATED]`, `[FIXTURE-11-CLOSED]` |
| Rounds 1–9 scores ≡ `expected_scores.csv` | `[FIXTURE-SCORES-1-9]` |
| Round 10 `CALCULATED`, not `PUBLISHED` | `[FIXTURE-10-NOT-PUBLISHED]` |
| Round 11 `CLOSED`, deadline passed | `[FIXTURE-11-CLOSED]`, `[FIXTURE-11-DEADLINE]` |
| `test_calculate_persistence_1_2.py` unchanged pass | `[REGRESS-CALC-PERSIST]` |
| E2E path to ACTIVE round 10 | `[E2E-PROFILE-ACTIVE-R10]` |
| `DEV_SETUP.md` accurate | `[DOC-DEV-SETUP]` |

---

## 15. Explicitly OUT OF SCOPE

- Per-status admin UI panels → `tester_2.3.1_fix_rounds.md`
- 24h deadline rule semantics change → `tester_2.3.1_fix_rounds.md`
- Public LB `PUBLISHED`-only enforcement → `tester_2.3.1_fix_rounds.md`
- `/admin` → `/supervisor` rename → `tester_1.13_supervisor_rename.md`
