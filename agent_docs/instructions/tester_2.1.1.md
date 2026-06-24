# Tester Instructions — Stage 2.1.1: Role-Based Routing Hotfix + Dev Bootstrap Demo User + Admin Stubs

> **Status gate:** @Coder `READY_FOR_TEST` for 2.1.1 in `agent_docs/progress/stage_2.md`.
> **Prerequisite:** Sub-stage **2.1** at `TEST_PASS`. **Local env:** [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md).
> **Reference:** `instructions/coder_2.1.1.md`, `instructions/coder_2.1.md`, `agent_docs/contracts/frontend_api_integration.md` § Post-login routing.
> **Strategy:** Unit (Vitest) + E2E (Playwright) — **agent runs**; visual/mobile UX — **human** (agent reminds in report).

---

## 1. Objective

Verify Stage **2.1.1** deliverables:

1. **Unit tests** — `resolvePostLoginPath` for each role + temp password (`npm run test:unit`).
2. **E2E (Playwright)** — role-based post-login routing; `/profile` USER-only; admin stubs reachable; supervisor blocked from profile.
3. **Bootstrap smoke** — `dev_setup.py` creates working `user/user` (API login 200).
4. **Lint & build** — ESLint, TypeScript `type-check`, Prettier `format:check`, `npm run build`.
5. **Docs** — Coder updated living UI specs (§9 of `coder_2.1.1.md`).

**Non-goals (later sub-stages):**

- Full admin CRUD (participants invite, rounds) → **2.3**
- Prediction form E2E → **2.2**
- `CONTEST_LOCKED` invite fix on contest `1` → **2.3** (use DRAFT contest for invite tests)
- Regression of 2.1 contacts/discovery flows — spot-check only if time permits

---

## 2. Test environment

**Setup guide:** [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md)

### 2.1 Backend (Terminal 1)

```bash
cd /work/football_prog
cp .env.example .env                              # once; set SEED_* passwords
uv run python src/scripts/dev_setup.py            # migrations + loader + bootstrap (incl. demo user)
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Bootstrap verification (before E2E):**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"user","password":"user"}' | jq -e '.access_token'
```

Expected: exit 0, non-empty `access_token`. If FAIL → report `[ENV-DEMO-USER]` blocker for @Coder.

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

### 2.2 Frontend env

`frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

### 2.3 Credentials

| Role | Login | Password source |
|------|-------|-----------------|
| USER (demo) | `user` | `user` — **bootstrap** (`SEED_DEMO_USER_*`), not loader CSV |
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` from root `.env` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` from root `.env` |

Do **not** commit passwords.

### 2.4 Playwright

Same as `tester_2.1.md` §2.4: `webServer` on `:3000`, `baseURL` `http://127.0.0.1:3000`. Both `:8000` and `:3000` must be up.

---

## 3. Scope — files you may create/modify

```
frontend/e2e/
  auth_role_routing.spec.ts           # NEW — primary 2.1.1 E2E
  auth_profile_user_only.spec.ts      # NEW — supervisor redirect from /profile
  staff_login.spec.ts                 # NEW (optional if /staff/login implemented)
frontend/e2e/fixtures/auth.ts         # extend login helpers per role
agent_docs/reports/test_2.1.1.md      # NEW — verdict report
```

You may **extend** Coder's Vitest files if coverage gaps found (document in report).

**Do NOT modify:** `docs/`, Python `src/` unless reporting bootstrap bugs as blockers.

---

## 4. Unit tests (Vitest) — mandatory

Run from `frontend/`:

```bash
npm run test:unit
```

| ID | File | Pass criteria |
|----|------|---------------|
| `[UNIT-RESOLVE-TEMP]` | `resolvePostLoginPath.test.ts` | `is_temp_password=true` → `/change-password` |
| `[UNIT-RESOLVE-USER]` | same | USER → `/profile` |
| `[UNIT-RESOLVE-SUPERVISOR]` | same | SUPERVISOR → `/admin/settings/parameters` |
| `[UNIT-RESOLVE-ADMIN]` | same | ADMIN → `/admin` |

If Coder omitted tests → **FAIL** @Coder.

---

## 5. E2E tests (Playwright) — mandatory

### 5.1 `auth_role_routing.spec.ts`

| ID | Steps | Assert |
|----|-------|--------|
| `[E2E-USER-LOGIN-PROFILE]` | Login `user`/`user` via UI | URL matches `/profile`; header shows «Личный кабинет»; **no** `/admin` |
| `[E2E-SUPERVISOR-LOGIN-ADMIN]` | Login `supervisor`/env password | URL matches `/admin` or `/admin/settings/parameters`; **not** `/profile` |
| `[E2E-ADMIN-LOGIN-ADMIN]` | Login `admin`/env password | URL matches `/admin`; stub dashboard visible (heading or placeholder text) |
| `[E2E-HOME-USER]` | Login as USER, goto `/` | Lands on participant flow (`/contests` or contest page), not `/admin` |
| `[E2E-HOME-STAFF]` | Login as SUPERVISOR, goto `/` | Redirected to `/admin` |

Use `page.waitForURL` with regex; allow query strings.

### 5.2 `auth_profile_user_only.spec.ts`

