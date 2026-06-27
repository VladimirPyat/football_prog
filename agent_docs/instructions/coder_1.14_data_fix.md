# Coder Instructions — Stage 1.14: Dev Fixture Data Fix (Round Statuses & Scores)

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 1.2 loader + `dev_setup.py`; manual QA feedback 2026-06-27.
> **Related:** `manuals/STATUS_REFERENCE.md`, `agent_docs/contracts/contest_lifecycle_flow.md`, `docs/test_data/contracted/*`
> **Non-goals:** Changing round status **enum values** in DB/API; `coder_2.3.1_fix` (24h / match-edit policy).
> **Follow-up tester:** `agent_docs/instructions/tester_1.14_data_fix.md`

---

## 1. Objective

After `load_test_data.py --reset` + `dev_setup.py`, dev contest `id=1` must expose **all meaningful round phases** for manual supervisor QA — not only `CLOSED` (1–9) + `ACTIVE` (10).

| ID | Problem | Target |
|----|---------|--------|
| **D1** | Rounds 1–9 stay `CLOSED`; `scores` table **empty** after loader | `PUBLISHED` + `scores` rows (contracted 90/90) |
| **D2** | Round 10 only `ACTIVE` / open predictions | `CALCULATED` + `scores` (10 rows), **not** published — demo «Рассчитан» |
| **D3** | No round 11 | New round **11** = `CLOSED`, deadline passed (ref. date **2026-06-27**), matches awaiting results entry |
| **D4** | `DEV_SETUP.md` claims «rounds 1–9 published» but loader never calculates | Align script + docs |

**E2E compatibility:** prediction / ACTIVE-round tests must keep a path to **round 10 ACTIVE** (see §6).

---

## 2. Policy clarification — `CALCULATED` vs `PUBLISHED` vs leaderboard

> Source: `src/services/leaderboard_service.py`, `agent_docs/contracts/contest_lifecycle_flow.md`, `manuals/STATUS_REFERENCE.md`

| Question | Answer |
|----------|--------|
| What is **`CALCULATED`**? | Supervisor ran `POST …/calculate`. Engine wrote rows to table **`scores`** (`points_*`, `bonus*`, `count_*`, totals). Round status → `CALCULATED`. |
| What is **`PUBLISHED`**? | Supervisor confirmed `POST …/publish`. Round status → `PUBLISHED`. Results treated as **final** in admin UX (VOID still allowed). |
| Are points in DB before `CALCULATED`? | **No** in `scores`. Match **results** live in `matches.score1/score2` only until calculate. |
| Does leaderboard need `PUBLISHED`? | **Yes** for participants and visitors. **`CALCULATED`** is visible only to **SUPERVISOR/ADMIN** (admin preview). See `manuals/STATUS_REFERENCE.md` §2.3. |
| Why publish at all? | Supervisor confirmation; until then public UI shows «Будет доступно после проверки организатором». |

**User misconception to fix in UI copy (later):** «Рассчитан» ≠ «скрыт из таблицы»; очки уже в `scores` и видны в API. «Опубликован» = финальное подтверждение, не первое появление очков.

---

## 3. Inventory — what is stored **today** after default bootstrap

Pipeline: `load_test_data.py --reset` → `bootstrap_users.py` → `dev_setup.py --ensure-running-only`.

### 3.1 Tables (conceptual — after current loader)

| Entity | Rounds 1–9 | Round 10 | Round 11 |
|--------|------------|----------|----------|
| `rounds.status` | `CLOSED` | `ACTIVE` (after `ensure_dev_contest_running`) | **does not exist** |
| `rounds.deadline` | historical (Jul–Sep 2025 from CSV) | shifted to ~now+14d | — |
| `matches.status` | `FINISHED` | `SCHEDULED` | — |
| `matches.score1/2` | real results from CSV | `NULL` | — |
| `predictions` | full grid per CSV (~8×10 per round) | **none** in contracted CSV | — |
| `scores` | **0 rows** | **0 rows** | — |
| `contests.status` | `RUNNING` after dev_setup | same | same |
| `contests.is_locked` | `true` | same | same |

