# Tester Instructions — Stage 2.1: Foundation, Auth & Profile Shell

> **Status gate:** @Coder `READY_FOR_TEST` for 2.1 in `agent_docs/progress/stage_2.md`.
> **Prerequisite:** Backend Stage 1.8+ at `TEST_PASS`. **Local env:** [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md). See `agent_docs/reports/BLOCKED.md`.
> **Reference:** `instructions/coder_2.1.md`, `docs/06_front_tests.md`, `agent_docs/contracts/frontend_api_integration.md`.
> **Strategy:** Unit (Vitest) + E2E (Playwright) — **agent runs**; visual/mobile UX — **human** (agent reminds in report).

---

## 1. Objective

Verify Stage **2.1** frontend deliverables:

1. **Unit tests** — validation, API error parser, default contest id helper (`npm run test:unit`).
2. **E2E smoke (Playwright)** — auth, discovery, profile contacts, RBAC guards, 401 logout, temp password.
3. **Lint & build** — ESLint, TypeScript `type-check`, Prettier `format:check`, `npm run build` (all exit 0).
4. **Docs** — Coder updated living UI specs (§11 of `coder_2.1.md`).

**Non-goals (later sub-stages):**

- Prediction form, batch validation, privacy matrix → **2.2**
- Leaderboard / Results tabbed UI → **2.4**
- Admin `/admin/*` → **2.3**
- Full E2E from `docs/06_front_tests.md` (`prediction_validation`, `supervisor_create_round`, …) → **2.2+**
- Visual pixel-perfect match to screenshots (partial shell only in 2.1) → **manual human**

---

## 2. Test environment

**Setup guide:** [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md)

### 2.1 Backend (Terminal 1)

```bash
cd /work/football_prog
cp .env.example .env                              # once; set SEED_* passwords
uv run python src/scripts/dev_setup.py            # migrations + loader + bootstrap + RUNNING contest
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Equivalent manual order (if not using script):

```bash
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py      # AFTER loader (loader wipes users)
uv run python src/scripts/dev_setup.py --ensure-running-only
```

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

Public discovery smoke: `curl -s http://127.0.0.1:8000/api/v1/contests/public` → non-empty (contest `1` RUNNING).

### 2.2 Frontend env

`frontend/.env.local` (copy from `.env.local.example`):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

### 2.3 Credentials

| Role | Login | Password source |
|------|-------|-----------------|
| USER | `user` | `user` (loader) |
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` from root `.env` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` from root `.env` |
| Temp-password user | create via invite flow or conftest pattern | returned `temp_password` |

Do **not** commit passwords. Read from local `.env` / test setup only.

### 2.4 Playwright `webServer`

`frontend/playwright.config.ts` should start Next.js dev server (or use `npm run dev` manually if Coder did not wire webServer yet):

```ts
webServer: {
  command: 'npm run dev',
  url: 'http://127.0.0.1:3000',
  reuseExistingServer: !process.env.CI,
},
use: { baseURL: 'http://127.0.0.1:3000' },
```

**Both** `:8000` (API) and `:3000` (UI) must be up for E2E.

---

## 3. Scope — files you may create/modify

```
frontend/playwright.config.ts           # if missing
frontend/e2e/
  auth_login_profile.spec.ts            # NEW
  auth_logout.spec.ts                   # NEW
  auth_temp_password.spec.ts            # NEW
  auth_401_logout.spec.ts               # NEW
  visitor_discovery.spec.ts             # NEW
  user_contests.spec.ts                 # NEW
  supervisor_contest_picker.spec.ts   # NEW
  profile_contacts.spec.ts              # NEW
  rbac_guards.spec.ts                   # NEW
  fallback_default_contest.spec.ts      # NEW (optional)
frontend/e2e/fixtures/auth.ts           # shared login helpers (optional)
agent_docs/reports/test_2.1.md          # NEW — verdict report
```

You may **extend** Coder's Vitest files if coverage gaps found (document in report).

**Do NOT modify:** `docs/`, Python `src/` (backend bugs → report as blockers).

