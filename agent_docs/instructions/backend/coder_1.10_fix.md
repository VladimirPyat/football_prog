# Coder Instructions — Stage 1.10 Fix: Multi-Contest UNIQUE + Stage 2.3 Unblock

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 2.3 Coder `READY_FOR_TEST`; Tester 2.3 `TEST_FAIL` — see `agent_docs/reports/test_2.3.md`.
> **Blockers:** **B7**, **B8** in `agent_docs/reports/BLOCKED.md`.
> **Goal:** Unblock `tester_2.3` re-run — fix root-cause DB constraints + minor frontend defects from test report.
> **Language policy:** code comments English; HTTP `detail` Russian; UI copy Russian.

---

## 1. Objective

Close blockers discovered during Stage **2.3** E2E verification. Primary failure is **backend** — legacy global UNIQUE constraints survived migration `c4d5e6f7a8b9` on SQLite. Secondary fixes are **frontend** polish required for `[E2E-SUPERVISOR-VOID]` and `[LINT-PRETTIER]`.

| ID | Severity | Fix owner | Summary |
|----|----------|-----------|---------|
| **B7** | CRITICAL | Backend | Drop global `UNIQUE(rounds.number)` — allows round `number=1` per contest |
| **B8** | CRITICAL | Backend | Drop global `UNIQUE(teams.name)` — allows same team name across contests |
| **F1** | HIGH | Frontend | VOID button visible on `PUBLISHED` round (`MatchResultRow`) |
| **F2** | LOW | Frontend | Prettier on 18 admin files (`npm run format`) |

**Non-goals:**

- Rewriting E2E specs (Tester owns `frontend/e2e/*`)
- Updating `tester_2.3.md` bootstrap (Planner/Tester — note only in handoff)
- Public leaderboard polish → **2.4**
- Re-run full Playwright suite (Tester after this fix)

---

## 2. Root cause (evidence)

Migration `alembic/versions/c4d5e6f7a8b9_multi_contest_and_participants.py` added per-contest constraints via `batch_alter_table(..., recreate="always")` but **did not remove** legacy singleton-era indexes from `0992bb744cc8_initial_schema.py`:

| Table | Legacy (must drop) | Correct (keep) |
|-------|-------------------|----------------|
| `rounds` | `sqlite_autoindex_rounds_1` UNIQUE(`number`) | `uq_rounds_contest_number` (`contest_id`, `number`) |
| `teams` | `sqlite_autoindex_teams_1` UNIQUE(`name`) | `uq_teams_contest_name` (`contest_id`, `name`) |

SQLAlchemy models in `src/database/models.py` are **already correct** — only per-contest uniques. Bug is **DB state only**.

**Verify before/after** (SQLite dev DB):

```bash
sqlite3 football.db ".indexes rounds"
sqlite3 football.db ".indexes teams"
```

After fix: **no** index with UNIQUE on `number` or `name` alone; composite indexes remain.

---

## 3. Part A — Backend (B7, B8)

### 3.1 New Alembic migration

Create revision **after** `c4d5e6f7a8b9`, e.g. `d5e6f7a8b9c0_drop_legacy_global_uniques.py`.

**Strategy (SQLite):** `batch_alter_table(..., recreate="always")` for `teams` and `rounds`, re-declaring **only** columns + FK + composite unique — **do not** recreate global `UniqueConstraint('name')` or `UniqueConstraint('number')`.

**`teams` columns (mirror models):**

- `id`, `contest_id` (FK → `contests.id` ON DELETE CASCADE), `name`, `short_name`, `logo_url`
- Constraint: `uq_teams_contest_name` on (`contest_id`, `name`)

**`rounds` columns:**

- `id`, `contest_id` (FK), `number`, `deadline`, `status`, `matches_count`
- Constraint: `uq_rounds_contest_number` on (`contest_id`, `number`)

**Data safety:** `recreate="always"` copies rows — no data loss. Test on copy of dev DB before handoff.

**Downgrade:** Restore global uniques only if strictly needed for rollback; document that downgrade fails when duplicate cross-contest names/numbers exist.

### 3.2 IntegrityError safety net (B8 follow-up)

Service layer already checks duplicate name **within contest** (`create_team` → `ValidationError` 400). After migration, cross-contest duplicates succeed.

Add defensive mapping so any remaining DB unique violation returns **409**, not **500**:

