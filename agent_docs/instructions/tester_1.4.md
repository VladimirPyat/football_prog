# Tester Instructions — Stage 1.4: Full HTTP E2E & Multi-Contest

> Status gate: @Coder `READY_FOR_TEST` for 1.4. Prerequisite: 1.3 `TEST_PASS`.
> Tests/reports English; user verdict Russian. Contracts: `api_v1.yaml`,
> `contest_lifecycle_flow.md`, `leaderboard_tiebreakers.md`, `bonus_rules.md`,
> reference data `docs/test_data/contracted/`.

## 1. Objective

**Full integration test via HTTP only** — no `load_test_data` for the main E2E flow.
Create contest from empty DB, SETUP phase (teams, participants, rules), operational phase
(rounds 1–9, activate, predictions, auto-close, results, calculate), verify **90/90**
against `expected_scores.csv` and **10/10** against `leaderboard.csv`.

Also verify multi-contest isolation, SETUP guards, close/auto-close, result deadline guards,
Free Tour, and contest-scoped exceptional tie-break.

**Regression:** `tests/integration/` (1.2 canary) must stay green — uses loader + legacy shims.

## 2. Scope — files you may create

```
tests/api/conftest.py                     # EXTEND: empty DB fixture, E2E helpers, time mocking
tests/api/test_setup_phase_1_4.py       # [SETUP-*]
tests/api/test_operational_phase_1_4.py # [OP-*] incl. close, result guards
tests/api/test_multi_contest_1_4.py     # [MULTI-*]
tests/api/test_calculate_leaderboard_1_4.py  # [API-CALC-*], [API-LB-*] — moved from 1.3
tests/api/test_free_tour_1_4.py         # [OP-FREE-*]
tests/manual/verify_via_api.py            # NEW — Script 1
tests/manual/compare_db_vs_reference.py   # NEW — Script 2
tests/manual/README.md
manuals/MANUAL_SCORING_VERIFICATION.md    # NEW — Russian human guide (Stage 1 sign-off)
```

Update `manuals/README.md` index to link the new guide.

Do NOT modify `src/`. Isolated test DB for destructive tests (delete contest).

## 3. E2E fixture strategy

**Primary fixture `empty_contest_db`:** migrate DB, seed ONLY admin/supervisor users (or create via API).
**No** `load_test_data.py` for main E2E class.

**Helper `build_contracted_contest_via_http(client)`:** sequential HTTP calls reproducing contracted data:
1. `POST /contests` with rules matching `contest_defaults.json`
2. Create 16 teams (names from `teams.csv`)
3. Add 10 participants (from `users.csv` logins)
4. Create rounds 1–9 with matches from `matches.csv` (parse dates/deadlines)
5. Activate rounds, submit predictions from contracted CSV values via API
6. Close rounds (wait or mock time past deadline), enter results, calculate

Use `freezegun` or deps override for deadline/auto-close if needed.

**Reference assertions:** load `expected_scores.csv`, `leaderboard.csv` read-only for comparison.

## 4. SETUP phase (`[SETUP-*]`)

- `[SETUP-CREATE]` POST `/contests` → 200, `status=DRAFT`, `is_locked=false`.
- `[SETUP-PATCH]` PATCH rules/structure before activate → 200.
- `[SETUP-TEAMS]` CRUD 16 teams; duplicate name in same contest → 400.
- `[SETUP-TEAMS-LOCK]` after activate, POST team → 403.
- `[SETUP-PART]` POST participant with email → 200, temp password returned; login works.
- `[SETUP-PART-LOCK]` after activate, DELETE participant → 403.
- `[SETUP-LIST]` GET teams/participants as SUPERVISOR → correct counts.

## 5. Operational phase (`[OP-*]`)

- `[OP-ACTIVATE]` first activate → contest `is_locked=true`, `status=RUNNING`.
- `[OP-PRED]` batch predictions ACTIVE round before deadline → 200; partial → 400.
- `[OP-PRED-DEADLINE]` after deadline → 403.
- `[OP-AUTOCLOSE]` ACTIVE round with `deadline <= now` → next API call → round CLOSED.
- `[OP-CLOSE]` POST `.../rounds/{id}/close` when deadline passed → CLOSED.
- `[OP-CLOSE-EARLY]` close before deadline → 400.
- `[OP-RESULT-GUARD]` PUT result before deadline → 403.
- `[OP-RESULT-OK]` after close + deadline → 200.
- `[OP-CALC]` calculate only when CLOSED → CALCULATED.
- `[OP-CALC-ACTIVE]` calculate on ACTIVE → 403/400.
- `[OP-PUBLISH]` CALCULATED → PUBLISHED.
- `[OP-VOID]` VOID → recalc; leaderboard updated.
- `[OP-FREE-TOUR]` POSTPONED match → free-tour → new round; match removed from source round.
- `[OP-PAUSE]` pause blocks predictions; resume restores.

