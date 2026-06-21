# Tester Instructions — Stage 1.6: Bootstrap Users & Organizer API

> Status gate: @Coder `READY_FOR_TEST` for 1.6. **Prerequisite:** Stage 1.5 at `TEST_PASS`.
> Reference: `instructions/coder_1.6.md`, `plans/draft_1.6_bootstrap_users.md`,
> `manuals/BOOTSTRAP_USERS.md`, `.env.example`.

## 1. Objective

Verify Stage 1.6 **user bootstrap and organizer API** without re-running full 1.4 scoring gate:

1. **Organizer API** — ADMIN can create SUPERVISOR; RBAC and duplicate-login guards.
2. **Bootstrap script** — optional smoke on temp DB with `.env` values (if feasible in CI).
3. **Docs** — `.env.example` and `BOOTSTRAP_USERS.md` match implemented behaviour.
4. **Regression** — full automated suite still green.

**Non-goals:** production deploy playbook, manual bcrypt workshop, admin UI.

## 2. Scope — files you may create

```
tests/api/test_admin_users.py           # extend if gaps found
tests/unit/test_bootstrap_users_1_6.py  # NEW (optional) — password resolution / idempotency
agent_docs/reports/test_1.6.md          # NEW — Russian report with [TEST-ID] table
```

You may **extend** `tests/api/conftest.py` with helpers if needed.

**Do NOT modify** `src/` unless Coder left a blocker (document in report).

## 3. API tests (required)

Use `loaded_api` fixture; `admin_api` / `supervisor_api` from conftest.

### 3.1 `[API-SUP-CREATE]`

```http
POST /api/v1/admin/users/supervisor
Authorization: Bearer <admin_api token>
{
  "login": "new_supervisor_<unique>",
  "password": "superpass123",
  "first_name": "New",
  "last_name": "Supervisor"
}
```

Assert:

- HTTP 200
- `body.user.role == "SUPERVISOR"`
- `POST /auth/login` with new credentials → 200
- `GET /auth/me` → role SUPERVISOR

### 3.2 `[API-SUP-RBAC]`

Same POST as SUPERVISOR (`supervisor_api` token) → **403**.

### 3.3 `[API-SUP-DUP]`

POST with `login: "supervisor_api"` (existing) as ADMIN → **400**, `code == "VALIDATION_ERROR"`.

### 3.4 `[API-SUP-VALIDATION]` (optional)

Empty `login` or `password` → **422** (Pydantic).

## 4. Bootstrap script tests (optional but recommended)

Run against **temporary SQLite** (not committed `football.db`):

```bash
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export SEED_ADMIN_PASSWORD=testadmin123
export SEED_SUPERVISOR_LOGIN=boot_supervisor
export SEED_SUPERVISOR_PASSWORD=testsup123
uv run python src/scripts/bootstrap_users.py --database-url "$DATABASE_URL"
# second run → skip messages, no error
uv run python src/scripts/bootstrap_users.py --database-url "$DATABASE_URL"
```

| ID | Check |
|----|-------|
| `[BOOT-ADMIN]` | ADMIN login works after bootstrap (if contest seeded in same DB) |
| `[BOOT-SUP]` | SUPERVISOR login works when env set |
| `[BOOT-IDEM]` | Second run exits 0; logs "already exists, skipping" |
| `[BOOT-NO-SUP]` | Without `SEED_SUPERVISOR_*` → supervisor skipped, exit 0 |

If in-memory DB lacks contest, `[BOOT-ADMIN]` may only verify user row exists via direct DB read in a unit test — acceptable.

## 5. Documentation audit (read-only)

| Check | Pass criteria |
|-------|---------------|
| `[DOC-ENV-EXAMPLE]` | `.env.example` lists `SEED_ADMIN_PASSWORD`, `SEED_SUPERVISOR_*`, `JWT_SECRET_KEY`, hash one-liner |
| `[DOC-BOOTSTRAP]` | `manuals/BOOTSTRAP_USERS.md` documents script order, idempotency, API alternative |
| `[DOC-API-GUIDE]` | `API_GUIDE.md` mentions `POST /admin/users/supervisor` |
| `[DOC-CONTRACT]` | `api_v1.yaml` path matches implementation |

## 6. Regression subset (mandatory)

After 1.6-specific tests pass:

```bash
uv run pytest tests/ --ignore=tests/manual -q
```

Expect: all green (same baseline as 1.5 + new tests).

Quick 1.5 smoke (optional):

```bash
uv run pytest tests/api/test_errors_1_5.py tests/unit/test_exceptions_1_5.py -q
```

## 7. Report template (`agent_docs/reports/test_1.6.md`)

Russian summary for user. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[API-SUP-CREATE]` | PASS/FAIL | |
| `[API-SUP-RBAC]` | PASS/FAIL | |
| `[API-SUP-DUP]` | PASS/FAIL | |
| `[BOOT-*]` | PASS/SKIP | |
| `[DOC-*]` | PASS/FAIL | |
| Regression | PASS/FAIL | N passed |

Verdict: **TEST_PASS** / **TEST_FAIL** with blockers for @Coder.

## 8. Progress update

On **TEST_PASS**, ask Planner/Coder to append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Tester (1.6)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_1.6.md
```

## 9. Explicitly OUT OF SCOPE

- Re-verify 90/90 scoring / CANARY manual scripts
- Security audit of bcrypt cost factor
- Penetration test of JWT