| ID | Steps | Assert |
|----|-------|--------|
| `[E2E-SUPERVISOR-NO-PROFILE]` | Login supervisor → navigate `/profile` | Redirected to `/admin` (or settings stub); profile hub not shown |
| `[E2E-USER-PROFILE-OK]` | Login user → `/profile` | Profile hub renders (heading «Личный кабинет») |

### 5.3 `staff_login.spec.ts` (if route exists)

| ID | Steps | Assert |
|----|-------|--------|
| `[E2E-STAFF-LOGIN-PAGE]` | Open `/staff/login`, login supervisor | Same redirect as modal login → `/admin/*` |

If Coder skipped `/staff/login` → mark `[E2E-STAFF-LOGIN-PAGE]` **SKIP** (non-blocking).

### 5.4 Regression spot-check (optional, non-blocking)

| ID | Note |
|----|------|
| `[E2E-REGRESS-LOGOUT]` | Re-run one logout spec from 2.1 if quick |
| `[E2E-REGRESS-CONTACTS]` | USER profile contacts still loads |

---

## 6. Lint & build — mandatory

From `frontend/`:

```bash
npm run lint && npm run type-check && npm run format:check && npm run build
```

| ID | Pass criteria |
|----|---------------|
| `[LINT-ESLINT]` | exit 0 |
| `[LINT-TSC]` | exit 0 |
| `[LINT-PRETTIER]` | exit 0 |
| `[BUILD]` | exit 0 |

---

## 7. Documentation audit (read-only)

| ID | Pass criteria |
|----|---------------|
| `[DOC-UI-PAGES]` | `pages.md` — `/admin` stubs, `/profile` USER-only, `/staff/login` noted |
| `[DOC-INTEGRATION]` | `frontend_api_integration.md` — § Post-login routing present |
| `[DOC-DEV-SETUP]` | `DEV_SETUP.md` — `user/user` sourced from bootstrap, not loader |
| `[DOC-TODO]` | `todo.md` — demo user removal after 2.3; CONTEST_LOCKED note |
| `[DOC-CODER-HANDOFF]` | `stage_2.md` has Coder 2.1.1 `READY_FOR_TEST` |

---

## 8. Manual checklist — human developer (agent reminds)

Include in `test_2.1.1.md`:

> Разработчик должен вручную проверить перед релизом 2.1.1:
> - [ ] AppShell: USER видит «Личный кабинет»; SUPERVISOR/ADMIN — «Управление»
> - [ ] AdminTopNav stub: вкладки видны, disabled/«Скоро 2.3»
> - [ ] Footer ссылка «Вход для организаторов» (если реализована)
> - [ ] Смена пароля (temp) → редирект по роли, не всегда `/profile`

Agent verdict **TEST_PASS** does not require manual checklist completion.

---

## 9. Execution order

```bash
# 0. API bootstrap smoke
curl login user/user

# 1. Unit
cd frontend && npm run test:unit

# 2. Lint
npm run lint && npm run type-check && npm run format:check

# 3. E2E
npm run test:e2e

# 4. Build
npm run build

# 5. Doc audit
```

---

## 10. Report template — `agent_docs/reports/test_2.1.1.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[ENV-DEMO-USER]` | PASS/FAIL | API curl user/user |
| `[UNIT-RESOLVE-*]` | PASS/FAIL | |
| `[E2E-USER-LOGIN-PROFILE]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-LOGIN-ADMIN]` | PASS/FAIL | |
| `[E2E-ADMIN-LOGIN-ADMIN]` | PASS/FAIL | |
| `[E2E-HOME-USER]` | PASS/FAIL | |
| `[E2E-HOME-STAFF]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-NO-PROFILE]` | PASS/FAIL | |
| `[E2E-USER-PROFILE-OK]` | PASS/FAIL | |
| `[E2E-STAFF-LOGIN-PAGE]` | PASS/FAIL/SKIP | |
| `[LINT-*]` | PASS/FAIL | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Manual checklist | REMINDER | |

**Verdict:** `TEST_PASS` / `TEST_FAIL` with blockers for @Coder.

On **TEST_PASS:**

- Stage 2.1.1 complete; unblock **2.3** (admin UI) and **2.2** (predictions) per dependency graph: `2.1 → 2.1.1 → 2.3 → 2.2 → 2.4`.
- Note: invite E2E in 2.3 must use DRAFT contest (`CONTEST_LOCKED` on contest `1`).

---

## 11. Handoff

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.1.1)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.1.1.md
- Unit: N passed; E2E: N passed (M skipped)
- Bootstrap: user/user API login OK
- Next: coder_2.3.md (admin UI), then coder_2.2.md (predictions)
```

On **TEST_FAIL:** status `TEST_FAIL`, list blockers; do not advance dependency chain.

---

## 12. Acceptance mapping (Coder §10)

| Coder criterion | Tester ID |
|-----------------|-----------|
| user/user → /profile | `[E2E-USER-LOGIN-PROFILE]`, `[ENV-DEMO-USER]` |
| supervisor → /admin | `[E2E-SUPERVISOR-LOGIN-ADMIN]` |
| admin → /admin stub | `[E2E-ADMIN-LOGIN-ADMIN]` |
| supervisor cannot stay on /profile | `[E2E-SUPERVISOR-NO-PROFILE]` |
| resolvePostLoginPath unit tests | `[UNIT-RESOLVE-*]` |
| lint/build | `[LINT-*]`, `[BUILD]` |