## 6. Multi-contest (`[MULTI-*]`)

- `[MULTI-ISOLATE]` Two contests; teams in A not visible in B list.
- `[MULTI-RUNNING]` Contest A RUNNING while B still DRAFT setup.
- `[MULTI-TIEBREAK]` Same user in A and B; different exceptional points per contest.

## 7. Calculate + leaderboard (`[API-CALC-*]`, `[API-LB-*]`) — full contract

Moved from 1.3; **this is the authoritative 90/90 gate.**

- `[API-CALC]` calculate rounds 1–9 → CALCULATED, `users_scored` correct.
- `[API-RESULTS]` per `expected_scores.csv` — **90/90** (all columns per tester_1.1 gate).
- `[API-LB-GLOBAL]` per `leaderboard.csv` — **10/10** incl. tie-break pairs.
- `[API-VOID]` VOID → atomic recalc; leaderboard updated.
- `[API-CACHE]` public GET Cache-Control + ETag on contest-scoped leaderboard/results.
- `[API-CACHE-ETAG]` ETag changes after calculate.
- `[API-TB-SET]` ADMIN PUT `.../participants/{id}/exceptional-tiebreak` when locked → 200.
- `[API-TB-RANK]` synthetic tie; exceptional points decide rank.
- `[API-TB-RBAC]` SUPERVISOR cannot set → 403.

## 8. Manual two-phase verification (mandatory for Stage 1 sign-off)

### Script 1 — `tests/manual/verify_via_api.py`

- Drives **contest-scoped** endpoints only; no knowledge of expected CSV values.
- Phases: setup → operational → public GET smoke.
- Exit 0 on success.

### Manual STOP — DBeaver

Inspect DB after Script 1; do not mutate.

### Script 2 — `tests/manual/compare_db_vs_reference.py`

- Read-only: DB `scores` vs `expected_scores.csv`; aggregate vs `leaderboard.csv`.
- **CANARY:** deliberate CSV edit → Script 2 must fail.

Document env vars and contest_id in `tests/manual/README.md`.

## 8a. Human manual — `manuals/MANUAL_SCORING_VERIFICATION.md` (mandatory, Russian)

**Purpose:** Final Stage 1 sign-off document for the **project owner / organizer**.
The Tester writes it after scripts and pytest pass. Language: **Russian**.
Technical terms (table/column names, CLI commands) may stay in English/latin.

**Audience:** Someone who wants to manually prove that scores are computed from DB data
(not hardcoded) and match contracted reference CSVs.

### Required sections (use this outline)

1. **Цель и три уровня проверки**
   - 1.1 — pure engine (`tests/scoring/`, no DB)
   - 1.2 — persistence canary (`tests/integration/`, loader → `calculate_round` → `scores`)
   - 1.4 — full path via HTTP + DB vs CSV (this guide focuses on 1.2 + 1.4 manual flow)

2. **Эталонные файлы** (read-only, do not edit during normal runs)
   - `docs/test_data/contracted/predictions.csv` — прогнозы
   - `docs/test_data/contracted/matches.csv` — результаты матчей
   - `docs/test_data/contracted/expected_scores.csv` — ожидаемые очки (90 строк, раунды 1–9)
   - `docs/test_data/contracted/leaderboard.csv` — итоговый рейтинг (10 игроков)
   - `docs/test_data/config/contest_defaults.json` — правила scoring

3. **Быстрая автоматическая проверка (рекомендуется перед ручным прогоном)**
   ```bash
   uv run pytest tests/integration/test_calculate_persistence_1_2.py -v   # [CALC-ROUND] 90/90
   uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v           # [API-RESULTS] 90/90
   uv run pytest tests/integration/ tests/api/ -v                         # полный Stage 1 regression
   ```
   Explain what each command proves in plain Russian.

