# Coder Instructions — Stage 1.13: Rename admin → supervisor (API + UI)

> **Status gate:** `INSTRUCTIONS_READY`
> **When to run:** **Last**, after `coder_1.12_fix` and `coder_2.1.2_fix_supervisor` are merged and green.
> **Delivery:** **One dedicated git commit**; then full test suite (pytest + frontend lint/type-check + E2E if available).
> **Prerequisite:** No real platform ADMIN UI exists yet — `docs/04_supervisor_scenario.md` covers organizer flows only; admin scenarios are undefined. **Now is the right time for a hard rename.**

---

## 1. Objective

Eliminate naming collision between:

| Term | Meaning after rename |
|------|----------------------|
| **Role `SUPERVISOR`** | Contest organizer (организатор) |
| **Role `ADMIN`** | Platform administrator (future; minimal API today) |
| **URL `/supervisor/`** | All organizer UI + contest-scoped operational API |
| **URL `/admin/`** | Platform-admin API only (global user management, cross-contest tools) |

**Why rename API too:** `/api/v1/contests/{id}/admin/rounds` is organizer functionality per supervisor scenarios — not platform admin. Keeping `admin` in API paths will confuse implementation when real admin UI arrives.

---

## 2. API path mapping (LOCKED)

### 2.1 Contest-scoped organizer routes — rename `admin` → `supervisor`

**Primary implementation:** `src/api/v1/contest_ops.py` (contest router prefix `/contests/{contest_id}`).

| Old path | New path |
|----------|----------|
| `POST …/admin/rounds` | `POST …/supervisor/rounds` |
| `POST …/admin/rounds/free-tour` | `POST …/supervisor/rounds/free-tour` |
| `PATCH …/admin/rounds/{round_id}` | `PATCH …/supervisor/rounds/{round_id}` |
| `POST …/admin/rounds/{round_id}/activate` | `POST …/supervisor/rounds/{round_id}/activate` |
| `POST …/admin/rounds/{round_id}/close` | `POST …/supervisor/rounds/{round_id}/close` |
| `POST …/admin/rounds/{round_id}/calculate` | `POST …/supervisor/rounds/{round_id}/calculate` |
| `POST …/admin/rounds/{round_id}/publish` | `POST …/supervisor/rounds/{round_id}/publish` |
| `PUT …/admin/matches/{match_id}/result` | `PUT …/supervisor/matches/{match_id}/result` |
| `PATCH …/admin/matches/{match_id}/status` | `PATCH …/supervisor/matches/{match_id}/status` |

OpenAPI tags: `supervisor (contest ops)` — drop misleading `admin (supervisor)`.

### 2.2 Platform ADMIN routes — keep `/admin/` prefix

These are **not** organizer flows; do **not** rename to supervisor:

| Path | Role | Purpose |
|------|------|---------|
| `POST /api/v1/admin/users/supervisor` | ADMIN | Create supervisor account |
| `POST /api/v1/contests/{contest_id}/admin/recalculate` | ADMIN | Full contest recalculate (optional: move to `POST /api/v1/admin/contests/{id}/recalculate` in same PR if cleaner — document choice) |

### 2.3 Legacy deprecated shims — remove or 410

Files (global prefix `/api/v1`, no contest_id):

- `src/api/v1/admin_rounds.py`
- `src/api/v1/admin_results.py`
- `src/api/v1/admin_contest.py`
- `src/api/v1/admin_misc.py` (partial)

**Action:** Either delete routers if unused, or leave **deprecated** aliases that return `301`/`308` redirect is not possible for POST — prefer:

- Remove from `main.py` includes if no tests depend on them, **or**
- Keep one release with `@router.*(deprecated=True)` returning `410 Gone` + message «use /contests/{id}/supervisor/…»

Grep tests for `/api/v1/admin/rounds` (without contest prefix) before deleting.

### 2.4 Setup routes — already correct

No rename needed (not under `admin`):

- `GET/POST /api/v1/contests/{id}/teams`
- `GET/POST /api/v1/contests/{id}/participants`
- `PATCH /api/v1/contests/{id}`

---

## 3. Backend file renames (recommended)

| Old | New |
|-----|-----|
| `src/api/v1/admin_rounds.py` | Remove or `legacy_admin_shims.py` (deprecated only) |
| `src/api/v1/admin_results.py` | same |
| `src/api/v1/admin_contest.py` | same |
| `src/api/v1/admin_misc.py` | Keep for global `/admin/recalculate` shim only, or merge into `admin_users.py` |
| `src/api/v1/admin_users.py` | **Keep name** — platform admin |

Router handlers in `contest_ops.py` — update path strings only; file can stay.

---

## 4. Frontend mapping (LOCKED)

### 4.1 Routes

| Old | New |
|-----|-----|
| `frontend/src/app/admin/**` | `frontend/src/app/supervisor/**` |
| `/admin/settings/parameters` | `/supervisor/settings/parameters` |
| `/admin/settings/participants` | `/supervisor/settings/participants` |
| `/admin/settings/teams` | `/supervisor/settings/teams` |
| `/admin/rounds` | `/supervisor/rounds` |
| `/admin/results` | `/supervisor/results` |
| `/admin/newsletters` | `/supervisor/newsletters` |
| `/admin/lifecycle` | `/supervisor/lifecycle` (organizer lifecycle when training mode) |
| `/admin/users` | **Move to future** `/admin/users` stub OR keep as supervisor-only stub at `/supervisor/users` until real admin UI |

**Temporary redirects** in `frontend/next.config.mjs` (301):

```js
{ source: '/admin/:path*', destination: '/supervisor/:path*', permanent: true }
{ source: '/admin', destination: '/supervisor/settings/parameters', permanent: true }
```

