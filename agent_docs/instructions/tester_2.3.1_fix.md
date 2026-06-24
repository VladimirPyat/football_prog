# Tester Instructions — Stage 2.3.1 Fix: E2E + Bootstrap Repair

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Coder **1.10 fix** `READY_FOR_RETEST`; B7/B8 **RESOLVED** in `agent_docs/reports/BLOCKED.md`.
> **Prior report:** `agent_docs/reports/test_2.3.md` § Retest — 4/17 E2E passed; unit/build/prettier OK.
> **Parent spec:** `agent_docs/instructions/tester_2.3.md` (full acceptance matrix unchanged).
> **Goal:** Fix E2E infra bugs → re-run full `tester_2.3.md` → `TEST_PASS` for Stage 2.3.
> **Strategy:** Fix tests/fixtures only; **do not modify** `src/` unless new backend blocker found.

---

## 1. Objective

Close **test-side** failures blocking Stage 2.3 sign-off. Production admin UI and backend multi-contest are already verified (unit 37/37, pytest B7/B8, build).

| ID | Category | Summary |
|----|----------|---------|
| **T1** | Bootstrap order | `load_test_data --reset` wipes users → must re-run `bootstrap_users` **after** load |
| **T2** | Credentials | Align supervisor/admin passwords between root `.env`, `frontend/.env.local`, and DB |
| **T3** | `adminApi.ts` | `ensureContestRunning` must use **ADMIN** token for `resume` (supervisor → 403) |
| **T4** | Missing imports | `gotoAdminContest`, `getContest` not imported in some specs |
| **T5** | TS / API misuse | `ensureRound10Active(1)` extra arg; `selectOption({ label: RegExp })` invalid |
| **T6** | Strict selectors | Banner + toast duplicate visible text → use `role=status` / `.first()` |
| **T7** | Test data design | `admin_setup` pre-fills all team slots → UI CRUD test cannot add teams |
| **T8** | Teardown isolation | `admin_pause` leaves contest PAUSED → poisons serial suite |
| **T9** | `playwright.global-setup.ts` | Read `E2E_SUPERVISOR_PASSWORD` fallback like `credentials.ts` |

**Non-goals:**

- Changing production React components (unless E2E proves real bug → report to @Coder, do not patch `src/` yourself)
- Backend changes
- Stage 2.4 features
- Visual screenshot regression

---

## 2. Root causes (from retest 2026-06-25)

| Failed test | Root cause | Fix owner |
|-------------|------------|-----------|
| `supervisor_create_round` | `gotoAdminContest` used but not imported | T4 |
| `admin_logo_upload` | `getContest` used but not imported | T4 |
| `supervisor_24h_rule`, `supervisor_active_round`, … | `ensureRound10Active(1)` — function takes 0 args | T5 |
| `admin_setup_locked`, loaded-contest specs | `ensureContestRunning` calls `resume` with supervisor token | T3 |
| `admin_pause` | Strict mode: banner + toast both match «Конкурс на паузе»; teardown uses supervisor resume | T3, T6, T8 |
| `admin_rbac` supervisor nav | Likely auth failure (password mismatch) or page not loaded | T2, T9 |
| `admin_setup` teams CRUD | `beforeEach` adds 4/4 teams via API → UI add blocked by limit | T7 |
| `admin_setup` invite | May fail if wrong contest context or form selector; verify after T7/T2 | T7 |
| `supervisor_results`, `supervisor_void_match` | Missing `gotoAdminContest` import | T4 |
| Global setup 401 | Bootstrap order / password drift | T1, T2 |

---

## 3. Correct bootstrap (mandatory before E2E)

Replace `tester_2.3.md` §2.1 order in **this fix run** (and patch parent doc in handoff):

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset   # contest id=1, clears users table
uv run python src/scripts/bootstrap_users.py          # recreates admin, supervisor, demo user
uv run python src/scripts/dev_setup.py --ensure-running-only  # id=1 RUNNING + is_locked
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

**Verify login smoke** (no password output):

```bash
uv run python -c "
import json, urllib.request, sys
sys.path.insert(0,'src')
from config.settings import get_settings
s=get_settings()
for login, pw in [(s.seed_supervisor_login, s.seed_supervisor_password), (s.seed_admin_login, s.seed_admin_password)]:
    req=urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login',
        data=json.dumps({'login':login,'password':pw}).encode(),
        headers={'Content-Type':'application/json'}, method='POST')
    try:
        urllib.request.urlopen(req)
        print(login, 'OK')
    except Exception:
        print(login, 'FAIL')
"
```

Both must print `OK` before Playwright.

### 3.1 Credentials alignment (T2)

| Source | Used by |
|--------|---------|
| Root `.env` `SEED_SUPERVISOR_PASSWORD` | `bootstrap_users.py`, `playwright.global-setup.ts` |
| `frontend/.env.local` `E2E_SUPERVISOR_PASSWORD` | `credentials.ts` (preferred in specs) |

