# Draft Plan — Stage 1.6: Bootstrap Users & Organizer API

> Planner note: closes gaps identified after Stage 1.5 — no API to assign contest organizer (SUPERVISOR);
> admin credentials defaulted in repo; bootstrap workflow undocumented.

## 1. Problem statement

| Gap | Impact |
|-----|--------|
| `draft_1.md` RBAC: ADMIN should assign SUPERVISOR | No HTTP endpoint; only manual DB / test fixtures |
| `seed_admin_password_hash` default in `settings.py` | Looks like a secret in git; devs unclear how to set real password |
| No `.env.example` | Onboarding friction; bcrypt hash generation undocumented |
| No bootstrap runbook | Ops don't know order: migrate → seed contest → create users |

## 2. Goals

1. **API:** `POST /api/v1/admin/users/supervisor` — ADMIN creates global SUPERVISOR (organizer) account.
2. **CLI:** `src/scripts/bootstrap_users.py` — idempotent ADMIN + optional SUPERVISOR from `.env` (plaintext passwords hashed at runtime).
3. **Config:** `SEED_ADMIN_PASSWORD`, `SEED_SUPERVISOR_*` env vars; `.env.example` with hash-generation one-liner.
4. **Docs:** `manuals/BOOTSTRAP_USERS.md`; sync `CONFIG.md`, `API_GUIDE.md`; update `api_v1.yaml`.

## 3. Non-goals

- Full admin UI for user CRUD (future frontend stage).
- Promote existing USER → SUPERVISOR via separate endpoint (optional later).
- Email invite for organizers (same as participants — out of scope).
- Changing RBAC matrix for contest operations.

## 4. API contract

### `POST /api/v1/admin/users/supervisor`

| Field | Type | Required |
|-------|------|----------|
| `login` | string | yes |
| `password` | string | yes |
| `first_name` | string | yes |
| `last_name` | string | yes |
| `is_temp_password` | bool | no (default `false`) |

| Caller | HTTP |
|--------|------|
| ADMIN | 200 + `{ user: UserOut }` |
| SUPERVISOR / USER | 403 |
| Duplicate login | 400 `VALIDATION_ERROR` |

Password stored as bcrypt hash via `hash_password()` — no separate server-side “hashing key”.

## 5. Bootstrap script

**Path:** `src/scripts/bootstrap_users.py`

| Step | Action |
|------|--------|
| 1 | Read settings from `.env` via `get_settings()` |
| 2 | Create ADMIN if login missing (`SEED_ADMIN_PASSWORD` or `SEED_ADMIN_PASSWORD_HASH`) |
| 3 | Optionally create SUPERVISOR (`SEED_SUPERVISOR_*`) — **comment out call when admin UI ships** |
| 4 | Enroll ADMIN in first `contests` row as `contest_participants` (if contest exists) |

Idempotent: existing logins skipped; passwords **not** updated on re-run.

**Typical server order:**

```bash
uv run alembic upgrade head
uv run python src/scripts/seed.py
uv run python src/scripts/bootstrap_users.py
```

## 6. Environment variables (new / clarified)

| Variable | Purpose |
|----------|---------|
| `SEED_ADMIN_PASSWORD` | Plaintext — hashed at bootstrap/seed time (preferred) |
| `SEED_ADMIN_PASSWORD_HASH` | Precomputed bcrypt (alternative) |
| `SEED_SUPERVISOR_LOGIN` | Optional organizer login |
| `SEED_SUPERVISOR_PASSWORD` | Plaintext supervisor password |
| `SEED_SUPERVISOR_PASSWORD_HASH` | Precomputed bcrypt alternative |

Hash one-liner for docs:

```bash
uv run python src/scripts/hash_password.py 'your-password'
```

## 7. Files to create/modify

```
src/services/user_admin_service.py       # NEW
src/schemas/users.py                     # NEW
src/api/v1/admin_users.py                # NEW
main.py                                  # register router
config/settings.py                       # new env fields
src/scripts/bootstrap_users.py           # NEW
src/scripts/seed.py                      # use SEED_ADMIN_PASSWORD when set
.env.example                             # NEW (repo root)
manuals/BOOTSTRAP_USERS.md               # NEW
manuals/{CONFIG,API_GUIDE,README}.md     # sync
agent_docs/contracts/api_v1.yaml         # add endpoint + schemas
tests/api/test_admin_users.py            # NEW
agent_docs/instructions/coder_1.6.md
agent_docs/instructions/tester_1.6.md
agent_docs/progress/stage_1.md           # append
```

## 8. Test scope (1.6)

| ID | Scenario |
|----|----------|
| `[BOOT-ADMIN]` | bootstrap creates ADMIN when env set |
| `[BOOT-SUP]` | bootstrap creates SUPERVISOR when env set |
| `[BOOT-IDEM]` | second run skips existing logins |
| `[API-SUP-CREATE]` | ADMIN POST supervisor → 200, can login |
| `[API-SUP-RBAC]` | SUPERVISOR POST supervisor → 403 |
| `[API-SUP-DUP]` | duplicate login → 400 `VALIDATION_ERROR` |

Regression: full `pytest tests/ --ignore=tests/manual` green.

## 9. Retirement path

When admin UI manages users:

1. Comment `await seed_supervisor_user(...)` in `bootstrap_users.py`.
2. Remove script from production deploy playbook (keep ADMIN break-glass optional).
3. Organizers created only via `POST /admin/users/supervisor` or future UI.

## 10. Sequencing

**Prerequisite:** Stage 1.5 `TEST_PASS`.

1.6 is independent of frontend (`docs/05_frontend.md`); unblocks first real-server deploy with non-default credentials.
