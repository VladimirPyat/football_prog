# Coder Instructions — Stage 2.1.1: Role-Based Routing Hotfix + Dev Bootstrap Demo User + Admin Stubs

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Sub-stage **2.1** at `TEST_PASS` (auth shell + profile). See `agent_docs/progress/stage_2.md`.
> **Plan:** `agent_docs/plans/draft_2.md` § Sub-stage 2.1.1.
> **Specs:** `agent_docs/ui/{components,pages,state_management}.md`, `agent_docs/contracts/frontend_api_integration.md` § Post-login routing.
> **Language policy:** UI copy Russian; code comments English; API `detail` shown as-is.

---

## 1. Objective

Fix the **post-login routing bug** (all roles land on `/profile`) and add minimal **admin shell stubs** so SUPERVISOR/ADMIN have a correct landing zone before full admin UI (2.3). Add a **bootstrap demo USER** so `user/user` works after `dev_setup.py` without E2E workarounds.

| Deliverable | Description |
|-------------|-------------|
| `resolvePostLoginPath` | Single resolver: temp password → role-based destination |
| `AuthProvider` | Use resolver after login and after change-password |
| `/profile` | **USER-only** hub; SUPERVISOR+/ADMIN redirected to `/admin` |
| `/` home | Authenticated USER → participant flow; SUPERVISOR+/ADMIN → `/admin` |
| `/admin/*` stubs | Layout + dashboard + settings parameters placeholder |
| `/staff/login` (recommended) | Same `LoginForm` + API; staff-oriented copy |
| `AppShell` | «Личный кабинет» for USER only; staff see «Управление» → `/admin` |
| Demo USER bootstrap | `user/user` in `bootstrap_users.py`; enrolled contest `id=1` ACCEPTED |
| Living docs | Update per §11 pattern from `coder_2.1.md` |

**Non-goals (later sub-stages):**

- Full admin CRUD UI → **2.3**
- Prediction form / privacy matrix → **2.2**
- New backend API endpoints
- Mock API data
- Fixing `CONTEST_LOCKED` for invite E2E on contest `id=1` (document only; see §3.4)

---

## 2. Background & known bugs

### 2.1 Current bug

`frontend/src/providers/AuthProvider.tsx` hardcodes `router.push("/profile")` after login and change-password (lines 84–88, 101). SUPERVISOR/ADMIN incorrectly land on the participant profile hub.

### 2.2 `[ENV-LOADER-AUTH]` (test_2.1.md)

`load_test_data.py --reset` loads CSV users with placeholder password hashes — `user/user` login fails. Stage 2.1 E2E used API provisioning workarounds. **2.1.1 fixes this** by seeding a real demo USER in `bootstrap_users.py` (runs after loader in `dev_setup.py`).

### 2.3 Prerequisites (verify before coding)

| Tool | Required |
|------|----------|
| Stage 2.1 | `TEST_PASS` in `stage_2.md` |
| Backend | `uv run python src/scripts/dev_setup.py` |
| Frontend | `cd frontend && npm run dev` on `:3000` |

Test logins after fix: `user/user`, `supervisor/SEED_SUPERVISOR_PASSWORD`, `admin/SEED_ADMIN_PASSWORD`.

---

## 3. Backend / dev bootstrap

### 3.1 Demo USER in `bootstrap_users.py`

Add `seed_demo_user()` and call it from `run_bootstrap()` **after** `seed_supervisor_user()`.

| Field | Value |
|-------|-------|
| Login | `settings.seed_demo_user_login` (default `"user"`) |
| Password | `settings.seed_demo_user_password` (default `"user"`) — hash at runtime |
| Role | `UserRole.USER` |
| `is_temp_password` | `false` |
| Names | sensible defaults (e.g. `Demo` / `User`) |
| Contest enrollment | contest `id=1` (first contest), `ParticipantStatus.ACCEPTED` |

**Idempotency:** if user with login already exists → skip create; ensure participant row exists.

**TEMPORARY marker (mandatory):**

```python
# TEMPORARY (2.1.1): remove after Stage 2.3 when supervisor invite UI seeds participants.
# Tracked in agent_docs/reports/todo.md
```

### 3.2 `config/settings.py`

Add optional env-backed fields (mirror existing `seed_admin_*` pattern):

```python
seed_demo_user_login: str = "user"
seed_demo_user_password: str | None = "user"  # default plaintext; hash at bootstrap
```

If password is `None`, skip demo user (log info) — same pattern as supervisor optional seed.

### 3.3 `.env.example`

Append (commented or with placeholder):

```bash
# Demo participant for dev/E2E (bootstrap_users.py) — TEMPORARY until 2.3 invite UI
# SEED_DEMO_USER_LOGIN=user
# SEED_DEMO_USER_PASSWORD=user
```

Document that defaults work without setting these vars.

### 3.4 `manuals/DEV_SETUP.md`

Update **Test logins** table:

| Role | Login | Password | Source |
|------|-------|----------|--------|
| USER (demo) | `user` | `user` | `bootstrap_users.py` (`SEED_DEMO_USER_*`) |

