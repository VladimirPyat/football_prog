# Tester Instructions — Stage 2.3.2 Fix: Loaded Contest Isolation + Credentials

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** `tester_2.3.1_fix` partial — 8/17 E2E pass; see `agent_docs/reports/test_2.3.md` § Retest 2.3.1.
> **Parent spec:** `agent_docs/instructions/tester_2.3.md`
> **Goal:** Fix remaining 9 E2E failures → full 2.3 re-run → maximize pass count; `TEST_PASS` if all green.
> **Password policy:** **Root `.env` only** — `SEED_SUPERVISOR_PASSWORD`, `SEED_ADMIN_PASSWORD`. Remove `E2E_*` overrides from Playwright/credentials.

---

## 1. Objective

| ID | Category | Summary |
|----|----------|---------|
| **U1** | Credentials | `credentials.ts` + `playwright.global-setup.ts` — passwords **only** from root `.env` `SEED_*` |
| **U2** | Loaded contest reset | `reloadLoadedContestFixture()` — full bootstrap chain before loaded-contest specs |
| **U3** | Round 10 ACTIVE | Verify round 10 status via API; reload fixture if not ACTIVE |
| **U4** | Round select by API id | `selectRoundByNumber(page, n)` — select by `round.id`, not hardcoded label |
| **U5** | Round API ids | Replace `/admin/rounds/9/` URLs with `round9.id` from `getRounds()` |
| **U6** | Admin shell wait | `waitForAdminShell(page)` after session seed |
| **U7** | Invite / lock paths | `gotoAdminContest` + wait before assertions |
| **U8** | Create round workaround | API `createDraftRound` + UI activate/lock until UI bug B9 fixed |
| **U9** | E2E order | Run `admin_pause` **last**; `beforeEach`/`afterEach` `ensureContestRunning(1)` |

**If `[E2E-SUPERVISOR-CREATE-ROUND]` still fails after U8:** append **B9** to `BLOCKED.md` (RoundBuilderForm hidden when `rounds.length === 0`).

---

## 2. Root causes (2.3.1 retest)

| Failure | Fix |
|---------|-----|
| round 10 not ACTIVE (24h, active, free_tour) | U2, U3 |
| void/results hardcoded round id `9` | U5 |
| LockBanner / invite / rbac nav timeout | U6, U7 |
| create round form not visible | U8 or B9 |
| pause — contest not RUNNING | U2, U9 |
| password drift E2E vs SEED | U1 |

---

## 3. U1 — Credentials from `.env` only

### 3.1 `frontend/e2e/fixtures/credentials.ts`

```ts
export const SUPERVISOR_PASSWORD = rootEnv.SEED_SUPERVISOR_PASSWORD ?? "";
export const ADMIN_PASSWORD = rootEnv.SEED_ADMIN_PASSWORD ?? "";
```

**Remove** `process.env.E2E_SUPERVISOR_PASSWORD` and `process.env.E2E_ADMIN_PASSWORD` fallbacks.

### 3.2 `frontend/playwright.global-setup.ts`

```ts
const supervisorPassword = rootEnv.SEED_SUPERVISOR_PASSWORD ?? "";
```

**Remove** `process.env.E2E_SUPERVISOR_PASSWORD` fallback.

### 3.3 Docs note

In handoff: E2E reads passwords from **project root `.env`** only (same as `bootstrap_users.py`). Do not document `E2E_*` in `frontend/.env.local` for auth.

---

## 4. U2 — `reloadLoadedContestFixture()`

Add to `adminApi.ts`:

```ts
export function reloadLoadedContestFixture(): void {
  execSync(
    "cd /work/football_prog && uv run python src/scripts/load_test_data.py --reset && " +
      "uv run python src/scripts/bootstrap_users.py && " +
      "uv run python src/scripts/dev_setup.py --ensure-running-only",
    { stdio: "pipe", timeout: 120_000 },
  );
}
```

Call in `beforeAll` of every describe using **loaded contest `id=1`**:

- `admin_setup_locked`
- `supervisor_24h_rule`
- `supervisor_active_round`
- `supervisor_free_tour`
- `supervisor_results`
- `supervisor_void_match`
- `admin_pause` (beforeAll + afterEach ensureContestRunning)

**Optional:** single `test.describe.configure({ mode: 'serial' })` at file level for loaded-contest files.

---

## 5. U3 — `ensureRound10Active()`

Replace stub with API verification:

```ts
export async function ensureRound10Active(contestId = 1): Promise<RoundOut> {
  ensureLoadedContestDevState();
  const token = await supervisorToken();
  let rounds = await getRounds(token, contestId);
  let round10 = rounds.find((r) => r.number === 10);
  if (!round10 || round10.status !== "ACTIVE") {
    reloadLoadedContestFixture();
    rounds = await getRounds(await supervisorToken(), contestId);
    round10 = rounds.find((r) => r.number === 10);
  }
  if (!round10 || round10.status !== "ACTIVE") {
    throw new Error(`Round 10 not ACTIVE after reload (status=${round10?.status})`);
  }
  return round10;
}
```

Export helper `roundOptionLabel(number, status)` → `Тур ${n} — ${label}` matching `roundStatusLabel` map (ACTIVE → «Активен», PUBLISHED → «Опубликован», etc.).

---

## 6. U4 — `selectRoundByNumber`