| File | Change |
|------|--------|
| `src/core/exceptions.py` | Add `ConflictError(AppError)` with `http_status = 409`, `code = "CONFLICT"` |
| `src/api/error_handlers.py` | In `unhandled_exception_handler`, catch `sqlalchemy.exc.IntegrityError` → log warning → `ConflictError("Конфликт данных: запись уже существует")` |

Optional: catch in `create_team` / `create_round` flush only — prefer **central handler** for consistency.

**Do not** catch-all swallow — re-raise unknown IntegrityError after logging if message doesn't match known constraints.

### 3.3 API regression tests

Extend or add tests proving multi-contest isolation **with colliding names/numbers**:

```
tests/api/test_multi_contest_unique_fix_1_10.py   # NEW
```

| Test ID | Scenario | Assert |
|---------|----------|--------|
| `[FIX-B7-ROUND]` | Contest A has round `number=1`; create round `number=1` in contest B | **201/200**, not 500 |
| `[FIX-B8-TEAM]` | Contest A has team `"E2E Team 1"`; create same name in contest B | **200**, not 500 |
| `[FIX-B8-DUP-IN-CONTEST]` | Same contest, duplicate team name | **400** `ValidationError` (existing behaviour) |
| `[FIX-B7-DUP-IN-CONTEST]` | Same contest, duplicate round number | **400** `ValidationError` |

Use `empty_api` fixture pattern from `tests/api/test_multi_contest_1_4.py`.

**Optional:** Add `[FIX-INDEX-SCHEMA]` in `tests/db/` — after migration, assert index list via SQLAlchemy inspector (skip on non-SQLite).

### 3.4 Scope — backend files

```
alembic/versions/d5e6f7a8b9c0_drop_legacy_global_uniques.py   # NEW
src/core/exceptions.py                                          # ConflictError
src/api/error_handlers.py                                       # IntegrityError → 409
tests/api/test_multi_contest_unique_fix_1_10.py                 # NEW
agent_docs/reports/BLOCKED.md                                   # B7/B8 → RESOLVED
agent_docs/progress/stage_1.md                                  # append handoff
manuals/DB_REFERENCE.md                                         # note per-contest uniques (if index section exists)
```

**Do NOT modify:** `docs/`, `src/scoring/*`, SQLAlchemy models (already correct).

### 3.5 Backend verification

```bash
cd /work/football_prog
uv run alembic upgrade head
sqlite3 football.db ".indexes rounds"    # no global number unique
sqlite3 football.db ".indexes teams"     # no global name unique

# Manual API smoke (supervisor token):
# POST /api/v1/contests  → id=2
# POST /api/v1/contests/2/teams  {"name":"Team 1",...}  → 200
# POST /api/v1/contests/2/admin/rounds  {"number":1,...}  → 200

uv run pytest tests/api/test_multi_contest_unique_fix_1_10.py tests/api/test_multi_contest_1_4.py -v
uv run pytest tests/ -q --tb=no   # full regression
```

---

## 4. Part B — Frontend (F1, F2)

Unblocks `[E2E-SUPERVISOR-VOID]` and `[LINT-PRETTIER]` from `test_2.3.md`.

### 4.1 F1 — VOID on PUBLISHED round

**Problem:** `ResultsEntryPanel` passes `readonly={uiMode.resultsReadonly || !uiMode.canEnterResults}`. On `PUBLISHED`, `resultsReadonly=true` → `MatchResultRow` hides «Отменить» (`!readonly` guard).

**Spec (`docs/04_supervisor_scenario.md`, coder_2.3 §6.5):** VOID allowed after calculate/publish; scores stay locked.

**Fix:**

1. **`deriveAdminUiMode.ts`** — add flag:

```ts
canVoidMatch: boolean;  // true when round CLOSED | CALCULATED | PUBLISHED && !disableAllMutations
```

2. **`MatchResultRow.tsx`** — split props:
   - `scoresReadonly` — disables score inputs + «Завершён»
   - `canVoid` — controls «Отменить» visibility (independent of scores readonly)

3. **`ResultsEntryPanel.tsx`** — pass:
   - `scoresReadonly={uiMode.resultsReadonly || !uiMode.canEnterResults}`
   - `canVoid={uiMode.canVoidMatch && match.status !== "VOID"}`