---

## 4. Unit tests (Vitest) — mandatory

Run from `frontend/`:

```bash
npm run test:unit
```

### 4.1 Required coverage (Coder or Tester adds tests)

| ID | Target | Assert |
|----|--------|--------|
| `[UNIT-LOGIN-SCHEMA]` | `lib/validation/login.ts` | Empty login/password rejected by Zod |
| `[UNIT-CONTACTS-SCHEMA]` | `lib/validation/contacts.ts` | Invalid email rejected; empty email allowed |
| `[UNIT-CHANGE-PW]` | `lib/validation/changePassword.ts` | Mismatch confirm → error; min length |
| `[UNIT-DEFAULT-CONTEST]` | `lib/contest/resolveDefaultContestId.ts` | Valid env → number; invalid → throws |
| `[UNIT-API-ERROR]` | `lib/api/client.ts` or `errors.ts` | Non-OK JSON → `AppError` with `detail`; optional `code` |
| `[UNIT-401-EVENT]` | API client | 401 response dispatches `fp:unauthorized` (mock `fetch` + `localStorage`) |

**Pass:** all tests green, zero failures.

If Coder omitted files — add minimal tests yourself and note in report.

---

## 5. E2E tests (Playwright) — mandatory smoke

Use real API (no route mocks for happy paths). Selectors: prefer `getByRole`, `getByLabel`, Russian visible text from specs.

### 5.1 `[E2E-LOGIN-PROFILE]` — `auth_login_profile.spec.ts`

1. Visit `/` as Visitor — button **Вход** visible.
2. Click **Вход** → modal opens.
3. Fill login `user`, password `user` → submit.
4. Assert redirect to **`/profile`** (or `/profile` reachable within 5s).
5. Header shows user identity (login or name), not **Вход**.
6. Link **Личный кабинет** present.

### 5.2 `[E2E-LOGOUT]` — `auth_logout.spec.ts`

1. Login as `user/user`.
2. Click **Выйти**.
3. Assert URL `/` (or home).
4. **Вход** visible again.
5. `localStorage.getItem('fp_access_token')` is null.

### 5.3 `[E2E-401-LOGOUT]` — `auth_401_logout.spec.ts`

1. Login as `user/user`.
2. Set invalid token: `localStorage.setItem('fp_access_token', 'invalid.jwt.token')`.
3. Navigate to `/profile` (triggers `GET /auth/me` → 401).
4. Assert Visitor state: **Вход** visible; token cleared.
5. Optional: toast or silent logout — either OK if token cleared.

### 5.4 `[E2E-TEMP-PASSWORD]` — `auth_temp_password.spec.ts`

Setup: invite participant via API (supervisor token) **or** use pre-seeded temp user if Coder documented one.

1. Login with temp password → redirect **`/change-password`** (not `/profile`).
2. Attempt `/profile` → redirected back to `/change-password`.
3. Submit new password (valid, confirm match) → redirect `/profile`.
4. `GET /auth/me` equivalent: header shows normal authenticated state.

Skip with `[SKIP-NO-TEMP-USER]` in report if no temp user available — mark **manual required**.

### 5.5 `[E2E-VISITOR-DISCOVERY]` — `visitor_discovery.spec.ts`

1. Clear storage; visit `/` without auth.
2. Assert public contest list OR redirect to `/contest/{id}` when list uses fallback.
3. If list UI: at least one contest name visible (RUNNING contest from loader).
4. Click contest → navigates to `/contest/{id}` placeholder page.

Cross-check API: `GET /api/v1/contests/public` returns RUNNING contests only.

### 5.6 `[E2E-USER-CONTESTS]` — `user_contests.spec.ts`

1. Login as `user/user`.
2. Visit `/contests`.
3. Assert enrolled contest(s) listed (from `GET /me/contests`).
4. Click row → `/contest/{id}`.

### 5.7 `[E2E-SUPERVISOR-PICKER]` — `supervisor_contest_picker.spec.ts`

