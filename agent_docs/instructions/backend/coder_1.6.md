# Coder Instructions — Stage 1.6: Bootstrap Users & Organizer API

> Status gate: `INSTRUCTIONS_READY`. **Prerequisite:** Stage 1.5 at `TEST_PASS`.
> Plan: `agent_docs/plans/draft_1.6_bootstrap_users.md`.
> **Language policy:** code comments English; HTTP `detail` Russian (existing 1.5 policy);
> API handler docstrings Russian; manuals English.

## 1. Objective

Close operational gaps for **first deploy** and **organizer onboarding**:

1. **HTTP:** ADMIN can create a contest organizer (`SUPERVISOR` global role).
2. **CLI:** Idempotent bootstrap script reads ADMIN + optional SUPERVISOR from `.env` (plaintext passwords → bcrypt at runtime).
3. **Secrets hygiene:** remove misleading hardcoded password hash default; document `.env` via `.env.example`.
4. **Runbook:** `manuals/BOOTSTRAP_USERS.md` for ops.

**Non-goals:** admin UI, user delete, role demotion, per-contest organizer binding (SUPERVISOR remains global `users.role`).

## 2. Background (why now)

- `agent_docs/plans/draft_1.md` §RBAC: `ADMIN` → “назначение supervisor” — planned but missing after 1.5.
- `seed.py` created ADMIN with `seed_admin_password_hash` default in repo — not a real bcrypt string.
- Tests used `conftest._seed_test_users` for `supervisor_api`; production had no equivalent.

## 3. Scope — files you may create/modify

```
src/services/user_admin_service.py     # NEW — create_supervisor()
src/schemas/users.py                   # NEW — CreateSupervisorRequest/Response
src/api/v1/admin_users.py              # NEW — POST /admin/users/supervisor
main.py                                # include admin_users router
config/settings.py                     # SEED_ADMIN_PASSWORD, SEED_SUPERVISOR_*
src/scripts/bootstrap_users.py         # NEW — bootstrap ADMIN + SUPERVISOR
src/scripts/seed.py                    # hash SEED_ADMIN_PASSWORD when set
.env.example                           # NEW — template + hash one-liner comment
manuals/BOOTSTRAP_USERS.md             # NEW — ops runbook
manuals/CONFIG.md                      # env table update
manuals/API_GUIDE.md                   # Admin User Management section
manuals/README.md                      # index entry
agent_docs/contracts/api_v1.yaml       # endpoint + schemas
tests/api/test_admin_users.py          # NEW
agent_docs/progress/stage_1.md         # append handoff (append-only)
```

**Do NOT modify** `src/scoring/*`, `docs/` (immutable specs), existing 1.4/1.5 business behaviour.

## 4. Settings (`config/settings.py`)

Add optional bootstrap fields (all overridable via `.env`):

```python
seed_admin_password: str | None = None
seed_admin_password_hash: str | None = None   # was required default — now optional

seed_supervisor_login: str | None = None
seed_supervisor_password: str | None = None
seed_supervisor_password_hash: str | None = None
seed_supervisor_first_name: str = "Supervisor"
seed_supervisor_last_name: str = "User"
```

Resolution order for password material:

1. Plaintext `SEED_*_PASSWORD` → `hash_password()` at script runtime.
2. Else `SEED_*_PASSWORD_HASH` (precomputed bcrypt).
3. For `bootstrap_users.py` ADMIN: exit with clear message if neither set.
4. For `seed.py` only: fall back to `"dev-only-placeholder-hash"` if neither set (dev backward compat).

## 5. Service — `user_admin_service.py`

```python
async def create_supervisor(
    session,
    *,
    login: str,
    password: str,
    first_name: str,
    last_name: str,
    is_temp_password: bool = False,
) -> User:
```

Rules:

- Strip `login`; reject empty login/password → `ValidationError` (Russian message).
- Duplicate login → `ValidationError` (`Логин «…» уже занят`).
- `role = UserRole.SUPERVISOR`; `password_hash = hash_password(password)`.
- Do **not** auto-enroll in `contest_participants` (organizer is not a player by default).

## 6. API — `POST /api/v1/admin/users/supervisor`

| Item | Value |
|------|-------|
| Router prefix | `/admin/users` |
| Tag | `admin (users)` |
| Auth | `RoleChecker(UserRole.ADMIN)` only |
| Response | `{ "user": UserOut }` |

Request body (`CreateSupervisorRequest`):

