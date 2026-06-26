# Coder Instructions — Stage 1.12: Auth Links, Participant Accept, Password Setup (B11, B12)

> **Status gate:** `INSTRUCTIONS_READY`
> **Blockers:** `agent_docs/reports/BLOCKED.md` — B11, B12
> **Related:** `agent_docs/instructions/coder_2.1.2_fix_supervisor.md` (supervisor UI fixes)
> **Follow-up (separate):** §9 — frontend `/admin` → `/supervisor` rename
> **Contracts to update after impl:** `agent_docs/contracts/api_v1.yaml`, `frontend_api_integration.md`, `manuals/API_GUIDE.md`, `manuals/CONFIG.md`, `manuals/DEV_SETUP.md`

---

## 1. Objective

| ID | Deliverable |
|----|-------------|
| **B11** | Invite + password setup via signed link; login + temp password + link in letter; purge PENDING on contest start; dev confirm scripts |
| **B12** | Supervisor lifecycle control; **training mode** enables finish/delete + contest restore window |
| **NEW** | Password reset by email (same link machinery) |
| **NEW** | Config flags for dev/training (`enforce_password_setup`, `supervisor_training_mode`, restore window) |

**Non-goals:**

- Real SMTP (links in modal / dev scripts only)
- Platform ADMIN dashboard (future `/admin/*` UI for global ops only)

---

## 2. Auth & invite model (LOCKED)

### 2.1 Login generation

| Source | Behaviour |
|--------|-----------|
| Supervisor form | Optional «Логин» |
| Backend default | From email local-part, uniquify (`ivanov`, `ivanov1`, …) — `add_participant()` |

**Letter / modal payload (invite + reset):** login + temp_password + setup_url.

### 2.2 Password state

| Concept | DB |
|---------|-----|
| Not set by user | `is_temp_password = true` |
| Set | `is_temp_password = false` |

API alias: `needs_password_setup`.

### 2.3 `POST /auth/complete-setup`

```json
{ "token": "<signed>", "new_password": "<optional>" }
```

Idempotent; sets password when provided; `PENDING→ACCEPTED` when `contest_id` in token.

Token payload: `{ sub, contest_id?, purpose: "setup_password", exp }`.

### 2.4 `POST /auth/request-password-reset`

Always 200; if email found → new temp password + new token + setup_url (same triple as invite).

**Expired invite link:** supervisor re-sends invite (`POST …/participants` with same email) or user uses «Восстановить пароль» — new token issued; no separate re-invite endpoint in v1.

### 2.5 Frontend `/auth/setup` (LOCKED)

Link format: `{FRONTEND_BASE_URL}/auth/setup?token=…`

`GET /auth/setup-preview?token=…` → `mode`:

| `enforce_password_setup` | `mode` | UI |
|--------------------------|--------|-----|
| `true` | `password_form` | Form → `complete-setup` with `new_password` |
| `false` | `confirm_only` | «Подтвердите участие; войдите с паролем из письма» → `complete-setup` without password |

Success → redirect to login (no auto-JWT).

### 2.6 Login gate

| `enforce_password_setup` | Temp password login |
|--------------------------|---------------------|
| `true` | `403 PASSWORD_SETUP_REQUIRED` |
| `false` | `200` + existing `/change-password` path |

### 2.7 Config — password setup

```python
enforce_password_setup: bool = True  # ENFORCE_PASSWORD_SETUP — false for dev/E2E
```

### 2.8 Purge unconfirmed on contest start

On first `DRAFT→RUNNING`: delete participants where `PENDING` + `is_temp_password` + `role=USER` (reuse `remove_participant` orphan logic). **No algorithm exists today** — add `purge_unconfirmed_participants()`.

### 2.9 Invite response

```python
class ParticipantInviteOut(BaseModel):
    user_id: int
    login: str
    temp_password: str
    status: str
    setup_url: str
```

No server-side file append on invite.

---

## 3. B12 — Supervisor lifecycle & training mode (LOCKED)

### 3.1 Role matrix

| Endpoint | Default (prod) | `supervisor_training_mode=true` |
|----------|----------------|----------------------------------|
| `POST …/pause` | SUPERVISOR + ADMIN | SUPERVISOR + ADMIN |
| `POST …/resume` | SUPERVISOR + ADMIN | SUPERVISOR + ADMIN |
| `POST …/finish` | ADMIN only | **SUPERVISOR + ADMIN** |
| `DELETE …` (confirm DELETE) | ADMIN only | **SUPERVISOR + ADMIN** |
| `POST …/restore` (new) | — | **SUPERVISOR + ADMIN** (within window) |

