# Coder Instructions — Stage 2.1: Foundation, Auth & Profile Shell

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Backend Stage 1.8+ at `TEST_PASS` (B1–B3 resolved). **Local env:** [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md) + `src/scripts/dev_setup.py`. See `agent_docs/reports/BLOCKED.md`.
> **Plan:** `agent_docs/plans/draft_2.md` § Sub-stage 2.1.
> **Specs:** `agent_docs/ui/{components,pages,forms_validation,state_management}.md`, `agent_docs/contracts/frontend_api_integration.md`.
> **Language policy:** UI copy Russian; code comments English; display API `detail` as-is (Russian).

---

## 1. Objective

Bootstrap the **`frontend/`** Next.js application and deliver the **auth + navigation shell** required before predictions (2.2) and admin UI (2.3).

| Deliverable | Description |
|-------------|-------------|
| Next.js 14+ App Router + TypeScript strict + Tailwind | Greenfield `frontend/` package |
| Typed API client | JWT, error parsing, 401 → logout |
| Auth flow | Login modal, logout, temp-password gate, `/change-password` |
| Contest discovery | Visitor list (B2), User «Конкурсы» (B1), Supervisor picker (GET `/contests`) |
| Profile hub | `/profile` with contacts form (B3) + nav links (stubs OK for 2.2+) |
| App shell | Header per `user_*.jpg` — brand, «Вход» / «Личный кабинет» + «Выйти» |

**Non-goals (later sub-stages):**

- Tabbed contest page with Leaderboard / Прогнозы / Результаты matrices → **2.2 / 2.4**
- Prediction form → **2.2**
- Admin `/admin/*` pages → **2.3**
- Playwright E2E full suite → **tester_2.1** (optional smoke only here)
- No mock API data — real FastAPI only (`docs/03_user_scenarios.md`)

---

## 2. Background & dev environment

**Authoritative setup guide:** [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md) — prerequisites, bootstrap script, test logins, troubleshooting.

- `frontend/` **does not exist** yet — create from scratch (this stage).
- Backend at `http://127.0.0.1:8000` — contest-scoped API `/api/v1/contests/{contest_id}/…` (no legacy shims).
- B1–B3 implemented in Stage 1.8; frontend fallbacks remain for resilience (§8).

### 2.1 Prerequisites (verify before coding)

| Tool | Required | Notes |
|------|----------|--------|
| Python + **uv** | ≥ 3.12 | `uv sync` in repo root |
| **Node.js** | ≥ 20 LTS | for `frontend/` (npm) |
| **npm** | ≥ 10 | ships with Node 20+ |
| `.env` | yes | copy `.env.example`; set `SEED_ADMIN_PASSWORD`, `SEED_SUPERVISOR_PASSWORD` |

Check: `uv run python src/scripts/dev_setup.py --check`

### 2.2 One-shot backend bootstrap

```bash
cd /work/football_prog
cp .env.example .env                    # once; edit passwords
uv run python src/scripts/dev_setup.py  # migrations + loader + admin + RUNNING contest
```

This runs (in order): `alembic upgrade head` → `load_test_data.py --reset` → `bootstrap_users.py` → contest `1` set **RUNNING** (required for `GET /contests/public`, B2).

**Why bootstrap after loader:** `load_test_data --reset` deletes the `users` table; `bootstrap_users.py` must run **after** to restore `admin` / `supervisor`.

### 2.3 Daily dev workflow

```bash
# Terminal 1 — API (after bootstrap)
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — frontend (after scaffold in §4)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                             # http://127.0.0.1:3000
```

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

### 2.4 Test logins

| Role | Login | Password |
|------|-------|----------|
| USER | `user` | `user` (from loader) |
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` in root `.env` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` in root `.env` |

See [BOOTSTRAP_USERS.md](../../manuals/BOOTSTRAP_USERS.md). Reset demo DB: `uv run python src/scripts/dev_setup.py`.

### 2.5 Frontend env (create with scaffold)

`frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Use `127.0.0.1` (matches Playwright `tester_2.1` and CORS smoke tests).

---

## 3. Scope — files you may create/modify

```
frontend/                                 # NEW entire package
  package.json
  tsconfig.json
  next.config.ts
  tailwind.config.ts
  postcss.config.mjs
  .env.local.example
  .gitignore
  src/
    app/
      layout.tsx                          # providers root
      page.tsx                            # Visitor home / discovery
      contests/page.tsx                   # «Конкурсы» list
      profile/page.tsx                    # profile hub
      change-password/page.tsx
      contest/[contestId]/page.tsx        # minimal placeholder (2.4)
    components/
      layout/AppShell.tsx
      layout/LoginModal.tsx
      auth/LoginForm.tsx
      auth/ChangePasswordForm.tsx
      auth/ProtectedRoute.tsx
      contest/ContestPicker.tsx
      contest/ContestList.tsx
      profile/ContactsForm.tsx
      profile/ProfileMenu.tsx
      ui/Toast.tsx
      ui/LoadingState.tsx
      ui/ErrorState.tsx
    lib/
      api/client.ts
      api/endpoints.ts
      api/errors.ts
      api/cache.ts                        # stub for 2.4 ETag
      auth/token.ts
      auth/guards.ts
      contest/resolveDefaultContestId.ts
      validation/login.ts
      validation/changePassword.ts
      validation/contacts.ts
    providers/
      AuthProvider.tsx
      ContestProvider.tsx
      ToastProvider.tsx
    hooks/
      useAuth.ts
      useContest.ts
      useMyContests.ts
      usePublicContests.ts
      useContacts.ts
    types/api.ts
  src/lib/**/*.test.ts                    # Vitest unit tests (minimal)