Remove or footnote the incorrect claim that `user/user` comes from loader CSV.

Add troubleshooting row: if `user/user` fails → re-run `dev_setup.py` (bootstrap after loader).

### 3.5 `CONTEST_LOCKED` note (doc only — do not fix in 2.1.1 unless trivial)

After `dev_setup.py`, contest `id=1` is **RUNNING** and **`is_locked=true`**. Supervisor invite (`POST …/participants`) returns `403 CONTEST_LOCKED` on locked contests.

**For 2.3 tester:** invite E2E should use a **fresh DRAFT contest** (`POST /api/v1/contests`) or a documented dev flag — not contest `1`. Append note to `agent_docs/reports/todo.md` (Planner provides text; Coder may add one sentence in `tester_2.3.md` cross-ref if editing docs).

**Out of scope for 2.1.1:** backend flag to unlock contest `1` for invites.

---

## 4. Scope — files you may create/modify

```
src/scripts/bootstrap_users.py          # seed_demo_user + run_bootstrap call
config/settings.py                      # SEED_DEMO_USER_* fields
.env.example                            # optional demo user vars
manuals/DEV_SETUP.md                    # test logins table fix

frontend/src/lib/auth/
  resolvePostLoginPath.ts               # NEW — pure function + unit tests
  resolvePostLoginPath.test.ts          # NEW
frontend/src/providers/AuthProvider.tsx # use resolver
frontend/src/components/auth/ProtectedRoute.tsx  # role redirects; change-password success path
frontend/src/components/layout/AppShell.tsx      # role-aware nav links
frontend/src/app/page.tsx               # role-based authenticated redirect
frontend/src/app/profile/page.tsx       # USER-only guard
frontend/src/app/admin/
  layout.tsx                            # NEW — ProtectedRoute SUPERVISOR+; AdminTopNav stub
  page.tsx                              # NEW — ADMIN dashboard stub; SUPERVISOR redirect
  settings/parameters/page.tsx          # NEW — supervisor stub
frontend/src/app/staff/login/page.tsx   # NEW (recommended) — staff LoginForm page
frontend/src/components/admin/
  AdminTopNav.tsx                       # NEW — stub tabs (disabled / «Скоро 2.3»)

agent_docs/ui/{pages,components,state_management}.md   # living docs §11
agent_docs/contracts/frontend_api_integration.md       # verify § Post-login routing (Planner updated)
agent_docs/reports/todo.md                             # append only if Coder adds cross-ref (Planner pre-filled)
agent_docs/progress/stage_2.md                         # handoff §14
```

**Do NOT modify:** `docs/`, prediction/admin business logic beyond stubs.

---

## 5. `resolvePostLoginPath` — contract

**File:** `frontend/src/lib/auth/resolvePostLoginPath.ts`

Pure function — no React, no router:

```ts
import type { UserOut } from "@/types/api";

export function resolvePostLoginPath(user: Pick<UserOut, "role" | "is_temp_password">): string {
  if (user.is_temp_password) return "/change-password";
  switch (user.role) {
    case "USER":
      return "/profile"; // or "/contests" — prefer /profile per pages.md
    case "SUPERVISOR":
      return "/admin/settings/parameters"; // landing; /admin also OK with redirect
    case "ADMIN":
      return "/admin";
    default:
      return "/";
  }
}
```

**Call sites (mandatory):**

1. `AuthProvider.login` — after `refreshUser()`, `router.push(resolvePostLoginPath(me))`
2. `AuthProvider.changePassword` — after success, same resolver (not hardcoded `/profile`)
3. `ProtectedRoute` — when authenticated user on `/change-password` with `!is_temp_password`, redirect via resolver (not hardcoded `/profile`)

Export for unit tests and any future OAuth callback.

---

## 6. Route guards & redirects

### 6.1 `/profile` — USER primary

Wrap content with `ProtectedRoute requireAuth requireRole="USER" requireNotTempPassword`.

When SUPERVISOR or ADMIN hits `/profile` directly → `router.replace("/admin")` (in `ProtectedRoute` or page-level effect). Do **not** show profile contacts to staff.

### 6.2 `/` home — `page.tsx`

Current code redirects all authenticated users to `/contests`. Change to:

| Role | Authenticated behaviour |
|------|-------------------------|
| USER | Keep participant flow → `/contests` (or last contest) |
| SUPERVISOR, ADMIN | `router.replace("/admin")` |

Visitors unchanged (public contest discovery).

### 6.3 `/admin/layout.tsx`

- `ProtectedRoute requireAuth requireRole="SUPERVISOR" requireNotTempPassword`
- Render `AdminTopNav` stub + `{children}`
- USER attempting `/admin/*` → redirect `/` or `/profile` with toast optional

### 6.4 `/admin/page.tsx`

- **ADMIN:** dashboard stub — heading «Панель администратора», disabled/placeholder links: «Жизненный цикл», «Пользователи», «Настройки конкурса» with note «Скоро — этап 2.3»
- **SUPERVISOR:** `redirect("/admin/settings/parameters")` (server `redirect()` or client `useEffect`)

### 6.5 `/admin/settings/parameters/page.tsx`