Implement via shared dependency that checks `get_settings().supervisor_training_mode` for finish/delete/restore.

### 3.2 Training mode settings

```python
# config/settings.py
supervisor_training_mode: bool = False       # SUPERVISOR_TRAINING_MODE
contest_restore_window_seconds: int = 86400  # CONTEST_RESTORE_WINDOW_SECONDS (24h)
```

When `supervisor_training_mode=true` (document in `.env.example` for local dev):

- Supervisor may finish and delete without asking ADMIN.
- **`contest_allow_instant_delete`** effectively `true` for supervisor delete path (skip grace wait), **or** set `contest_delete_grace_seconds=0` only when training mode — pick one, document in CONFIG.
- Restore window active (§3.3).

When `false` (production default): finish/delete remain ADMIN-only; restore disabled or ADMIN-only.

### 3.3 Contest restore after delete

**Today:** `DELETE …/contests/{id}` calls `delete_contest_data()` → `reset_contest_to_draft()` — wipes operational data, contest row stays as empty DRAFT. **No undo.**

**Add restore snapshot before wipe:**

1. Before `wipe_contest_data`, serialize restorable payload to JSON:
   - contest scalar fields + `rules_json`
   - teams, participants (user_ids only), rounds, matches (no predictions/scores required for training restore — document minimal set: teams + rounds + matches + participants)
2. Store in new table `contest_restore_snapshots`:

```python
class ContestRestoreSnapshot(BaseModel):
    contest_id: int  # PK FK contests.id
    snapshot_json: dict
    deleted_at: datetime
    expires_at: datetime
    deleted_by_user_id: int | null
```

3. After wipe, row remains until `expires_at` or successful restore.

**New endpoint:**

```
POST /api/v1/contests/{contest_id}/restore
→ 200 { restored: true }  if snapshot exists and now < expires_at
→ 404 / 410 if no snapshot or expired
```

Restore: replay snapshot into contest (replace current DRAFT state); delete snapshot row.

**UI (when training mode):** after delete, toast «Конкурс сброшен. Восстановление доступно N часов» + button on lifecycle panel if snapshot exists.

**Tests:** delete → restore within window → teams back; after expiry → 410.

### 3.4 Files

- `src/api/v1/contests.py` — role deps + restore route
- `src/services/contest_lifecycle_service.py` — snapshot hook in delete path
- `src/services/contest_restore_service.py` (new)
- Alembic migration for `contest_restore_snapshots`

---

## 4. Dev scripts — confirm links without SMTP (LOCKED)

**Location:** all dev tooling under `src/scripts/` (prod scripts later in a different place — out of scope).

| Artifact | Path | Git |
|----------|------|-----|
| CLI script | `src/scripts/dev_invite_setup.py` | committed |
| Editable export list | `src/scripts/dev_unconfirmed.tsv` | committed OK (dev convenience) |
| Generated tokens/links | `src/scripts/.tokens` | **gitignored** |

Add to `.gitignore`:

```
src/scripts/.tokens
```

### 4.1 Subcommands

```bash
# Export PENDING + is_temp_password users from DB
uv run python src/scripts/dev_invite_setup.py get-unconfirmed \
  [--contest-id 2] \
  [--out src/scripts/dev_unconfirmed.tsv] \
  [--links-out src/scripts/.tokens]   # optional: regenerate setup_url per row

# Confirm rows from TSV (# lines skipped)
uv run python src/scripts/dev_invite_setup.py confirm-list \
  [--file src/scripts/dev_unconfirmed.tsv] \
  [--password 'DevPass123!']

# Export + confirm all
uv run python src/scripts/dev_invite_setup.py confirm-all \
  [--contest-id 2] \
  [--password 'DevPass123!']
```

**`.tokens` format** (one JSON object per line, append on `get-unconfirmed --links-out`):

```json
{"user_id":42,"contest_id":2,"login":"ivanov","setup_url":"http://127.0.0.1:3000/auth/setup?token=…","exported_at":"…"}
```

Operator may copy URLs from `.tokens` or run `confirm-list` on TSV (script re-issues tokens at confirm time — preferred).

**No backend hooks** on `POST /participants`.