| Field | Validation |
|-------|------------|
| `login` | min_length=1 |
| `password` | min_length=1 |
| `first_name` | min_length=1 |
| `last_name` | min_length=1 |
| `is_temp_password` | default `false` |

Handler docstring (RU): «Создать организатора конкурса (роль SUPERVISOR). Только ADMIN.»

Register in `main.py` after other admin routers.

## 7. Bootstrap script — `bootstrap_users.py`

### 7.1 `seed_admin_user`

- Login from `SEED_ADMIN_LOGIN` (default `admin`).
- Skip if user exists; optionally add `contest_participants` row for first contest.
- `is_temp_password=True` (force change-password on first login).

### 7.2 `seed_supervisor_user`

- Run only when `SEED_SUPERVISOR_LOGIN` and password/hash configured.
- `is_temp_password=False` by default.
- **Comment in source:** when admin UI exists, comment out `await seed_supervisor_user(...)` in `run_bootstrap()`.

### 7.3 CLI

```bash
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/bootstrap_users.py --no-contest-enroll
```

Uses `create_engine` + `Base.metadata.create_all` (same pattern as `seed.py`).

## 8. `.env.example`

Include at minimum:

- `SEED_ADMIN_LOGIN`, `SEED_ADMIN_PASSWORD`
- `SEED_SUPERVISOR_LOGIN`, `SEED_SUPERVISOR_PASSWORD` (optional block)
- `JWT_SECRET_KEY`
- Comment with hash one-liner:

```bash
uv run python src/scripts/hash_password.py 'your-password'
```

(`core` is under `src/`; use this script or `PYTHONPATH=src` for inline `-c`.)

Note: `.env` is gitignored; never commit real secrets.

## 9. Documentation

### `manuals/BOOTSTRAP_USERS.md`

Sections: overview, prerequisites, configure `.env`, run script, first login, API alternative, retire CLI organizer block, related links.

### `manuals/API_GUIDE.md`

Add **Admin User Management** with `POST /admin/users/supervisor` table.

### `manuals/CONFIG.md`

Update env var table; link bootstrap script and `.env.example`.

## 10. Contract sync (`api_v1.yaml`)

Add path `/api/v1/admin/users/supervisor` and schemas `CreateSupervisorRequest`, `CreateSupervisorResponse`.

## 11. Tests — `tests/api/test_admin_users.py`

| Test ID | Assertion |
|---------|-----------|
| `[API-SUP-CREATE]` | ADMIN creates supervisor → 200; new user can login |
| `[API-SUP-RBAC]` | SUPERVISOR → 403 |
| `[API-SUP-DUP]` | duplicate login → 400, `code=VALIDATION_ERROR` |

Optional unit test for `create_supervisor` duplicate login (can live in API test).

## 12. Acceptance criteria

- [ ] `POST /api/v1/admin/users/supervisor` works for ADMIN; 403 for SUPERVISOR
- [ ] Duplicate login returns 400 + `VALIDATION_ERROR`
- [ ] `bootstrap_users.py` creates ADMIN when `SEED_ADMIN_PASSWORD` set
- [ ] `bootstrap_users.py` creates SUPERVISOR when `SEED_SUPERVISOR_*` set; skips when unset
- [ ] Second bootstrap run is idempotent (no password overwrite)
- [ ] `.env.example` present at repo root
- [ ] `manuals/BOOTSTRAP_USERS.md` complete
- [ ] `api_v1.yaml` updated
- [ ] `pytest tests/ --ignore=tests/manual` green

## 13. Explicitly OUT OF SCOPE

- `PATCH /admin/users/{id}/role` (promote USER → SUPERVISOR)
- Delete / disable user endpoints
- Email notifications for organizer credentials
- Frontend admin panel (`docs/05_frontend.md`)

## 14. Implementation order

1. `settings.py` + `.env.example`
2. `user_admin_service.py` + `schemas/users.py`
3. `admin_users.py` + `main.py`
4. `bootstrap_users.py`; update `seed.py` password resolution
5. Manuals + `api_v1.yaml`
6. Tests + full pytest

## 15. Handoff

Append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Coder (1.6 bootstrap users)
- STATUS: READY_FOR_TEST
- Files: user_admin_service, admin_users, bootstrap_users, .env.example, manuals/BOOTSTRAP_USERS.md, ...
- Verified: pytest tests/ -> N passed
- Next: agent_docs/instructions/tester_1.6.md
```