Remove redirects after E2E updated (or keep indefinitely for dev bookmarks).

### 4.2 Code identifiers (same commit)

| Old | New |
|-----|-----|
| `components/admin/` | `components/supervisor/` |
| `lib/admin/` | `lib/supervisor/` |
| `AdminTopNav` | `SupervisorTopNav` |
| `AdminPageShell` | `SupervisorPageShell` |
| `deriveAdminUiMode` | `deriveSupervisorUiMode` |
| `useContestAdmin` | `useContestSupervisor` (optional; `useContestOrganizer` also OK — pick one, grep all) |
| `contestAdmin` in `endpoints.ts` | `contestSupervisor` |
| E2E `gotoAdminContest` | `gotoSupervisorContest` |

### 4.3 Auth routing

`resolvePostLoginPath.ts`:

- `SUPERVISOR` → `/supervisor/settings/parameters`
- `ADMIN` → `/admin` (future platform dashboard stub; until built, redirect to `/supervisor/settings/parameters` with banner «Режим администратора платформы — в разработке» OR separate minimal `/admin` page listing platform tools only)

Document decision in commit message.

---

## 5. Documentation & contracts (mandatory same commit)

Update **every** reference — grep is the source of truth:

```bash
rg '/admin/' --glob '!node_modules' --glob '!.venv' --glob '!docs/'
rg 'admin/rounds' --glob '!node_modules'
rg 'AdminTopNav|deriveAdminUiMode|gotoAdminContest' frontend/
```

| File | Action |
|------|--------|
| `agent_docs/contracts/api_v1.yaml` | All contest-scoped `admin` paths → `supervisor`; bump minor version note in description |
| `agent_docs/contracts/frontend_api_integration.md` | §5.5 matrix, routing table §2.4, path builders |
| `manuals/API_GUIDE.md` | Terminology § + all endpoint examples |
| `manuals/DEV_SETUP.md` | curl examples |
| `manuals/BOOTSTRAP_USERS.md` | keep `/admin/users/supervisor` |
| `agent_docs/ui/pages.md` | route paths |
| `agent_docs/ui/components.md` | component paths |
| `agent_docs/instructions/coder_2.1.2_fix_supervisor.md` | path references |
| `agent_docs/instructions/coder_1.12_fix.md` | §9 cross-link only |
| `agent_docs/plans/draft_2.md` | if paths cited |
| `README.md` | if supervisor URLs mentioned |

**Do not edit** immutable `docs/` specs except if user runs `/docs-git-sync` — note in PR that `docs/04_supervisor_scenario.md` route examples are descriptive; canonical routes live in `manuals/` + contracts.

Add to `manuals/API_GUIDE.md` — **Terminology**:

```markdown
## Roles vs URL prefixes

- **SUPERVISOR** (role): contest organizer. UI: `/supervisor/*`. API: `/api/v1/contests/{id}/supervisor/*`.
- **ADMIN** (role): platform operator. API: `/api/v1/admin/*` (global). UI: `/admin/*` (future).
- Do not use `admin` in URLs for organizer features.
```

---

## 6. Tests (mandatory)

### 6.1 Backend

Replace in all `tests/`:

- `contest_url(id, "/admin/rounds")` → `"/supervisor/rounds"`
- Same for matches, calculate, publish, close, activate, free-tour

Files likely touched (non-exhaustive — **run rg**):

- `tests/api/conftest.py`
- `tests/api/test_*.py` (errors, multi_contest, operational, setup, lifecycle, …)
- `tests/integration/*`

### 6.2 Frontend

- `frontend/e2e/**/*.ts` — all `/admin/` paths
- `frontend/e2e/fixtures/adminApi.ts` → rename file + paths
- `frontend/src/lib/admin/deriveAdminUiMode.test.ts` → move + rename
- `frontend/tests/*` if any

### 6.3 Verification gate (after commit)

```bash
# Full backend
uv run pytest tests/ -v --tb=short

# Lint
uv run ruff check src/ tests/
uv run mypy src/

# Frontend
cd frontend && npm run lint && npm run type-check

# E2E (if env up)
cd frontend && npx playwright test
```

**Do not merge** if any test still references old `/admin/rounds` contest-scoped paths (except platform `/admin/users`).

---

## 7. Git workflow

1. Ensure branch is green **before** rename commit.
2. Single commit: `refactor: rename organizer admin paths to supervisor (API + UI)`
3. Run full §6.3 verification.
4. Fix stragglers in follow-up commits only if pre-commit hook reformats — avoid mixing feature work.

**No backward-compat aliases** for contest-scoped `/admin/*` in production code (dev is pre-release). Deprecated global shims may 410 for one cycle if needed.

---

## 8. Checklist summary

- [ ] `contest_ops.py` paths → `supervisor`
- [ ] Legacy admin router files handled (§2.3)
- [ ] `api_v1.yaml` updated
- [ ] `frontend` app dir + components + lib renamed
- [ ] `endpoints.ts` → `contestSupervisor`
- [ ] `resolvePostLoginPath` updated
- [ ] All pytest paths updated
- [ ] All Playwright paths updated
- [ ] `manuals/API_GUIDE.md` terminology section
- [ ] `frontend_api_integration.md` updated
- [ ] `next.config.mjs` redirects (optional)
- [ ] Full test suite green

---

## 9. Out of scope

- Implementing real platform ADMIN UI
- Renaming DB tables or Python module `admin_*` in `src/services/` unless coder finds confusing dead code — focus on **HTTP paths and user-facing routes**
- Changing OpenAPI tag `admin (users)` for platform endpoints