Document workflow in `manuals/DEV_SETUP.md`.

---

## 5. Backend checklist

| # | Task |
|---|------|
| 1 | Settings: `frontend_base_url`, `setup_token_expire_hours`, `enforce_password_setup`, `supervisor_training_mode`, `contest_restore_window_seconds` |
| 2 | `src/core/setup_tokens.py` |
| 3 | `auth_setup_service.py` — `complete_setup`, preview |
| 4 | Auth routes: `complete-setup`, `setup-preview`, `request-password-reset`, login gate |
| 5 | Invite `setup_url` in `ParticipantInviteOut` |
| 6 | B12 roles + restore snapshot + `POST …/restore` |
| 7 | `purge_unconfirmed_participants` on first activate |
| 8 | `src/scripts/dev_invite_setup.py` |
| 9 | Migration `contest_restore_snapshots` |
| 10 | Tests: auth setup, purge, supervisor pause/finish/delete/restore, training mode off/on |

---

## 6. Frontend checklist (1.12 minimal)

| # | Task |
|---|------|
| 1 | `/auth/setup` page |
| 2 | Login: «Восстановить пароль» |
| 3 | `PASSWORD_SETUP_REQUIRED` handling |
| 4 | Invite modal: login + temp_password + setup_url |
| 5 | Lifecycle panel: finish/delete for supervisor when training mode (read flag from API or env `NEXT_PUBLIC_SUPERVISOR_TRAINING_MODE`) |

Supervisor UI fixes (parameters, teams, rounds, results): `coder_2.1.2_fix_supervisor.md`.

---

## 7. E2E note (LOCKED)

Recommend for local / CI `.env`:

```bash
ENFORCE_PASSWORD_SETUP=false
SUPERVISOR_TRAINING_MODE=true
CONTEST_DELETE_GRACE_SECONDS=0
```

Migrate Playwright from `change-password` to `complete-setup` when stable.

---

## 8. Verification

```bash
uv run pytest tests/api/test_participant_accept.py tests/api/test_auth_setup.py \
  tests/api/test_participant_purge.py tests/api/test_contest_restore.py -v
uv run ruff check src/ && uv run mypy src/
cd frontend && npm run lint && npm run type-check
```

Manual:

1. Invite → modal shows login + temp password + link.
2. `/auth/setup` works (both modes).
3. `dev_invite_setup.py get-unconfirmed` → edit TSV → `confirm-list`.
4. Purge on first round activate.
5. Training mode: supervisor finish → pause → delete → restore within window.
6. Training mode off: supervisor finish → 403.

After `TEST_PASS`: resolve B11/B12 in `BLOCKED.md`; update contracts.

---

## 9. Follow-up — full admin → supervisor rename (separate commit)

**Agreed:** contest-scoped `admin` in API and UI is organizer (supervisor) functionality — rename **now** while no platform admin scenarios exist (`docs/04_supervisor_scenario.md` only; admin scenarios TBD).

**Instruction:** [`coder_1.13_supervisor_rename.md`](coder_1.13_supervisor_rename.md)

| Scope | Change |
|-------|--------|
| API | `…/contests/{id}/admin/*` → `…/contests/{id}/supervisor/*` |
| UI | `/admin/*` → `/supervisor/*` |
| Keep `/admin/` | Platform ADMIN only (`POST /api/v1/admin/users/supervisor`, future global tools) |

**When:** after 1.12 + 2.1.2 fixes; **one commit**; full pytest + frontend lint + E2E.

Not blocking 1.12 backend work.

---

## 10. File checklist

| Action | Path |
|--------|------|
| NEW | `src/core/setup_tokens.py` |
| NEW | `src/services/auth_setup_service.py` |
| NEW | `src/services/contest_restore_service.py` |
| NEW | `src/scripts/dev_invite_setup.py` |
| NEW | `alembic/versions/*_contest_restore_snapshots.py` |
| EDIT | `src/api/v1/auth.py`, `contests.py`, `contest_setup_service.py`, `contest_lifecycle_service.py` |
| EDIT | `config/settings.py`, `.env.example`, `.gitignore` |
| EDIT | `frontend` auth + invite + lifecycle (§6) |
| EDIT | `manuals/CONFIG.md`, `manuals/DEV_SETUP.md` |
| DEFER | Full admin→supervisor rename — `coder_1.13_supervisor_rename.md` (§9) |
