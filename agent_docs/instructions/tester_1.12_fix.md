# Tester Instructions — Stage 1.12 Fix: Auth Links, B11/B12, Training Mode

> **Status gate:** @Coder `READY_FOR_TEST` for 1.12 fix.
> **Coder spec:** `agent_docs/instructions/coder_1.12_fix.md`
> **Prerequisite:** Stage 1.10+ backend green; frontend 2.3 shell exists.
> **Report:** `agent_docs/reports/test_1.12_fix.md` (NEW, Russian summary + PASS/FAIL table)
> **Strategy:** Pytest (API + unit) + targeted manual smoke; minimal frontend checks for §6 deliverables. **Do not modify** `src/` unless new blocker.

---

## 1. Objective

Verify Stage **1.12 fix** closes **B11** and **B12** in `agent_docs/reports/BLOCKED.md`:

| ID | Area |
|----|------|
| **B11** | Invite returns `login` + `temp_password` + `setup_url`; `complete-setup` + `setup-preview`; password reset request; purge PENDING on contest start; `dev_invite_setup.py` |
| **B12** | Supervisor `pause`/`resume`; training mode → supervisor `finish`/`delete`/`restore` |
| **CFG** | `enforce_password_setup`, `supervisor_training_mode`, `contest_restore_window_seconds` |

**Non-goals:**

- Full supervisor UI matrix → `tester_2.1.2_fix_supervisor.md`
- Route rename `/admin` → `/supervisor` → `tester_1.13_supervisor_rename.md`
- Real SMTP
- Platform ADMIN dashboard

---

## 2. Test environment

### 2.1 Base bootstrap

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

For lifecycle/purge tests use **fresh DRAFT contest** via API (`empty_api` / supervisor token) — not locked contest `id=1` unless test says so.

### 2.2 Configuration (not in root `.env`)

**Root `.env` — secrets only:** `SEED_ADMIN_PASSWORD`, `SEED_SUPERVISOR_PASSWORD` (see `.env.example`).

Tuning flags (`ENFORCE_PASSWORD_SETUP`, `SUPERVISOR_TRAINING_MODE`, `FRONTEND_BASE_URL`, …) use **`config/settings.py` defaults** locally. Pytest injects env via `monkeypatch` (`tests/api/stage_112_helpers.py`).

For ad-hoc API runs, prefix the command (do **not** add to `.env`):

```bash
ENFORCE_PASSWORD_SETUP=true SUPERVISOR_TRAINING_MODE=true \
  CONTEST_DELETE_GRACE_SECONDS=0 CONTEST_RESTORE_WINDOW_SECONDS=3600 \
  uv run pytest tests/api/test_contest_restore.py -v
```

Re-run subset with `ENFORCE_PASSWORD_SETUP=false` via shell prefix for legacy/E2E compatibility checks (§5.6).

### 2.3 Frontend (minimal §6)

```bash
cd frontend && cp .env.local.example .env.local
npm run dev   # :3000
```

---

## 3. Scope — files you may create

```
tests/api/test_auth_setup.py           # NEW or extend — Coder may add; extend if gaps
tests/api/test_participant_purge.py    # NEW — Coder may add
tests/api/test_contest_restore.py      # NEW — Coder may add
tests/api/test_participant_accept.py   # UPDATE for complete-setup path
agent_docs/reports/test_1.12_fix.md
```

**Do NOT modify** `src/` unless blocker → `agent_docs/reports/BLOCKED.md`.

---

## 4. B11 — Auth & invite

### 4.1 `[INVITE-OUT]` Invite response shape

Supervisor on **unlocked DRAFT** contest:

1. `POST /api/v1/contests/{cid}/participants` with email, names.
2. Assert `200` body contains: `user_id`, `login`, `temp_password` (non-empty), `status: "PENDING"`, `setup_url` (contains `/auth/setup?token=`).

### 4.2 `[SETUP-PREVIEW]` Token preview

1. Extract token from `setup_url`.
2. `GET /api/v1/auth/setup-preview?token=…` → `200` with `login`, `mode` (`password_form` or `confirm_only`), `already_completed: false`.

### 4.3 `[SETUP-COMPLETE]` Accept + set password

With `ENFORCE_PASSWORD_SETUP=true`:

1. `POST /api/v1/auth/complete-setup` `{ token, new_password: "NewSecure1!" }` → `200`, `accepted: true`.
2. `GET /contests/{cid}/participants` → user `status == "ACCEPTED"`.
3. Login with **new** password → `200` + JWT, `is_temp_password: false`.

### 4.4 `[SETUP-IDEMPOTENT]` Repeat complete-setup

Same token or second call after success → `200` with `already_completed: true` (no 500).

### 4.5 `[LOGIN-GATE]` Temp password blocked when enforce=true

After invite, **before** complete-setup:

1. `POST /auth/login` with `login` + `temp_password` → **403**, `code == "PASSWORD_SETUP_REQUIRED"`.

With `ENFORCE_PASSWORD_SETUP=false`:

1. Same login → **200**, `is_temp_password: true` (legacy path to change-password).