### 3.2 What loader **does** load (`src/scripts/load_test_data.py`)

- CSV: `docs/test_data/contracted/{teams,users,matches,predictions}.csv`
- Rounds **1–10 only** (no round 11 in `matches.csv`)
- Status convention hardcoded: `round_number < 10` → `CLOSED`, else `ACTIVE`
- Does **not** call `calculate_round` / `publish`
- Contract reference: `expected_scores.csv` (90 rows = users × rounds **1–9**), `leaderboard.csv` (aggregates rounds 1–9)

### 3.3 What tests expect (do not break)

| Consumer | Expectation |
|----------|-------------|
| `tests/integration/test_calculate_persistence_1_2.py` | Fresh DB: rounds 1–9 `CLOSED`, then **test** calls `calculate_round` |
| `tests/api/conftest.py` → `calculate_rounds_via_http` | Calculates rounds 1–9 via HTTP from `CLOSED` |
| E2E `ensureRound10Active` | Round 10 `ACTIVE` with future deadline |
| `tests/scoring/test_contracted_scores.py` | Engine vs CSV; independent of DB fixture |

→ **Do not** bake `PUBLISHED` into `load_test_data.py` alone without a profile flag — breaks calculate tests.

---

## 4. Target fixture — contest `id=1` (manual dev profile)

Reference «today» for new dates: **2026-06-27** (UTC).

| Round | `rounds.status` | `deadline` (illustrative) | `matches` | `predictions` | `scores` rows |
|-------|-----------------|---------------------------|-----------|---------------|---------------|
| **1–9** | `PUBLISHED` | unchanged (historical CSV) | `FINISHED` + CSV scores | loaded | **10 per round** (90 total), values ≡ `expected_scores.csv` |
| **10** | `CALCULATED` | e.g. `2026-06-26T12:00:00Z` (passed) | `FINISHED` + **synthetic** results (see §5.2) | optional minimal seed OR none (zeros OK) | **10 rows** |
| **11** | `CLOSED` | e.g. `2026-06-27T08:00:00Z` (passed) | `SCHEDULED`, kickoff afternoon 27.06 | none required | **0** (awaiting results + calculate) |
| **12+** | — | not created | — | — | — |

**UI labels (frontend, separate task):** API `CLOSED` → «Дедлайн»; round 11 demonstrates that phase.

### 4.1 Supervisor walkthrough enabled

| Round | Screen to demo |
|-------|----------------|
| 1–9 `PUBLISHED` | Public leaderboard / results — full history |
| 10 `CALCULATED` | Admin preview on «Туры»; **public** LB for tour 10 **hidden** until publish (`coder_2.3.1` §9.9) |
| 11 `CLOSED` | Results entry demo; public stub |
| 11 `CLOSED` | Results — enter scores, then **«Рассчитать»** |

---

## 5. Data plan — what to write where

### 5.1 Rounds 1–9 → `PUBLISHED`

**Step A — idempotent calculate (per round 1..9):**

```
FOR each round r in 1..9:
  IF no rows in scores WHERE round_id = r.id:
    ASSERT r.status == CLOSED  (or transition ACTIVE→CLOSED if needed — should not happen)
    CALL calculate_round(session, r.id, contest_id=1)
    ASSERT r.status == CALCULATED
    ASSERT 10 score rows (one per contracted user)
    ASSERT values match expected_scores.csv (reuse tests/api/reference_compare.py helpers)
```

**Step B — publish:**

```
FOR each round r in 1..9:
  IF r.status == CALCULATED:
    CALL transition_round(session, r.id, PUBLISHED)
```

**No changes** to `matches` / `predictions` — already correct from CSV.

### 5.2 Round 10 → `CALCULATED` (not `PUBLISHED`)