```ts
export async function selectRoundByNumber(
  page: Page,
  token: string,
  contestId: number,
  roundNumber: number,
): Promise<void> {
  const rounds = await getRounds(token, contestId);
  const round = rounds.find((r) => r.number === roundNumber);
  if (!round) throw new Error(`Round ${roundNumber} not found`);
  const roundSelect = page.locator('label:text-is("Тур:") + select');
  await roundSelect.waitFor({ state: "visible", timeout: 15_000 });
  await roundSelect.selectOption(String(round.id));
}
```

Use instead of hardcoded `selectRoundByLabel(page, "Тур 10 — Активен")` where round state may vary.

For results page, filter still applies (CLOSED/CALCULATED/PUBLISHED only) — select by id after verifying status.

---

## 7. U5 — API round ids

Replace all:

```ts
fetch(`.../admin/rounds/9/calculate`)
```

With:

```ts
const round9 = rounds.find((r) => r.number === 9)!;
fetch(`.../admin/rounds/${round9.id}/calculate`)
```

Same for `publish`, `getPublicResults(token, 1, round9.id)`.

Add helpers `calculateRound(token, contestId, roundId)`, `publishRound(...)` in `adminApi.ts`.

---

## 8. U6 — `waitForAdminShell`

```ts
import { expect } from "@playwright/test";

export async function waitForAdminShell(page: Page): Promise<void> {
  await expect(page.getByRole("link", { name: "Настройки" })).toBeVisible({
    timeout: 20_000,
  });
}
```

Call after `seedSupervisorSession` / `seedAdminSession` + `goto` in rbac, lock, invite specs.

---

## 9. U7 — Spec updates

| File | Change |
|------|--------|
| `admin_rbac.spec.ts` | After goto parameters → `waitForAdminShell` |
| `admin_setup_locked.spec.ts` | `reloadLoadedContestFixture` in beforeAll; `gotoAdminContest(1, ...)` + wait LockBanner |
| `admin_setup.spec.ts` invite | `gotoAdminContest(page, contestId, "/admin/settings/participants")` + wait heading |
| `supervisor_void_match.spec.ts` | API publish via `round9.id`; `selectRoundByNumber` for round 9 |
| `supervisor_24h_rule`, `active`, `free_tour` | `ensureRound10Active()` + `selectRoundByNumber(..., 10)` |
| `supervisor_results.spec.ts` | `round9.id` in API helpers |

---

## 10. U8 — Create round workaround

UI bug: `RoundBuilderForm` hidden when no rounds selected (`canEditRoundStructure` requires `selectedRound.status === DRAFT`).

**Test workaround (until B9 fixed):**

In `supervisor_create_round.spec.ts`:

1. `beforeAll`: fresh contest + teams (unchanged)
2. In test: **API** `createDraftRound` with 1 match, valid deadline
3. UI: `gotoAdminContest` → `/admin/rounds` → select created round in dropdown → **Активировать** → confirm
4. Assert: `ТУР АКТИВИРОВАН`, `is_locked`, LockBanner on settings

Still validates activate + lock Path A; defers UI draft builder to manual/B9.

---

## 11. U9 — Pause test isolation

- Move `admin_pause.spec.ts` to run last: rename to `z_admin_pause.spec.ts` **or** document serial order in playwright config
- `beforeEach` + `afterEach`: `ensureContestRunning(1)`
- Pre-check: `getContest(adminToken, 1).status === "RUNNING"` before clicking Пауза

---

## 12. Scope — files to modify

```
frontend/e2e/fixtures/credentials.ts
frontend/e2e/fixtures/adminApi.ts
frontend/playwright.global-setup.ts
frontend/e2e/admin_rbac.spec.ts
frontend/e2e/admin_setup_locked.spec.ts
frontend/e2e/admin_setup.spec.ts
frontend/e2e/admin_pause.spec.ts          # or z_admin_pause.spec.ts
frontend/e2e/supervisor_*.spec.ts
agent_docs/reports/test_2.3.md            # append § Retest 2.3.2
agent_docs/reports/BLOCKED.md             # B9 if create-round UI still blocked
agent_docs/progress/stage_2.md
```

**Do NOT modify:** `docs/`, `src/` (unless documenting B9 only in BLOCKED.md).

---

## 13. Execution — full Stage 2.3 re-verify

Do **not** ask user for confirmation.

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run uvicorn main:app --host 127.0.0.1 --port 8000  # background

cd frontend
npm run test:unit
npm run lint && npm run type-check && npm run format:check
npm run test:e2e -- admin_* supervisor_* z_admin_*
npm run build
```

Tear down `:8000` after tests.

Compare E2E pass count vs 2.3.1 (8/17) in report.

---

## 14. Acceptance & report

Append **§ Retest 2.3.2** to `test_2.3.md` with verdict table.

Handoff in `stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3.2 fix)
- STATUS: TEST_PASS | TEST_FAIL
- E2E: X/17 passed (was 8/17)
- Fixed: U1–U9; credentials from root .env only
- B9: OPEN | N/A
- Next: coder_2.4 | coder_2.3_ui_fix | tester_2.3.3
```

**TEST_PASS** when all §7 matrix from `tester_2.3.md` green.

---

## 15. Explicitly OUT OF SCOPE

- Fixing `RoundBuilderForm` in `src/` (B9 → @Coder)
- Stage 2.4 features
- Backend changes