**Rule:** Values must match what bootstrap hashed into DB. If `E2E_*` differs from `SEED_*`, either sync files or make `credentials.ts` and `global-setup.ts` use the same resolution order:

```ts
process.env.E2E_SUPERVISOR_PASSWORD ?? rootEnv.SEED_SUPERVISOR_PASSWORD ?? ""
```

Apply same for `E2E_ADMIN_PASSWORD` / `SEED_ADMIN_PASSWORD`.

---

## 4. Scope — files to create/modify

```
frontend/e2e/fixtures/adminApi.ts           # T3, T9 helpers
frontend/e2e/fixtures/credentials.ts        # optional: export adminToken helper
frontend/playwright.global-setup.ts         # T9 password fallback
frontend/e2e/supervisor_create_round.spec.ts   # T4 import gotoAdminContest
frontend/e2e/admin_logo_upload.spec.ts         # T4 import getContest
frontend/e2e/supervisor_results.spec.ts        # T4
frontend/e2e/supervisor_void_match.spec.ts     # T4
frontend/e2e/supervisor_24h_rule.spec.ts       # T5 remove arg
frontend/e2e/supervisor_active_round.spec.ts   # T5
frontend/e2e/supervisor_free_tour.spec.ts      # T5 if present
frontend/e2e/admin_pause.spec.ts               # T3, T6, T8
frontend/e2e/admin_setup.spec.ts               # T7 split setup data
frontend/e2e/admin_setup_locked.spec.ts        # T3 admin resume in beforeEach
frontend/e2e/admin_rbac.spec.ts                # T6 newsletters selector
agent_docs/instructions/tester_2.3.md          # PATCH §2.1 bootstrap order (handoff)
agent_docs/reports/test_2.3.md                 # append § Retest 2.3.1 verdict
agent_docs/progress/stage_2.md                 # append handoff
```

**Do NOT modify:** `docs/`, `src/`, `alembic/`.

---

## 5. Required fixes (detailed)

### 5.1 `adminApi.ts` — T3

Replace supervisor-based resume in `ensureContestRunning`:

```ts
export async function adminToken(): Promise<string> {
  if (!ADMIN_PASSWORD) throw new Error("SEED_ADMIN_PASSWORD missing");
  return apiLogin(ADMIN_LOGIN, ADMIN_PASSWORD);
}

export async function ensureContestRunning(contestId = 1): Promise<void> {
  const token = await adminToken();
  const contest = await getContest(token, contestId);
  if (contest.status === "PAUSED") {
    await resumeContest(token, contestId);
  }
  if (contest.status === "DRAFT") {
    // optional: call dev_setup or POST activate if needed for loaded profile
    ensureLoadedContestDevState();
  }
}
```

Export `adminToken` for specs that need explicit ADMIN API calls.

**`admin_pause.spec.ts`:** In test body, replace supervisor `resumeContest` pre-check with `adminToken()` + `resumeContest(adminToken, 1)`.

**`afterEach`:** Always resume via **admin** token, not supervisor.

### 5.2 Missing imports — T4

| File | Add to import from `./fixtures/adminApi` |
|------|------------------------------------------|
| `supervisor_create_round.spec.ts` | `gotoAdminContest` |
| `admin_logo_upload.spec.ts` | `getContest` |
| `supervisor_results.spec.ts` | `gotoAdminContest` |
| `supervisor_void_match.spec.ts` | `gotoAdminContest` |

Run `npm run type-check` — must exit **0** for `e2e/` after fixes.

### 5.3 TypeScript / Playwright API — T5

- Remove `(1)` from all `ensureRound10Active()` calls.
- Replace `selectOption({ label: /Тур 10/ })` with string label or `selectOption({ index: N })`:

```ts
// Prefer visible option text from roundStatusLabel in UI, e.g.:
await page.locator("select").first().selectOption({ label: "Тур 10 — Активен" });
// Or find by value after API knows round id
```

Inspect loaded contest round 10 status label at runtime (`ACTIVE` → «Активен» per `roundStatusLabel`).

### 5.4 Strict mode selectors — T6

| Spec | Bad | Better |
|------|-----|--------|
| `admin_pause` | `getByText("Конкурс на паузе")` | `page.getByRole("status").filter({ hasText: "Конкурс на паузе" })` |
| `admin_rbac` newsletters | `getByText(/недоступн/i)` matches LockBanner too | Scope: `page.locator("main").getByText(/недоступн/i)` or exact placeholder copy |

### 5.5 `admin_setup` team limit — T7

**Problem:** `beforeEach` calls `addTeams(token, contestId, 4)` with `total_teams: 4` → UI cannot add «Alpha FC».

