# Todo backend fix — auth audit, demo user removal, ACTIVE round guard

> **Status:** Done  
> **Scope:** Items 1, 3, 6 from `agent_docs/reports/todo.md`

## 1. Auth audit log (`auth.log`)

- Add `auth_log_file` to `config/settings.py` (default `logs/auth.log`).
- `setup_auth_audit_logging()` in `src/core/auth_audit.py` — dedicated logger, no passwords.
- `AuthAuditMiddleware` on `POST /api/v1/auth/login`: timestamp, client IP, login, HTTP status, outcome (`success` / `failed`).
- Wire in `main.py` when `log_to_file` is enabled.

## 2. Remove demo bootstrap user (item 3)

- Delete `seed_demo_user()` from `src/scripts/bootstrap_users.py`.
- Remove `SEED_DEMO_USER_*` from `config/settings.py` and `.env.example`.
- `load_test_data.py`: hash dev password `user` for CSV users (real contracted logins).
- `finalize_dev_fixture.py`: remove `_ensure_demo_user_accepted` and `e2e_with_published` demo hook.
- Update `tests/scripts/test_finalize_dev_fixture_1_14.py` — assert contracted user `shutov` ACCEPTED.
- Update `manuals/DEV_SETUP.md` test logins table.

## 3. Block ACTIVE round structure edits (item 6)

- `contest_ops.py` and `admin_rounds.py` `update_round`: reject `team1_id` / `team2_id` when round status is `ACTIVE`.
- Add API test `[ACTIVE-ROUND-NO-TEAMS]` in `tests/api/test_operational_gaps_1_4.py`.

## Non-goals

- Docker Compose (deferred).
- Clone wizard (deferred).
- `CONTEST_LOCKED` doc item — closed, no code change.