**Matches** (from CSV pairings, round 10 in `matches.csv`):

| match_num | home | away |
|-----------|------|------|
| 1–8 | КрСов/Ахм/… | per `matches.csv` lines 74–81 |

**Apply:**

1. Set `date_time` to past window, e.g. **2026-06-26T15:00Z** … **2026-06-26T22:00Z** (stagger +1h).
2. Set `status = FINISHED`, assign **synthetic** `score1/score2` (CSV `0:0` is placeholder for SCHEDULED — pick e.g. `1:0`, `2:1`, `1:1`, …).
3. Set `round.deadline` = **2026-06-26T12:00:00Z** (before first kickoff).
4. Set `round.status = CLOSED` (deadline passed).
5. Optional: insert **predictions** for 10 users × 8 matches (synthetic) so calculate is non-trivial — **not required** for status demo (zeros if absent).
6. `calculate_round` → `CALCULATED`.
7. **Do not** publish.

### 5.3 Round 11 → `CLOSED` (new data)

**Create** round (not in CSV today):

```
round.number = 11
round.status = CLOSED
round.deadline = 2026-06-27T08:00:00+00:00
round.matches_count = 8
```

**8 matches** — reuse teams from round 10 CSV pairings **or** next unused pairings from calendar; all:

```
status = SCHEDULED
score1 = score2 = NULL
date_time = 2026-06-27T14:00Z .. 21:00Z (stagger)
```

No `predictions` unless you add a small seed block (optional).

**Contest metadata:** `contests.total_rounds` may stay 30 (structural max); no need to bump unless UI lists «only up to total_rounds».

### 5.4 Contest row

Unchanged: `status=RUNNING`, `is_locked=true` (set by existing `ensure_dev_contest_running`).

---

## 6. Implementation design

### 6.1 New module (recommended)

```
src/scripts/finalize_dev_fixture.py   # async core + CLI
```

**Functions:**

| Function | Purpose |
|----------|---------|
| `finalize_rounds_1_9_published(session, contest_id=1)` | §5.1 |
| `finalize_round_10_calculated(session, contest_id=1, *, reference_now)` | §5.2 |
| `ensure_round_11_closed(session, contest_id=1, *, reference_now)` | §5.3 idempotent |
| `finalize_dev_fixture(contest_id=1, profile="manual")` | orchestrator |

**Reuse:** `calculate_round` from `scoring_persistence`; `transition_round` from `round_service`; validation helpers from `tests/api/reference_compare.py` (move shared asserts to `src/scripts/` or import in dev-only path).

### 6.2 Wire into `dev_setup.py`

| Flag | Behaviour |
|------|-----------|
| `--ensure-running-only` (extend) | RUNNING + **full `finalize_dev_fixture(profile=manual)`** |
| `--ensure-running-only --e2e` | RUNNING + round 10 **ACTIVE** future dates only (current behaviour); **skip** publish 1–9 if env `E2E_FIXTURE=1` OR explicit flag |
| `--finalize-fixture-only` | Run finalize without servers (repair existing DB) |

**Default `--run` / full setup:** after loader + bootstrap → `finalize_dev_fixture(manual)`.

### 6.3 Do **not** change by default

- `load_test_data.py` status convention for **pytest** (`CLOSED` 1–9, `ACTIVE` 10) — keep unless `--profile` passed to loader (optional future).

### 6.4 E2E repair path

`frontend/e2e/fixtures/adminApi.ts` → `reloadLoadedContestFixture()`:

- Option A: call `dev_setup.py --ensure-running-only --e2e` (restores ACTIVE round 10)
- Option B: keep resetting round 10 via API in `ensureRound10Active`

Document in instruction handoff for tester if behaviour changes.

---

## 7. Verification checklist

### 7.1 SQL (SQLite)