4. **`deriveAdminUiMode.test.ts`** — add cases:
   - `PUBLISHED` → `canVoidMatch: true`, `resultsReadonly: true`
   - `PAUSED` → `canVoidMatch: false`

### 4.2 F2 — Prettier

```bash
cd frontend && npm run format
npm run format:check   # must exit 0
```

Target: admin files flagged in `test_2.3.md` (components/admin/*, lib/admin/*, hooks/use*Admin*, app/admin/*).

**Do not** change logic while formatting.

### 4.3 Scope — frontend files

```
frontend/src/lib/admin/deriveAdminUiMode.ts
frontend/src/lib/admin/deriveAdminUiMode.test.ts
frontend/src/components/admin/MatchResultRow.tsx
frontend/src/components/admin/ResultsEntryPanel.tsx
frontend/src/**/admin/**          # prettier only
frontend/src/hooks/use*Admin*.ts  # prettier only
```

### 4.4 Frontend verification

```bash
cd frontend
npm run test:unit        # all pass, including new deriveAdminUiMode cases
npm run format:check     # 0
npm run lint && npm run type-check && npm run build
```

---

## 5. BLOCKED.md update

After verification, update status table:

```markdown
| B7 | RESOLVED | Migration d5e6f7a8b9c0 — legacy global UNIQUE on rounds.number dropped |
| B8 | RESOLVED | Same migration — legacy global UNIQUE on teams.name dropped; IntegrityError → 409 |
```

Move OPEN sections to a **Resolved** appendix; keep evidence for audit.

---

## 6. Acceptance criteria

Manual + automated:

- [ ] Fresh contest `id>1`: `POST …/teams` with name colliding with contest 1 → **200**
- [ ] Fresh contest: `POST …/admin/rounds` with `number=1` → **200**
- [ ] Same-contest duplicate name/number → **400**, not 500
- [ ] `[FIX-B7-*]` / `[FIX-B8-*]` pytest green
- [ ] Full backend regression green
- [ ] `deriveAdminUiMode`: `PUBLISHED` → `canVoidMatch=true`
- [ ] `npm run format:check` exit 0
- [ ] `npm run test:unit` + `npm run build` exit 0
- [ ] B7/B8 marked RESOLVED in `BLOCKED.md`

**Deferred to Tester re-run (not blocking this fix):**

- E2E RBAC/login timeouts — may clear once B7/B8 fixed + bootstrap uses `dev_setup.py --ensure-running-only`
- `[E2E-ADMIN-PAUSE]` — requires contest `RUNNING` (bootstrap note for Tester)

---

## 7. Implementation order

1. Inspect current SQLite indexes (document in handoff)
2. Write + apply migration `d5e6f7a8b9c0`
3. `ConflictError` + IntegrityError handler
4. API tests `[FIX-B7/B8]`
5. Backend regression pytest
6. Frontend: `canVoidMatch` + component split
7. Prettier format
8. Frontend unit/build
9. Update `BLOCKED.md`, append progress logs

---

## 8. Handoff

### 8.1 `agent_docs/progress/stage_1.md`

```
## YYYY-MM-DD — Coder (1.10 fix — multi-contest UNIQUE)
- STATUS: READY_FOR_TEST
- Blockers closed: B7, B8
- Migration: d5e6f7a8b9c0_drop_legacy_global_uniques.py
- Verified: pytest multi_contest fix + regression; alembic upgrade head
- Next: tester_1.10_fix.md (or re-run tester_2.3 after frontend Part B)
```

### 8.2 `agent_docs/progress/stage_2.md`

```
## YYYY-MM-DD — Coder (1.10 fix — 2.3 unblock)
- STATUS: READY_FOR_RETEST
- Frontend: canVoidMatch on PUBLISHED, prettier
- Backend: B7/B8 resolved — see stage_1 handoff
- Verified: npm run test:unit, format:check, build
- Next: re-run agent_docs/instructions/tester_2.3.md
```

---

## 9. Explicitly OUT OF SCOPE

- Editing `tester_2.3.md` bootstrap section (recommend append `dev_setup.py --ensure-running-only` in handoff note only)
- Fixing E2E auth/session flakiness unless root-caused by code defect found during F1
- PostgreSQL-specific migration (SQLite dev target; PG uses named constraints — verify separately if CI uses PG)
- Stage 2.4 features