### 4.6 `[RESET-REQUEST]` Password reset request

1. `POST /auth/request-password-reset` `{ email: known }` → **always 200** (privacy message).
2. Unknown email → still **200** (same message shape).
3. If Coder exposes setup_url in dev/logs: new token works via complete-setup.

### 4.7 `[PURGE-ON-START]` Unconfirmed purge

On fresh DRAFT contest:

1. Invite user A (do **not** complete setup).
2. Invite user B → complete-setup → ACCEPTED.
3. Create teams + activate first round → contest `RUNNING`.
4. Assert: user A gone from participants (and user row deleted if orphan); user B remains ACCEPTED.

Tag subcases:

| Tag | Setup | Expected |
|-----|-------|----------|
| `[PURGE-PENDING-TEMP]` | PENDING + is_temp_password | removed |
| `[PURGE-ACCEPTED]` | ACCEPTED | kept |
| `[PURGE-MULTI-CONTEST]` | PENDING in C1, ACCEPTED in C2 | C1 row removed, user kept |

---

## 5. B12 — Lifecycle & training mode

### 5.1 `[LIFE-PAUSE-SUP]` Supervisor pause/resume (always)

With `supervisor_training_mode=false`:

1. Contest `RUNNING`.
2. Supervisor `POST /contests/{id}/pause` → **200**.
3. Supervisor `POST /contests/{id}/resume` → **200**.
4. USER token → **403** on both.

### 5.2 `[LIFE-FINISH-TRAIN]` Finish — training mode gate

| `supervisor_training_mode` | Actor | `POST …/finish` |
|--------------------------|-------|-----------------|
| `false` | SUPERVISOR | **403** |
| `false` | ADMIN | **200** |
| `true` | SUPERVISOR | **200** |

### 5.3 `[LIFE-DELETE-TRAIN]` Delete — training mode gate

Contest **PAUSED** (instant delete if grace=0 + training):

| Mode | Actor | `DELETE …` + `{confirm:"DELETE"}` |
|------|-------|-----------------------------------|
| `false` | SUPERVISOR | **403** |
| `true` | SUPERVISOR | **200**, contest reset to DRAFT |

### 5.4 `[RESTORE-WINDOW]` Snapshot restore

With `supervisor_training_mode=true`, contest with teams + round data:

1. Delete (wipe to DRAFT).
2. `POST /contests/{id}/restore` within window → **200**, teams/rounds restored per snapshot spec.
3. Second restore → **404/410** (snapshot consumed).
4. After `expires_at` (mock time or short window in test) → **410**.

---

## 6. Dev scripts

### 6.1 `[DEV-GET-UNCONFIRMED]`

```bash
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id {cid} \
  --out src/scripts/dev_unconfirmed.tsv
```

Assert TSV has header + PENDING rows; optional `--links-out src/scripts/.tokens` creates gitignored file.

### 6.2 `[DEV-CONFIRM-LIST]`

1. Comment one row in TSV with `#`.
2. `confirm-list --file src/scripts/dev_unconfirmed.tsv` → only uncommented rows ACCEPTED.
3. Re-run → skipped / idempotent (no error exit).

### 6.3 `[DEV-CONFIRM-ALL]`

Fresh invites → `confirm-all` → all PENDING+temp become ACCEPTED.

---

## 7. Frontend smoke (minimal)

| ID | Check |
|----|-------|
| `[UI-SETUP-PAGE]` | Open `setup_url` in browser → form or confirm_only per config |
| `[UI-INVITE-MODAL]` | Supervisor invite → modal shows login + temp password + link (if 2.1.2 merged, else API-only OK) |
| `[UI-PASSWORD-GATE]` | Login with temp when enforce=true → UI handles 403 (if 2.1.2 merged) |

---

## 8. Documentation audit

| ID | Check |
|----|-------|
| `[DOC-CONTRACT]` | `api_v1.yaml`: `complete-setup`, `setup-preview`, `request-password-reset`, `restore`, `ParticipantInviteOut.setup_url` |
| `[DOC-CONFIG]` | `manuals/CONFIG.md`: new env vars |
| `[DOC-DEV]` | `manuals/DEV_SETUP.md`: dev_invite_setup workflow |
| `[DOC-BLOCKED]` | B11/B12 marked RESOLVED on PASS |

---

## 9. Regression

```bash
uv run pytest tests/api/test_participant_accept.py tests/api/test_auth_setup.py \
  tests/api/test_participant_purge.py tests/api/test_contest_restore.py -v
uv run pytest tests/api/ -q --tb=line -x   # full API if time permits
uv run ruff check src/ tests/
uv run mypy src/
```

---

## 10. Exit criteria

| Gate | Requirement |
|------|-------------|
| **TEST_PASS** | All §4–§6 tags PASS; no open B11/B12 blockers |
| **TEST_FAIL** | Report in `test_1.12_fix.md` with failing tag, request/response, assign @Coder |

**Execution order vs other testers:** run **before** `tester_1.13_supervisor_rename.md` (paths still `/admin/` in API during 1.12 test).