```sql
SELECT r.number, r.status, r.deadline,
       (SELECT COUNT(*) FROM scores s WHERE s.round_id = r.id) AS score_rows,
       (SELECT COUNT(*) FROM matches m WHERE m.round_id = r.id) AS match_rows
FROM rounds r
WHERE r.contest_id = 1
ORDER BY r.number;
```

**Expected after fix:**

| number | status | score_rows |
|--------|--------|------------|
| 1–9 | PUBLISHED | 10 each |
| 10 | CALCULATED | 10 |
| 11 | CLOSED | 0 |

### 7.2 API smoke

```bash
# Global leaderboard — only PUBLISHED rounds (1–9 after finalize; not round 10 until publish)
curl -s http://127.0.0.1:8000/api/v1/contests/1/leaderboard | jq '.leaderboard | length'

# Round 10 public leaderboard → 403 until publish (after 2.3.1 backend §9.9.2)
# Round 10 supervisor preview → 200 with supervisor token

# Round 11 public → 403 (CLOSED)
```

### 7.3 Contract regression

```bash
uv run pytest tests/integration/test_calculate_persistence_1_2.py -v   # unchanged DB fixture
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
```

If finalize runs in dev only, integration tests stay green.

---

## 8. Docs to update

| File | Change |
|------|--------|
| `manuals/DEV_SETUP.md` | §What `--full` does — accurate table 1–9 PUBLISHED, 10 CALCULATED, 11 CLOSED after finalize |
| `manuals/STATUS_REFERENCE.md` | §2.3 visibility; dev fixture round numbers |
| `manuals/MANUAL_SCORING_VERIFICATION.md` | SQL example: expect 100 score rows (90 + 10) after dev finalize |
| `agent_docs/instructions/coder_2.3.1_fix.md` | Cross-link: dev fixture round 11 for CLOSED results demo |

---

## 9. Acceptance criteria

- [ ] After `uv run python src/scripts/dev_setup.py` (full), SQL §7.1 matches target
- [ ] Rounds 1–9 `scores` match `expected_scores.csv` (90/90)
- [ ] Round 10 `CALCULATED`, not `PUBLISHED`; publish button works in admin UI
- [ ] Round 11 exists, `CLOSED`, deadline before 2026-06-27 EOD; results entry enabled
- [ ] `pytest tests/integration/test_calculate_persistence_1_2.py` still passes (no loader regression)
- [ ] E2E path to ACTIVE round 10 documented and working (`--e2e` or `ensureRound10Active`)
- [ ] `manuals/DEV_SETUP.md` no longer contradicts loader

---

## 10. Execution order (Coder)

```bash
# 1. Implement finalize_dev_fixture.py + dev_setup flags
# 2. Run on fresh DB
uv run python src/scripts/dev_setup.py

# 3. Verify
uv run python -c "..."  # or sqlite3 queries §7.1

# 4. Regression
uv run pytest tests/integration/test_calculate_persistence_1_2.py tests/api/test_calculate_leaderboard_1_4.py -v

# 5. Update manuals §8
```

**Handoff:** `READY_FOR_TEST` → manual QA all round statuses on `/admin/rounds` + `/admin/results` + public leaderboard.

---

## Appendix A — Two layers of «очки»

| Layer | Table / field | When populated | Used for |
|-------|---------------|----------------|----------|
| Match result | `matches.score1`, `matches.score2` | Supervisor enters on Results (or CSV loader for 1–9) | Input to scoring engine |
| User round score | `scores.*` | `calculate_round` | Leaderboard, tie-breakers, bonuses |

User phrase «очки уже в базе» for rounds 1–9 means **match results** are loaded; **`scores`** still require calculate (and publish is a separate status bit).

---

## Appendix B — Round 10 vs E2E predictions

| Profile | Round 10 | Use case |
|---------|----------|----------|
| `manual` (default dev) | `CALCULATED` | Status walkthrough, publish demo |
| `e2e` | `ACTIVE`, future deadline | `supervisor_24h_rule`, prediction batch tests |

Both can coexist via flags; never silently break E2E.