4. **Ручной двухфазный прогон (основной сценарий Stage 1 sign-off)**

   **Подготовка:**
   ```bash
   uv run alembic upgrade head
   # Option A — full HTTP setup (Script 1, after 1.4 Coder):
   uv run python tests/manual/verify_via_api.py [--database-url ...] [--base-url http://127.0.0.1:8000]
   # Option B — bootstrap DB from CSV then API calculate only (bridge, document if supported):
   uv run python src/scripts/load_test_data.py --reset
   uv run uvicorn main:app --host 127.0.0.1 --port 8000   # separate terminal
   ```
   Document exact env vars the scripts accept (`DATABASE_URL`, `CONTEST_ID`, `API_BASE_URL`).

   **Фаза 1 — Script 1 (`verify_via_api.py`):**
   - Что делает по шагам (setup → predictions → results → calculate) **без** чтения expected CSV.
   - Ожидаемый exit code 0.

   **STOP — DBeaver (read-only inspection):**
   - Path to SQLite file (default `./football.db` or test DB path from script output).
   - Tables to inspect and example queries:
     - `predictions` — строки прогнозов (отсутствие строки = нет прогноза, не 0:0)
     - `matches` — `score1`/`score2`, `status` (FINISHED / VOID / SCHEDULED)
     - `scores` — persisted totals after calculate (`total_with_bonus3`, `count_*`, bonuses)
     - `contest_participants` — exceptional tie-break points (after 1.4)
   - What to visually confirm before Script 2 (row counts, round statuses CALCULATED/PUBLISHED).

   **Фаза 2 — Script 2 (`compare_db_vs_reference.py`):**
   ```bash
   uv run python tests/manual/compare_db_vs_reference.py [--database-url ...] [--contest-id N]
   ```
   - Join logic: `user_login` + `round_number` → `scores` rows.
   - Columns compared (same as `[CALC-ROUND]` / `[API-RESULTS]`):
     `base`, `bonus1+bonus2`, `bonus3`, `total_with_bonus3`, optional `count_*`.
   - Global leaderboard vs `leaderboard.csv` (10/10).

5. **CANARY — доказательство, что ответы не зашиты в код**
   Step-by-step for the owner:
   1. Copy `expected_scores.csv` → edit one `expected_total` (or `predictions.csv` one score).
   2. Re-run Script 2 (or pytest) **without** changing application code.
   3. **Must FAIL** with a clear mismatch message (login, round, expected vs actual).
   4. Revert CSV change → must PASS again.
   Warn: never commit canary edits to reference files.

6. **Что менять для проверки разных слоёв**

   | If you change… | Re-run | Expected |
   |----------------|--------|----------|
   | `predictions.csv` → reload / re-submit via API | integration or Script 1+2 | FAIL on affected rows |
   | `matches.csv` result → reload / PUT result via API | same | FAIL |
   | `expected_scores.csv` only (canary) | Script 2 / pytest | FAIL (oracle changed) |
   | `scores` table directly in DBeaver | Script 2 after **no** recalculate | May PASS until recalculate overwrites |
   | Application `src/scoring/*` | `tests/scoring/` first | FAIL if math broken |

7. **Типичные проблемы (troubleshooting)**
   - Round not CLOSED → calculate returns 403/400 (1.4 guards).
   - Result before deadline → 403.
   - Partial predictions → 400 batch rejected.
   - SQLite path / wrong contest_id in multi-contest setup.

8. **Критерий приёмки Stage 1 (для владельца проекта)**
   - [ ] `tests/integration/` green — 90/90 persistence
   - [ ] `tests/api/` green — 90/90 via HTTP
   - [ ] Script 1 exit 0
   - [ ] Script 2 exit 0 (90/90 + 10/10)
   - [ ] CANARY fail → revert → pass
   - [ ] DBeaver inspection done (optional but recommended)

Link to related docs: [SCORING_LOGIC.md](SCORING_LOGIC.md),
[DB_REFERENCE.md](DB_REFERENCE.md), [API_GUIDE.md](API_GUIDE.md).

**Acceptance:** file exists, Russian prose, all sections above present, commands copy-pasteable.

## 9. Regression

```
uv run pytest tests/integration/ -v
```
Must remain green (loader + legacy shim paths).

## 10. Automated execution & report

```
uv run pytest tests/api/ -v
```

- **PASS** → `agent_docs/reports/test_1.4.md` (Russian) with [TEST-ID] table;
  append `STATUS: TEST_PASS` to `progress/stage_1.md`;
  confirm `manuals/MANUAL_SCORING_VERIFICATION.md` linked from `manuals/README.md`.
- **FAIL** → expected vs actual per [TEST-ID]; append `STATUS: TEST_FAIL`. Never edit `src/`.

## 11. Verdict to user (Russian)

Этап 1.4, PASS/FAIL, покрытие: full HTTP E2E setup→calculate, **90/90 + 10/10**,
multi-contest, auto-close/close, result guards, Free Tour, exceptional tie-break (contest-scoped),
manual scripts, integration regression green, дефекты с [TEST-ID].
**Финал Stage 1:** `manuals/MANUAL_SCORING_VERIFICATION.md` — инструкция по ручной проверке
логики подсчёта (рус.), CANARY, DBeaver.

## 12. Execution order (recommended)

1. Confirm 1.3 `TEST_PASS` (narrow HTTP tests on loader data).
2. Run 1.4 suite after Coder handoff.
3. Run manual scripts for sign-off.
4. Write `manuals/MANUAL_SCORING_VERIFICATION.md`; update `manuals/README.md` index.
5. Stage 1 complete when 1.4 `TEST_PASS` + human manual delivered.