Stub only:

- Title: «Управление конкурсом»
- Body: «Полный интерфейс настроек — этап 2.3»
- Optional: read-only `GET /contests/{id}` name display if `ContestProvider` already has active contest

### 6.6 `AdminTopNav.tsx` (stub)

Match future 2.3 structure visually but **non-functional**:

- Tabs: `Настройки` | `Туры` | `Рассылки` | `Результаты` — `span` or `button disabled` with `title="Скоро 2.3"`
- Right: reuse `ContestPicker` if already works for SUPERVISOR+
- Brand link → `/admin`

### 6.7 `/staff/login/page.tsx` (recommended)

- Reuse `LoginForm` component (extract from `LoginModal` if needed — minimal refactor)
- Same `useAuth().login()` → resolver handles redirect
- Copy: «Вход для организаторов»; subtitle explaining staff use same credentials
- Link from `AppShell` footer: «Вход для организаторов» → `/staff/login`
- No separate API — `POST /auth/login` only

### 6.8 `AppShell` header

| Auth state | Role | Nav |
|------------|------|-----|
| Visitor | — | «Вход» |
| Authenticated | USER | «Личный кабинет» → `/profile` |
| Authenticated | SUPERVISOR+ | «Управление» → `/admin` (hide «Личный кабинет») |

Keep `ContestPicker` for SUPERVISOR+ in header (existing).

---

## 7. Unit tests (Vitest)

**File:** `frontend/src/lib/auth/resolvePostLoginPath.test.ts`

| Case | Expected path |
|------|---------------|
| `is_temp_password=true`, any role | `/change-password` |
| USER, `is_temp_password=false` | `/profile` |
| SUPERVISOR | `/admin/settings/parameters` |
| ADMIN | `/admin` |

Run: `npm run test:unit`.

---

## 8. Implementation order

1. Backend: `settings.py` → `bootstrap_users.py` → `.env.example` → `DEV_SETUP.md`
2. Verify: `uv run python src/scripts/dev_setup.py` then `curl -X POST …/auth/login` with `user/user` → 200
3. `resolvePostLoginPath.ts` + unit tests
4. `AuthProvider` + `ProtectedRoute` updates
5. `/profile` USER-only guard
6. `/` home role redirect
7. `/admin/*` stub pages + `AdminTopNav`
8. `AppShell` nav + optional `/staff/login`
9. Living docs update (§11)
10. Lint/build/unit pass
11. Handoff to `stage_2.md`

---

## 9. Documentation maintenance (required)

Same pattern as `coder_2.1.md` §11:

| File | Updates |
|------|---------|
| `agent_docs/ui/pages.md` | `/admin` stubs ✅; `/profile` USER-only; `/staff/login`; access matrix |
| `agent_docs/ui/components.md` | `AdminTopNav` stub; `resolvePostLoginPath` in auth module |
| `agent_docs/ui/state_management.md` | Post-login routing via resolver in `AuthProvider` |
| `agent_docs/contracts/frontend_api_integration.md` | Confirm § Post-login routing matches implementation |

Append update log rows — do not delete prior content.

---

## 10. Acceptance criteria (2.1.1 done)

Manual smoke (all must pass):

- [ ] **`user/user` login → `/profile`** (not `/admin`)
- [ ] **`supervisor/…` login → `/admin/*`** (not `/profile`)
- [ ] **`admin/…` login → `/admin`** dashboard stub
- [ ] **Supervisor cannot stay on `/profile`** — auto-redirect `/admin`
- [ ] **Temp password** → `/change-password` → after change → role-appropriate path
- [ ] **Home `/`:** USER → contests flow; SUPERVISOR/ADMIN → `/admin`
- [ ] **AppShell:** USER sees «Личный кабинет»; staff sees «Управление»
- [ ] **`dev_setup.py` + API login `user/user`** → 200
- [ ] **`npm run test:unit`** — includes `resolvePostLoginPath` tests
- [ ] **`npm run lint`**, **`type-check`**, **`format:check`**, **`build`** pass
- [ ] Living docs updated (§9)
- [ ] `bootstrap_users.py` has TEMPORARY comment; `todo.md` notes removal after 2.3

---

## 11. Handoff

Append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Coder (2.1.1 routing hotfix + demo user + admin stubs)
- STATUS: READY_FOR_TEST
- Scope: resolvePostLoginPath, role guards, /admin stubs, bootstrap demo user
- Key paths: frontend/src/lib/auth/resolvePostLoginPath.ts, app/admin/*, bootstrap_users.py
- Verified: npm run build, test:unit; user/user API login 200 after dev_setup
- Docs updated: ui/pages.md, ui/components.md, ui/state_management.md, DEV_SETUP.md
- Next: agent_docs/instructions/tester_2.1.1.md
```

---

## 12. Explicitly OUT OF SCOPE

- Full supervisor admin UI (parameters CRUD, participants invite) → **2.3**
- Prediction form and privacy → **2.2**
- New Python API routes
- Removing demo user seed (tracked in `todo.md` for post-2.3 cleanup)
- `CONTEST_LOCKED` workaround for contest `1` invites