agent_docs/ui/components.md               # UPDATE — mark 2.1 components + file paths
agent_docs/ui/pages.md                    # UPDATE — mark 2.1 routes implemented
agent_docs/ui/state_management.md         # UPDATE if provider API differs from spec
agent_docs/ui/forms_validation.md         # UPDATE if Zod paths/schemas differ
agent_docs/contracts/frontend_api_integration.md  # UPDATE if integration quirks found
agent_docs/progress/stage_2.md            # APPEND handoff (append-only)
```

**Do NOT modify:** `docs/`, Python `src/` except **`src/scripts/dev_setup.py`** if bootstrap needs a fix (document in handoff). `manuals/` — only if setup doc must be corrected alongside a bootstrap fix.

---

## 4. Project scaffold

### 4.1 Create Next.js app

Use App Router, TypeScript, Tailwind, ESLint. **No** external UI libraries (no shadcn, MUI, Radix).

Suggested versions (align with `docs/02_project_structure.md`):

- `next` ≥ 14
- `react` / `react-dom` ≥ 18
- `typescript` ≥ 5.3
- `tailwindcss` ≥ 3.4
- `zod` for validation

Add devDependencies: `vitest`, `@testing-library/react` (optional for 2.1), `eslint`, `prettier`.

`package.json` scripts:

```json
{
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,js,jsx,json,css,md}\"",
    "format": "prettier --write \"src/**/*.{ts,tsx,js,jsx,json,css,md}\"",
    "test:unit": "vitest run",
    "test:e2e": "playwright test"
  }
}
```

Optional lint smoke: `frontend/tests/test_linting.ts` or `"test:lint": "npm run lint && npm run type-check && npm run format:check"`.

### 4.2 Environment

`frontend/.env.local.example`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Copy to `.env.local` for local dev. **`NEXT_PUBLIC_DEFAULT_CONTEST_ID`** is the fallback when B1/B2 lists are empty or requests fail. Align with [manuals/DEV_SETUP.md](../../manuals/DEV_SETUP.md).

### 4.3 CORS

Backend `cors_origins` defaults to `["*"]` in `config/settings.py` — direct browser calls from `:3000` to `:8000` should work. If CORS errors appear, check deployment env / `settings.py`; do not add non-secret vars to root `.env`. **Do not** add a Next.js rewrite proxy unless CORS cannot be fixed on backend (document in handoff if you do).

---

## 5. API layer

Follow `agent_docs/contracts/frontend_api_integration.md` exactly.

### 5.1 `lib/api/client.ts`

```ts
export class AppError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
  ) { super(detail); }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { auth?: boolean },
): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');

  if (options?.auth !== false) {
    const token = localStorage.getItem('fp_access_token');
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${base}${path}`, { ...options, headers });

  if (res.status === 401) {
    window.dispatchEvent(new Event('fp:unauthorized'));
    throw new AppError(401, 'Unauthorized');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new AppError(res.status, body.detail ?? res.statusText, body.code);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
```

- `401` → dispatch `fp:unauthorized` (AuthProvider listens → logout).
- Parse `{ detail, code? }` for domain errors; Pydantic 422 may be array — handle in form components.

### 5.2 `lib/api/endpoints.ts`

Path builders — **contest-scoped** for future stages; global auth paths:

```ts
export const auth = {
  login: () => '/api/v1/auth/login',
  me: () => '/api/v1/auth/me',
  changePassword: () => '/api/v1/auth/change-password',
  contacts: () => '/api/v1/auth/me/contacts',
};
export const me = {
  contests: () => '/api/v1/me/contests',
};
export const contests = {
  list: () => '/api/v1/contests',
  public: () => '/api/v1/contests/public',
  byId: (id: number) => `/api/v1/contests/${id}`,
};
```

Login uses `auth: false`. Public list uses `auth: false`.

### 5.3 `lib/contest/resolveDefaultContestId.ts`

```ts
export function resolveDefaultContestId(): number {
  const raw = process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID ?? '1';
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) throw new Error('Invalid NEXT_PUBLIC_DEFAULT_CONTEST_ID');
  return id;
}
```

Used when `GET /me/contests` or `GET /contests/public` returns `[]` or errors.

---

## 6. State — providers & hooks

Implement per `agent_docs/ui/state_management.md`.

### 6.1 `AuthProvider`

State: `user: UserOut | null`, `loading: boolean`.

| Method | Behaviour |
|--------|-----------|
| `login(login, password)` | POST `/auth/login` → store `fp_access_token` → GET `/auth/me` → if `is_temp_password` redirect `/change-password` else `/profile` |
| `logout()` | clear token, `user=null`, router.push(`/`) |
| `refreshUser()` | GET `/auth/me` |

On mount: if token → `refreshUser()`; on 401 → logout.

Listen: `window.addEventListener('fp:unauthorized', logout)`.

### 6.2 `ContestProvider`

State: `contestId`, `contest: ContestOut | null`.

- `setContestId(id)` → GET `/contests/{id}` (SUPERVISOR+ only today — for 2.1 supervisor picker stores id in context + localStorage key `fp_active_contest_id`).
- For USER/VISITOR: store selected contest id from list navigation; full `ContestOut` fetch optional in 2.1 (id is enough for routing).

### 6.3 Hooks (2.1)

| Hook | Endpoint | Notes |
|------|----------|-------|
| `useMyContests()` | GET `/me/contests` | On error/empty → `[{ id: resolveDefaultContestId(), … }]` synthetic single item **only** as fallback navigation target, label from env or «Конкурс по умолчанию» |
| `usePublicContests()` | GET `/contests/public` | RUNNING only; empty → redirect `/contest/{defaultId}` |
| `useContacts()` | GET/PATCH `/auth/me/contacts` | `readonly` flag when GET fails |

---

## 7. Components (2.1 subset)

Implement and wire per `agent_docs/ui/components.md`. After implementation, **update `components.md`** with actual file paths and note any prop renames.

### 7.1 `AppShell`

- Left: **Sport Prognosis**
- Right (Visitor): button **Вход** → `LoginModal`
- Right (authenticated): link **Личный кабинет** → `/profile`, button **Выйти**
- If `role` is `SUPERVISOR` or `ADMIN`: show **`ContestPicker`** (compact) in header
- Footer: `© 2024 SportPrognosis. Все права защищены.`

### 7.2 `LoginModal` + `LoginForm`

Zod schema per `ui/forms_validation.md` § LoginForm.

- POST login with `auth: false`
- On 401: show `detail` under form
- On success: close modal; AuthProvider handles redirect

### 7.3 `ChangePasswordForm`

Route `/change-password`. Wrapped in `ProtectedRoute requireAuth`.

- Block all other app routes while `user.is_temp_password === true` (except this page and `/auth/me` hydration)
- POST change-password → `refreshUser()` → redirect `/profile`
- Zod: min password length 8, confirm match

### 7.4 `ContestPicker` + `ContestList`

**Supervisor/Admin:** fetch `GET /contests` (Bearer).

**User:** fetch `GET /me/contests`.

**Visitor:** not shown in header (discovery on `/`).

On select: `setContestId(id)`, persist `fp_active_contest_id`, navigate `/contest/{id}` (placeholder page OK).

Fallback: if list empty → use `resolveDefaultContestId()`.

### 7.5 `ContactsForm`

On `/profile`. Zod per `ui/forms_validation.md` § ContactsForm.

| Mode | When |
|------|------|
| **Editable** | GET contacts succeeds |
| **Readonly** | GET fails (404/501/network) — show fields disabled, **hide Save**, small note «Редактирование недоступно» |

PATCH on Save → toast success; on error show `detail`.

Allowed during temp password (backend 1.8) — but UI still forces `/change-password` first via guard; contacts editable after password changed.

### 7.6 `ProfileMenu`

Links (stubs → real routes in 2.2+):

| Label | Route | 2.1 behaviour |
|-------|-------|---------------|
| Контакты | anchor on page | scroll to ContactsForm |
| Конкурсы | `/contests` | working |
| Сделать прогноз | `/contest/[id]/predict/...` | disabled link or «Скоро (2.2)» |
| Просмотр результатов | `/contest/[id]` | placeholder |
| Личная статистика | `#` | stub text |
| Выйти | logout | working |

### 7.7 Shared UI

- `ToastProvider` + `useToast()` — success/error; no animation library
- `LoadingState`, `ErrorState`
- `ProtectedRoute` — props: `requireAuth?`, `requireRole?`, `requireNotTempPassword?`

---

## 8. Pages & routing

Implement per `agent_docs/ui/pages.md`. After implementation, **update `pages.md`** §1 routes with ✅ and note placeholders.

| Route | Access | 2.1 implementation |
|-------|--------|---------------------|
| `/` | all | Visitor: `ContestList` from `GET /contests/public`; click → `/contest/{id}`. Authenticated: optional redirect to `/contests` or last contest. Empty public list → redirect `/contest/{defaultId}` |
| `/contests` | auth | User: `/me/contests`; Supervisor+: `/contests`; list UI + navigation |
| `/profile` | USER+ | `ProfileMenu` + `ContactsForm`; show `user.login`, name |
| `/change-password` | auth + temp pwd | `ChangePasswordForm`; also reachable when `is_temp_password` forced |
| `/contest/[contestId]` | all | **Placeholder:** title + «Раздел в разработке (2.4)» — proves routing + contest context |

**Guards:**

- `/profile`, `/contests` → `requireAuth`
- `/change-password` → `requireAuth`; if `!is_temp_password` → redirect `/profile`
- All other authenticated routes: if `is_temp_password` → redirect `/change-password`

---

## 9. Fallback behaviour (mandatory)

| ID | Primary | Fallback (no mocks) |
|----|---------|---------------------|
| B1 | `GET /me/contests` | Empty or error → navigate using `NEXT_PUBLIC_DEFAULT_CONTEST_ID` |
| B2 | `GET /contests/public` | Empty or error → redirect `/contest/{defaultId}` |
| B3 | `GET/PATCH /auth/me/contacts` | GET fail → readonly fields, no Save |

Never fabricate leaderboard/prediction data — only contest **id** fallback for navigation.

---

## 10. Unit tests (Vitest)

Per `docs/06_front_tests.md` — minimal set for 2.1:

| File | Tests |
|------|-------|
| `lib/api/errors.test.ts` or `client.test.ts` | Parse `AppError` from JSON body; 401 dispatches event |
| `lib/contest/resolveDefaultContestId.test.ts` | Valid env; invalid throws |
| `lib/validation/login.test.ts` | Empty fields rejected |
| `lib/validation/contacts.test.ts` | Email format |

Run: `npm run test:unit` — must pass before handoff.

E2E (Playwright) — optional smoke in 2.1; full specs delegated to `tester_2.1.md` when written.

---

## 11. Documentation maintenance (required)

When implementation deviates from or completes spec sections, **update living docs** in the same PR/commit batch:

| File | What to update |
|------|----------------|
| `agent_docs/ui/components.md` | Mark 2.1 components ✅ + `frontend/src/...` paths; append update log |
| `agent_docs/ui/pages.md` | Mark routes ✅/placeholder; append update log |
| `agent_docs/ui/state_management.md` | Provider fields/hooks if different; append update log |
| `agent_docs/ui/forms_validation.md` | Actual Zod export paths; append update log |
| `agent_docs/contracts/frontend_api_integration.md` | Any discovered quirks (422 shape, temp-password routes); append update log |

Do **not** delete spec content — annotate with **Implemented (2.1)** or **Deferred (2.x)**.

---

## 12. Acceptance criteria (2.1 done)

Manual smoke (all must pass):

- [ ] **`user/user` login → `/profile`** — header shows login, not «Вход»
- [ ] **Supervisor sees contest switcher** — `ContestPicker` populated from `GET /contests`
- [ ] **401 on any authenticated request → auto logout** — clear token, Visitor state
- [ ] **Temp password → forced `/change-password`** — cannot reach `/profile` until changed
- [ ] **CORS `:3000` ↔ `:8000`** — login works from browser without CORS errors
- [ ] **Visitor `/`** — lists RUNNING contests from `GET /contests/public` (or fallback redirect)
- [ ] **User `/contests`** — shows enrolled contests from `GET /me/contests`
- [ ] **Contacts** — GET/PATCH works; readonly fallback if GET fails
- [ ] **`npm run build`** succeeds
- [ ] **`npm run lint`**, **`npm run type-check`**, **`npm run format:check`** pass (Tester §6)
- [ ] **`npm run test:unit`** passes
- [ ] Living docs updated (§11)

---

## 13. Implementation order

1. Scaffold `frontend/` + env + Tailwind
2. `types/api.ts` + `lib/api/*`
3. Providers (`Auth`, `Toast`, `Contest`) + hooks
4. Validation schemas (Zod)
5. `AppShell`, `LoginModal`, `Toast`
6. Pages: `/`, `/contests`, `/change-password`, `/profile`
7. `ContactsForm` + fallback readonly mode
8. `ContestPicker` for SUPERVISOR+ in header
9. `ProtectedRoute` + temp-password gate
10. Placeholder `/contest/[contestId]`
11. Vitest unit tests
12. Update `agent_docs/ui/*` + `frontend_api_integration.md`
13. Append handoff to `agent_docs/progress/stage_2.md`

---

## 14. Handoff

Append to `agent_docs/progress/stage_2.md` (create file if missing):

```
## YYYY-MM-DD — Coder (2.1 foundation & auth)
- STATUS: READY_FOR_TEST
- Scope: frontend scaffold, auth, profile, contest discovery, contacts
- Blockers used: B1, B2, B3 (live API)
- Key paths: frontend/src/app/{page,profile,contests,change-password}, lib/api, providers
- Verified: npm run build, npm run test:unit; manual smoke checklist §12
- Docs updated: ui/components.md, ui/pages.md, ui/state_management.md, ui/forms_validation.md, frontend_api_integration.md
- Next: agent_docs/instructions/tester_2.1.md, then coder_2.2.md
```

---

## 15. Explicitly OUT OF SCOPE

- Leaderboard / Predictions / Results tabbed UI (`PublicTabs`, matrices)
- Prediction batch form
- Admin `/admin/*` shell and CRUD
- ETag caching implementation (stub OK)
- Team logo upload (B5)
- Docker / CI for frontend
- i18n — Russian only