1. Login as supervisor.
2. Assert **contest switcher** (`ContestPicker`) visible in header (SUPERVISOR+).
3. Dropdown/list contains at least one contest (from `GET /contests`).
4. Selecting contest updates route or active contest context (`fp_active_contest_id` in localStorage optional check).

### 5.8 `[E2E-PROFILE-CONTACTS]` — `profile_contacts.spec.ts`

1. Login as `user/user` → `/profile`.
2. Contacts section visible (email / VK / TG / notify).
3. PATCH flow: change `vk_id` or toggle notify → Save → success toast or persisted value after reload.
4. GET after reload reflects change.

### 5.9 `[E2E-RBAC-GUARDS]` — `rbac_guards.spec.ts`

1. Visitor → `/profile` → blocked (redirect home or login prompt; must not show profile content).
2. Visitor → `/contests` → blocked.
3. Authenticated user → `/profile` → 200 content.

### 5.10 `[E2E-CORS-SMOKE]` — (in `auth_login_profile` or separate)

During login flow, assert **no** browser console CORS errors. Playwright:

```ts
page.on('console', msg => {
  if (msg.text().includes('CORS') || msg.text().includes('Access-Control')) failures.push(msg.text());
});
```

Alternatively manual-only if flaky — document in report.

### 5.11 `[E2E-FALLBACK-DEFAULT]` — `fallback_default_contest.spec.ts` (optional)

Requires env `NEXT_PUBLIC_DEFAULT_CONTEST_ID=1` and empty public list scenario (hard to setup) — **optional**.

If implemented: when `/contests/public` returns `[]`, home redirects to `/contest/1`.

---

## 6. TypeScript lint & build (mandatory)

**Tooling** (Coder 2.1 wires `package.json` scripts; re-run every stage):

```bash
cd frontend
npm run lint           # ESLint — code style, React patterns
npm run type-check     # TypeScript — tsc, no emit
npm run format:check   # Prettier — check-only (no write)
npm run build          # Next.js production build
```

Optional smoke (if Coder added): `npm run test:lint` or `frontend/tests/test_linting.ts`.

| ID | Command | Pass criteria |
|----|---------|---------------|
| `[LINT-ESLINT]` | `npm run lint` | exit 0; ESLint **errors** = FAIL; warnings noted in report |
| `[LINT-TSC]` | `npm run type-check` | exit 0 |
| `[LINT-PRETTIER]` | `npm run format:check` | exit 0 |
| `[BUILD]` | `npm run build` | exit 0 |

Missing script → **FAIL** for @Coder (all four commands expected from 2.1 scaffold).

---

## 7. Documentation audit (read-only)

| ID | Pass criteria |
|----|---------------|
| `[DOC-UI-COMPONENTS]` | `agent_docs/ui/components.md` — 2.1 components marked implemented + paths |
| `[DOC-UI-PAGES]` | `agent_docs/ui/pages.md` — routes `/`, `/contests`, `/profile`, `/change-password` marked ✅ |
| `[DOC-INTEGRATION]` | `frontend_api_integration.md` update log mentions 2.1 if quirks found |
| `[DOC-CODER-HANDOFF]` | `agent_docs/progress/stage_2.md` has Coder 2.1 `READY_FOR_TEST` entry |

---

## 8. Manual checklist — human developer (agent reminds, does NOT execute)

Per `docs/06_front_tests.md` — **not automated in 2.1**. Include this block in `test_2.1.md` report:

> Разработчик должен вручную проверить перед релизом 2.1:
> - [ ] Визуальное соответствие header/footer скринам `user_*.jpg` (brand, кнопки, footer)
> - [ ] Навигация: все ссылки профиля кликабельны или помечены как stub
> - [ ] Ошибки форм login/contacts отображаются под полями / toast
> - [ ] Состояния кнопок (disabled Save при readonly contacts)
> - [ ] Мобильная ширина ~375px — header не ломается, списки читаемы

Agent verdict **TEST_PASS** does not require manual checklist completion — only that reminder is present.

---

## 9. Execution order