**Fix (pick one):**

1. **Recommended:** Remove API `addTeams` from `[E2E-ADMIN-SETUP]` describe; let UI tests create teams. Keep API teams only for round/create specs.
2. Or: `total_teams: 8`, `addTeams(..., 2)` in beforeEach — leaves room for 2 UI adds.

Split `test.describe` if needed:

```ts
test.describe("[E2E-ADMIN-SETUP] parameters", () => { /* no addTeams */ });
test.describe("[E2E-ADMIN-SETUP] teams + invite", () => { /* total_teams: 6, addTeams 0 */ });
```

### 5.6 Test isolation — T8

- Mark `admin_pause.spec.ts` as `test.describe.serial` if sharing contest `id=1`.
- Run `ensureContestRunning(1)` in `beforeEach` **and** `afterEach` using **admin** token.
- Consider running pause test **last** in suite or use dedicated contest via API.

### 5.7 `playwright.global-setup.ts` — T9

Align password resolution with `credentials.ts`:

```ts
const supervisorPassword =
  process.env.E2E_SUPERVISOR_PASSWORD ??
  rootEnv.SEED_SUPERVISOR_PASSWORD ??
  "";
```

---

## 6. Execution order (full 2.3 re-verify)

After applying §5 fixes:

```bash
# 1. Unit (unchanged)
cd frontend && npm run test:unit

# 2. Lint toolchain
npm run lint && npm run type-check && npm run format:check

# 3. Backend up (§3 bootstrap)
# Terminal 1: uvicorn :8000

# 4. E2E — full 2.3 admin subset
npm run test:e2e -- admin_* supervisor_*

# 5. Build
npm run build
```

Prefer E2E order: **RBAC → SETUP → create_round → 24h → active → results → void → free_tour → pause (last)**.

Tear down: kill `:8000` if you started uvicorn manually.

---

## 7. Acceptance criteria (2.3.1 done)

Same matrix as `tester_2.3.md` §6–§7; all must pass:

| ID | Pass criteria |
|----|---------------|
| `[UNIT-*]` | 37+ passed |
| `[LINT-ESLINT]` `[LINT-TSC]` `[LINT-PRETTIER]` `[BUILD]` | exit 0 |
| `[E2E-ADMIN-RBAC]` | 4/4 cases |
| `[E2E-ADMIN-SETUP]` | parameters, teams, invite |
| `[E2E-ADMIN-LOCK]` | Path A + Path B |
| `[E2E-SUPERVISOR-CREATE-ROUND]` | DRAFT → activate → lock |
| `[E2E-SUPERVISOR-24H]` | 24h + newsletter stub |
| `[E2E-SUPERVISOR-ACTIVE-ROUND]` | structure frozen |
| `[E2E-SUPERVISOR-FREE-TOUR]` | POSTPONED only |
| `[E2E-SUPERVISOR-RESULTS]` | calculate → publish |
| `[E2E-SUPERVISOR-VOID]` | VOID on published + leaderboard |
| `[E2E-ADMIN-PAUSE]` | pause/resume mutations |
| `[E2E-ADMIN-LOGO]` | PASS or documented SKIP |
| `[DOC-*]` | unchanged from prior pass |
| BLOCKED.md | B7/B8 remain RESOLVED; no new B9 |

**Verdict:** `TEST_PASS` → Stage 2.3 complete → `instructions/coder_2.4.md`.

If production bug found (UI not rendering after correct test fix): append `BLOCKED.md` B9, `TEST_FAIL` with evidence.

---

## 8. Report — append to `agent_docs/reports/test_2.3.md`

Add section **§ Retest 2.3.1 fix** with updated verdict table. Reference fixed IDs T1–T9.

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3.1 fix)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.3.md § Retest 2.3.1
- Fixed: E2E fixtures T1–T9; bootstrap order in tester_2.3.md §2.1
- Unit: N passed; E2E 2.3: M/M passed
- BLOCKED.md: B7/B8 confirmed RESOLVED
- Next: instructions/coder_2.4.md
```

On **TEST_FAIL:** list failing `[E2E-*]` IDs; if Coder needed → `@Coder` with file/behavior.

---

## 9. Patch parent `tester_2.3.md` (handoff)

Update §2.1 Backend bootstrap to:

```bash
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Add note: **`bootstrap_users` after `load_test_data --reset`** — loader clears `users` table.

---

## 10. Manual UX checklist

Unchanged from `tester_2.3.md` §10 — include **REMINDER** in report; human sign-off not required for agent `TEST_PASS`.

---

## 11. Explicitly OUT OF SCOPE

- Re-implementing admin UI (`coder_2.3.md`)
- Backend migration (`coder_1.10_fix.md`) — already done
- Fixing Stage 2.2 prediction E2E
- `toHaveScreenshot()` visual regression
