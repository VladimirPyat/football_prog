# Test Report — Stage 1.12 Fix (B11/B12)

**Date:** 2026-06-27  
**Tester:** @Tester  
**Verdict:** **TEST_PASS** (re-verified after purge/lock fix)  
**Spec:** `agent_docs/instructions/tester_1.12_fix.md`

## Environment

| Flag | Value |
|------|-------|
| `ENFORCE_PASSWORD_SETUP` | `true` |
| `SUPERVISOR_TRAINING_MODE` | `true` |
| `CONTEST_DELETE_GRACE_SECONDS` | `0` |
| `CONTEST_RESTORE_WINDOW_SECONDS` | `3600` |
| `FRONTEND_BASE_URL` | `http://127.0.0.1:3000` |

Bootstrap: `alembic upgrade head`, `load_test_data.py --reset`, `bootstrap_users.py`.

## Summary (RU)

Этап 1.12 закрыт: auth/setup, training lifecycle, restore, dev-скрипты и purge при старте конкурса проходят. Purge/lock ordering исправлен (@Coder post-test).

## Results table

| Tag | Area | Result |
|-----|------|--------|
| `[INVITE-OUT]` | Invite shape | **PASS** |
| `[SETUP-PREVIEW]` | setup-preview | **PASS** |
| `[SETUP-COMPLETE]` | complete-setup | **PASS** |
| `[SETUP-IDEMPOTENT]` | Idempotent setup | **PASS** |
| `[LOGIN-GATE]` | Temp login gate | **PASS** |
| `[RESET-REQUEST]` | Password reset | **PASS** |
| `[PURGE-ON-START]` | Purge on start | **PASS** |
| `[PURGE-PENDING-TEMP]` | Purge pending | **PASS** |
| `[PURGE-ACCEPTED]` | Keep accepted | **PASS** |
| `[PURGE-MULTI-CONTEST]` | Multi-contest purge | **PASS** |
| `[LIFE-PAUSE-SUP]` | Supervisor pause/resume | **PASS** |
| `[LIFE-FINISH-TRAIN]` | Finish training gates | **PASS** |
| `[LIFE-DELETE-TRAIN]` | Delete training gates | **PASS** |
| `[RESTORE-WINDOW]` | Snapshot restore | **PASS** |
| `[DEV-GET-UNCONFIRMED]` | dev script export | **PASS** |
| `[DEV-CONFIRM-LIST]` | dev confirm-list | **PASS** |
| `[DEV-CONFIRM-ALL]` | dev confirm-all | **PASS** |
| `[ACCEPT-INVITE]` | complete-setup accept | **PASS** |
| `[ACCEPT-PRED-GUARD]` | Pending pred guard | **PASS** |
| `[ACCEPT-REG]` | Predictions after accept | **PASS** |
| `[ACCEPT-ME-CONTESTS]` | /me/contests | **PASS** |
| `[DOC-CONTRACT]` | api_v1.yaml | **PASS** |
| `[DOC-CONFIG]` | CONFIG.md | **PASS** |
| `[DOC-DEV]` | DEV_SETUP.md | **PASS** |

**Pytest:** 25 collected — **25 passed**  
**Ruff (new tests):** 0 errors

## Blockers

| ID | Status |
|----|--------|
| **B11** | **RESOLVED** |
| **B12** | **RESOLVED** |

B11/B12 marked RESOLVED in `agent_docs/reports/BLOCKED.md` (2026-06-27).

## Tests created/updated

| File | Purpose |
|------|---------|
| `tests/api/stage_112_helpers.py` | Shared fixtures/helpers |
| `tests/api/test_auth_setup.py` | B11 auth & invite |
| `tests/api/test_participant_purge.py` | Purge on contest start |
| `tests/api/test_contest_restore.py` | B12 lifecycle & restore |
| `tests/api/test_dev_invite_setup.py` | dev_invite_setup CLI |
| `tests/api/test_participant_accept.py` | complete-setup accept path |

## Commands

```bash
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
ENFORCE_PASSWORD_SETUP=true SUPERVISOR_TRAINING_MODE=true \
  CONTEST_DELETE_GRACE_SECONDS=0 CONTEST_RESTORE_WINDOW_SECONDS=3600 \
  uv run pytest tests/api/test_auth_setup.py tests/api/test_participant_purge.py \
    tests/api/test_contest_restore.py tests/api/test_dev_invite_setup.py \
    tests/api/test_participant_accept.py -v
# → 25 passed
uv run ruff check tests/api/test_auth_setup.py tests/api/test_participant_purge.py \
  tests/api/test_contest_restore.py tests/api/test_dev_invite_setup.py \
  tests/api/test_participant_accept.py tests/api/stage_112_helpers.py
# → All checks passed
```