```bash
# 1. Unit
cd frontend && npm run test:unit

# 2. Lint
npm run lint && npm run type-check && npm run format:check

# 3. E2E (backend must be running)
npm run test:e2e          # or: npx playwright test

# 4. Build
npm run build

# 5. Doc audit (read files)
```

Add `package.json` script if missing:

```json
"test:e2e": "playwright test"
```

---

## 10. Report template — `agent_docs/reports/test_2.1.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-*]` | PASS/FAIL/SKIP | count: N passed |
| `[E2E-LOGIN-PROFILE]` | PASS/FAIL | |
| `[E2E-LOGOUT]` | PASS/FAIL | |
| `[E2E-401-LOGOUT]` | PASS/FAIL | |
| `[E2E-TEMP-PASSWORD]` | PASS/FAIL/SKIP | |
| `[E2E-VISITOR-DISCOVERY]` | PASS/FAIL | |
| `[E2E-USER-CONTESTS]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-PICKER]` | PASS/FAIL | |
| `[E2E-PROFILE-CONTACTS]` | PASS/FAIL | |
| `[E2E-RBAC-GUARDS]` | PASS/FAIL | |
| `[E2E-CORS-SMOKE]` | PASS/FAIL/MANUAL | |
| `[LINT-ESLINT]` | PASS/FAIL | warnings: … |
| `[LINT-TSC]` | PASS/FAIL | |
| `[LINT-PRETTIER]` | PASS/FAIL | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Manual checklist | REMINDER | link to §8 |

**Verdict:** `TEST_PASS` / `TEST_FAIL` with blockers for @Coder.

On **TEST_PASS:**

- Stage 2.1 frontend ready for 2.2 (predictions).
- Note any skipped tests and manual follow-ups.

---

## 11. Acceptance mapping (Coder §12)

| Coder criterion | Test ID |
|-----------------|---------|
| `user/user` login → profile | `[E2E-LOGIN-PROFILE]` |
| Supervisor contest switcher | `[E2E-SUPERVISOR-PICKER]` |
| 401 → auto logout | `[E2E-401-LOGOUT]` |
| Temp password gate | `[E2E-TEMP-PASSWORD]` |
| CORS :3000 ↔ :8000 | `[E2E-CORS-SMOKE]` / login E2E |
| Visitor public list | `[E2E-VISITOR-DISCOVERY]` |
| User `/contests` | `[E2E-USER-CONTESTS]` |
| Contacts GET/PATCH | `[E2E-PROFILE-CONTACTS]` |
| `npm run test:unit` | `[UNIT-*]` |
| Lint toolchain | `[LINT-ESLINT]`, `[LINT-TSC]`, `[LINT-PRETTIER]` |
| `npm run build` | `[BUILD]` |

---

## 12. Progress update

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.1)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.1.md
- Unit: N passed; E2E: M passed (K skipped)
- Build: OK
- Manual UX checklist: reminded in report §8
- Next: instructions/coder_2.2.md
```

On **TEST_FAIL**, append `STATUS: TEST_FAIL` with `[TEST-ID]` blockers.

---

## 13. Explicitly OUT OF SCOPE

- `[E2E-PREDICT-*]`, `[E2E-DEADLINE-*]`, `[E2E-PRIVACY-*]` → 2.2
- `[E2E-LEADERBOARD-*]`, `[E2E-RESULTS-*]` → 2.4
- `[E2E-ADMIN-*]`, `[E2E-SUPERVISOR-ROUND-*]` → 2.3
- Visual regression `toHaveScreenshot()` vs `docs/screens/` (full matrices not in 2.1)
- Backend API regression (covered by Stage 1.8 tests)

---

## 14. Example Playwright helper (optional)

```ts
// frontend/e2e/fixtures/auth.ts
import { Page } from '@playwright/test';

export async function login(page: Page, login: string, password: string) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Вход' }).click();
  await page.getByLabel(/логин/i).fill(login);
  await page.getByLabel(/пароль/i).fill(password);
  await page.getByRole('button', { name: /войти|вход/i }).click();
}
```

Adjust selectors to match Coder's actual labels.
