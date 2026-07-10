# Local Development Setup (Backend + Frontend)

One-time and day-to-day workflow for running the **Football Predictions Contest** stack locally.

**Related docs:** [CONFIG.md](CONFIG.md) · [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) · [API_GUIDE.md](API_GUIDE.md) · Stage 2 frontend: `agent_docs/instructions/coder_2.1.md`

> **Docker Compose:** not provided yet (Stage 3). Use the bootstrap script below or run commands manually.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|--------|
| **Python** | ≥ 3.12 | `python3 --version` |
| **[uv](https://docs.astral.sh/uv/)** | latest | `uv --version` |
| **Node.js** | ≥ 20 LTS (18+ may work) | `node --version` |
| **npm** | ≥ 10 | `npm --version` |

Optional for E2E (Stage 2.1+ tester): Playwright browsers — **one-time**:

```bash
cd frontend && npm run playwright:install
```

Browsers are stored in `frontend/.playwright-browsers/` (gitignored, reused by agents).  
`playwright.config.ts` sets `PLAYWRIGHT_BROWSERS_PATH` automatically — do **not** use bare `npx playwright install` (sandbox may download to ephemeral `/tmp/cursor-sandbox-cache/`).

---

## Quick start (recommended)

From the repository root:

```bash
# 1. Environment (once)
cp .env.example .env
# Edit .env: set SEED_SUPPORT_PASSWORD and SEED_SUPERVISOR_PASSWORD (see .env.example)

# 2. Bootstrap DB + start API & UI (one command)
uv run python src/scripts/dev_setup.py --run
# → http://127.0.0.1:3000/  (UI)
# → http://127.0.0.1:8000/health  (API)
# Press Ctrl+C to stop both servers
```

On first `--run`, the script also creates `frontend/.env.local` from `.env.local.example` and runs `npm install` if `node_modules/` is missing.

### Manual start (two terminals)

Use when you prefer separate processes or DB is already bootstrapped:

```bash
# Bootstrap only (no servers)
uv run python src/scripts/dev_setup.py

# Terminal 1 — API
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — UI
cd frontend
cp .env.local.example .env.local   # once
npm install                        # once
npm run dev                        # http://127.0.0.1:3000
```

**Restart servers without resetting DB:**

```bash
uv run python src/scripts/dev_setup.py --run-only
```

**Verify API:** `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`

**Verify public contest list (B2):** after full setup, contest id `1` is **RUNNING** → `curl -s http://127.0.0.1:8000/api/v1/contests/public`

---

## Bootstrap script — `src/scripts/dev_setup.py`

Automates migrations, test data, admin users, and dev contest state.

```bash
uv run python src/scripts/dev_setup.py              # full frontend dev DB (default)
uv run python src/scripts/dev_setup.py --run        # full setup + start API (:8000) & UI (:3000)
uv run python src/scripts/dev_setup.py --run-only     # start servers only (skip DB setup)
uv run python src/scripts/dev_setup.py --minimal    # empty contest + admin only (no CSV loader)
uv run python src/scripts/dev_setup.py --no-reset   # full without wiping loader tables first
uv run python src/scripts/dev_setup.py --check      # prerequisites only, no DB changes
uv run python src/scripts/dev_setup.py --check-ports  # verify :8000 and :3000 are free [UPDATED]
uv run python src/scripts/dev_setup.py --ensure-running-only          # manual fixture after loader
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e    # E2E: round 10 ACTIVE only
uv run python src/scripts/dev_setup.py --finalize-fixture-only      # repair fixture on existing DB
uv run python src/scripts/dev_setup.py --help
```

### What `--run` / `--run-only` do [UPDATED]

1. **`assert_dev_ports_free`** — abort if API `:8000` or UI `:3000` already in use (see `--check-ports`)
2. Ensure `frontend/.env.local` exists (copy from `.env.local.example` if missing)
3. Run `npm install` in `frontend/` when `node_modules/` is absent
4. Start **API**: `uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000`
5. Start **UI**: `npm run dev` in `frontend/` → `http://127.0.0.1:3000`
6. Poll `/health` and UI root until ready (or timeout ~90s)
7. On **Ctrl+C** or SIGTERM — stop both child processes

`--run` = default full setup, then steps 1–7. `--run-only` = steps 1–7 without touching the DB.

**Port check only:**

```bash
uv run python src/scripts/dev_setup.py --check-ports
# ✅ API: 127.0.0.1:8000 is free
# ❌ UI: 127.0.0.1:3000 is in use  → exit 1
```

### What `--full` (default) does

1. `uv sync` (install Python deps from `pyproject.toml`)
2. Warn if `.env` missing (copy from `.env.example` manually)
3. `alembic upgrade head`
4. `load_test_data.py --reset` — contest **id=1**, 16 teams, 10 users (`user`/`user`, …), rounds 1–10 from CSV
5. `bootstrap_users.py` — **after loader** (loader `--reset` deletes all `users`; bootstrap restores `support` / `supervisor` from `.env`)
6. **Dev contest state** — contest `1` → `RUNNING` + `is_locked=true`
7. **`finalize_dev_fixture`** (manual profile, default) — rounds **1–9** `PUBLISHED` with `scores` (90 rows ≡ `expected_scores.csv`), round **10** `CALCULATED` (10 scores, not published), round **11** `CLOSED` (awaiting results entry)

| Round | Status after finalize | `scores` rows |
|-------|----------------------|---------------|
| 1–9 | `PUBLISHED` | 10 each (90 total) |
| 10 | `CALCULATED` | 10 |
| 11 | `CLOSED` | 0 |

**E2E profile** (`--e2e`): skip finalize; round **10** stays `ACTIVE` with a future deadline (prediction / 24h-rule tests). Use:

```bash
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
```

**Repair existing DB** without full reset:

```bash
uv run python src/scripts/dev_setup.py --finalize-fixture-only
```

### What `--minimal` does

1–3 as above, then `seed.py` + `bootstrap_users.py` (no CSV loader, no `user/user` test login).

Use `--minimal` for a blank SETUP-phase contest; use **`--full`** for Stage 2 frontend / E2E.

### Dev fixture — `finalize_dev_fixture` (Stage 1.14)

Script: `src/scripts/finalize_dev_fixture.py`. Called automatically at the end of **default full setup** and `--ensure-running-only` (unless `--e2e`).

**Purpose:** after CSV loader, contest `id=1` exposes all meaningful round phases for supervisor manual QA — not only `CLOSED` (1–9) + `ACTIVE` (10).

| Step | What happens |
|------|----------------|
| Rounds 1–9 | `calculate_round` → `PUBLISHED`; `scores` rows ≡ `expected_scores.csv` (90 total) |
| Round 10 | Synthetic match results → `CALCULATED` (10 scores); **not** published |
| Round 11 | New round `CLOSED`, deadline passed (ref. **2026-06-27**), 8 `SCHEDULED` matches, 0 scores |
| Contest | `RUNNING` + `is_locked=true` |
| Participants | Bootstrap-only users (`admin`, demo `user`) set to `PENDING` so scoring stays 10 users/round |

**Profiles:**

| Profile | Command | Round 10 | Rounds 1–9 | Round 11 |
|---------|---------|----------|------------|----------|
| Manual (default) | `dev_setup.py` or `--ensure-running-only` | `CALCULATED` | `PUBLISHED` + scores | `CLOSED` |
| E2E | `--ensure-running-only --e2e` | `ACTIVE`, future deadline | `CLOSED`, no finalize | not created |
| Repair only | `--finalize-fixture-only` | (re-applies manual table) | | |

**Verify fixture (SQLite):**

```sql
SELECT r.number, r.status,
       (SELECT COUNT(*) FROM scores s WHERE s.round_id = r.id) AS score_rows
FROM rounds r
WHERE r.contest_id = 1
ORDER BY r.number;
-- Expected: 1–9 PUBLISHED (10 each), 10 CALCULATED (10), 11 CLOSED (0); total scores = 100
```

Status meanings and UI walkthrough: [STATUS_REFERENCE.md](STATUS_REFERENCE.md) §2.3 (dev fixture table).

**Pytest isolation:** `load_test_data.py` alone keeps rounds 1–9 `CLOSED` and round 10 `ACTIVE` — finalize runs only from `dev_setup`, not from the loader.

**Stage 2.3.2 manual QA:** after supervisor walkthrough on `/admin/rounds` or `/admin/results`, re-run `--finalize-fixture-only` before handoff to restore rounds 9=`PUBLISHED`, 10=`CALCULATED`, 11=`CLOSED` (see [STATUS_REFERENCE.md](STATUS_REFERENCE.md) §2.3).

---

## Manual steps (without script)

```bash
uv sync
cp .env.example .env   # edit passwords

uv run alembic upgrade head

# Full dev data (order matters — bootstrap AFTER loader):
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only   # RUNNING + finalize fixture (manual profile)

# Same as three lines above in one shot:
# uv run python src/scripts/dev_setup.py

# Minimal alternative:
# uv run python src/scripts/seed.py
# uv run python src/scripts/bootstrap_users.py
```

---

## Frontend environment

Create `frontend/.env.local` (see `frontend/.env.local.example` after scaffold):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Use `127.0.0.1` consistently (matches Playwright `baseURL` in tester instructions). `localhost` also works if CORS allows it (default `CORS_ORIGINS=["*"]`).

---

## Test logins (after `--full` setup)

| Role | Login | Password | Source |
|------|-------|----------|--------|
| USER (contracted) | `shutov` (or any CSV login) | `user` | `load_test_data.py` — all contracted users share dev password `user` |
| SUPERVISOR | `supervisor` | value from `.env` `SEED_SUPERVISOR_PASSWORD` | `bootstrap_users.py` |
| Support | `support` | value from `.env` `SEED_SUPPORT_PASSWORD` | `bootstrap_users.py` |

> **Note:** For new participants use supervisor invite UI (`/admin/settings/participants`) or `dev_invite_setup.py confirm-all`. Playwright E2E provisions a dedicated user via `playwright.global-setup.ts`.

Do **not** commit `.env` or real passwords.

---

## Running tests

### Backend

```bash
uv run pytest tests/ --ignore=tests/manual -q
```

Stage 1.12 regression (auth setup, purge, training restore):

```bash
ENFORCE_PASSWORD_SETUP=true SUPERVISOR_TRAINING_MODE=true \
  CONTEST_DELETE_GRACE_SECONDS=0 CONTEST_RESTORE_WINDOW_SECONDS=3600 \
  uv run pytest tests/api/test_auth_setup.py tests/api/test_participant_purge.py \
    tests/api/test_contest_restore.py tests/api/test_dev_invite_setup.py \
    tests/api/test_participant_accept.py -v
```

### Frontend (after Stage 2.1 scaffold)

```bash
cd frontend
npm run test:unit
npm run lint && npm run type-check && npm run format:check
npm run test:e2e          # requires API on :8000 and UI on :3000
npm run build
```

Lint IDs for tester reports: `[LINT-ESLINT]`, `[LINT-TSC]`, `[LINT-PRETTIER]` — see `agent_docs/instructions/tester_2.1.md` §6.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `bootstrap_users` skips / no support user | Set `SEED_SUPPORT_PASSWORD` in `.env` |
| `GET /contests/public` returns `[]` | Re-run `dev_setup.py` (contest must be **RUNNING**) |
| CORS errors from `:3000` | Ensure `CORS_ORIGINS` includes frontend origin or `["*"]` |
| `load_test_data` unique constraint | Use `--reset` or run full `dev_setup.py` |
| Admin missing after loader | Run `bootstrap_users.py` **after** `load_test_data --reset` |
| `user/user` login fails (401) | Re-run `dev_setup.py --full` — use contracted login `shutov` / `user` |
| Playwright E2E cannot find browser | `cd frontend && npm run playwright:install` (cache: `.playwright-browsers/`) |
| Port in use | `uv run python src/scripts/dev_setup.py --check-ports`; stop process on :8000/:3000 or use another terminal's stack |
| `--run` exits immediately | Check logs — missing `frontend/`, `node`, or `npm`; run `--check` |
| UI not ready after `--run` | Wait up to 90s on first `npm install`; re-run `cd frontend && npm run dev` |

---

## New contest: confirm participants without email (Stage 1.12+)

SMTP is **not** wired in dev. Invited players start as `PENDING` in `contest_participants` until they complete password setup (`ACCEPTED`). Until then they cannot submit predictions.

> **Critical:** on **first round activation**, the API **purges** all `PENDING` USER participants. Confirm everyone **before** activating tour 1. See [API_GUIDE.md](API_GUIDE.md#password-setup--invite-links-stage-112).

### Local invite testing (defaults)

No extra root `.env` flags needed. Defaults in `config/settings.py`:

- `enforce_password_setup=true` — production-like invite flow
- `frontend_base_url=http://127.0.0.1:3000` — correct `setup_url` host

Legacy automated login in tests only: `ENFORCE_PASSWORD_SETUP=false` via **shell prefix** or pytest `monkeypatch` — see [CONFIG.md — Local / CI tuning](CONFIG.md#local--ci-tuning-not-in-env).

### Workflow A — UI invite + setup link (one participant)

1. Start stack: `uv run python src/scripts/dev_setup.py --run-only` (or `--run` on fresh DB).
2. Log in as **supervisor** → **Настройки** → **Участники** (`/admin/settings/participants`).
3. Select the target contest (multi-contest: switch contest in supervisor shell).
4. Fill invite form (email, name) → **Пригласить**.
5. Modal shows **login**, **temporary password**, and **`setup_url`** — copy all three (button «Скопировать»).
6. **Confirm the participant** (pick one):
   - **Browser:** open `setup_url` in a new tab (or incognito), set a permanent password → redirect to login → log in as the new user.
   - **Share manually:** send login + `setup_url` to the player (no mail server needed).
7. In **Участники**, status should change from «Ожидает» (`PENDING`) to «Принят» (`ACCEPTED`).
8. User can open the contest and submit predictions once a tour is `ACTIVE`.

`setup_url` format: `http://127.0.0.1:3000/auth/setup?token=…` (frontend host from `FRONTEND_BASE_URL` / settings).

### Workflow B — bulk confirm via `dev_invite_setup.py` (dev / QA)

Use when you invited many users and want to skip opening each link by hand.

```bash
# 1. List PENDING invitees for contest id=2; optional: write setup links
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id 2 \
  --out src/scripts/dev_unconfirmed.tsv \
  --links-out src/scripts/.tokens

# 2a. Open links from .tokens (JSON lines with setup_url) — same as step 6 in Workflow A
# 2b. Or confirm all server-side (sets password + ACCEPTED in one step):
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id 2 \
  --password 'DevPass123!'

# Partial list from TSV:
uv run python src/scripts/dev_invite_setup.py confirm-list \
  --file src/scripts/dev_unconfirmed.tsv \
  --password 'DevPass123!'
```

`src/scripts/.tokens` is gitignored. TSV columns: `user_id`, `contest_id`, `email`, `login`.

### Workflow C — create a blank contest (`--minimal`)

For a **new** contest (not CSV contest `id=1`):

```bash
uv run python src/scripts/dev_setup.py --minimal
# → empty DRAFT contest + admin/supervisor; no demo users
```

Then in UI: create/configure contest → invite participants (Workflow A or B) → add teams/rounds → activate first tour only after all needed users are `ACCEPTED`.

### Verify in DB (optional)

```sql
SELECT u.login, cp.status
FROM contest_participants cp
JOIN users u ON u.id = cp.user_id
WHERE cp.contest_id = 2
ORDER BY u.login;
-- Want ACCEPTED before POST .../rounds/{id}/activate
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Invite modal has no `setup_url` | Check API logs; ensure `FRONTEND_BASE_URL` / frontend on `:3000` |
| Login with temp password → 403 `PASSWORD_SETUP_REQUIRED` | Expected when `ENFORCE_PASSWORD_SETUP=true` — use `setup_url`, not temp password login |
| Participant vanished after tour activation | Was still `PENDING` — re-invite or confirm before activate |
| `confirm-all` finds 0 rows | Wrong `--contest-id`; or user already `ACCEPTED` / not temp-password |

API details: [API_GUIDE.md — Password Setup & Invite Links](API_GUIDE.md#password-setup--invite-links-stage-112).

---

## Invite confirm without SMTP — `dev_invite_setup.py` (quick reference)

When SMTP is not configured, use the dev script to export PENDING invitees and confirm via `complete-setup`:

```bash
# Export unconfirmed participants (optional: regenerate setup links)
uv run python src/scripts/dev_invite_setup.py list-pending
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id 2 \
  --out src/scripts/dev_unconfirmed.tsv \
  --links-out src/scripts/.tokens

# Confirm rows from TSV (# lines skipped)
uv run python src/scripts/dev_invite_setup.py confirm-list \
  --file src/scripts/dev_unconfirmed.tsv \
  --password 'DevPass123!'

# Export + confirm all in one step (password from SEED_SUPERVISOR_PASSWORD in .env)
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id 2
```

`src/scripts/.tokens` is gitignored (one JSON object per line with `setup_url`).  
For E2E/training toggles use shell env or pytest `monkeypatch` — see [CONFIG.md — Local / CI tuning](CONFIG.md#local--ci-tuning-not-in-env).

---

## Daily workflow

| Task | Command |
|------|---------|
| Bootstrap + start stack | `uv run python src/scripts/dev_setup.py --run` |
| Start stack (DB already OK) | `uv run python src/scripts/dev_setup.py --run-only` |
| Start API only | `uv run uvicorn main:app --reload --port 8000` |
| Start UI only | `cd frontend && npm run dev` |
| Reset DB to demo state | `uv run python src/scripts/dev_setup.py` |
| Repair fixture only (no loader) | `uv run python src/scripts/dev_setup.py --finalize-fixture-only` |
| E2E DB (round 10 ACTIVE) | `uv run python src/scripts/dev_setup.py --ensure-running-only --e2e` |
| Archive application log | `uv run python src/scripts/archive_logs.py` |
| Re-run migrations | `uv run alembic upgrade head` |

You **do not** re-run `bootstrap_users.py` on every API restart — users persist in `football.db`. Re-run after wiping the DB or fresh clone.

---

## Stage 2 agent references

| Role | Document |
|------|----------|
| Coder 2.1 | `agent_docs/instructions/coder_2.1.md` §2 |
| Tester 2.1 | `agent_docs/instructions/tester_2.1.md` §2 |
| API integration | `agent_docs/contracts/frontend_api_integration.md` |
| Blockers | `agent_docs/reports/BLOCKED.md` (B1–B6 resolved) |

---

*Last updated: Stage 2.3.1 — `--check-ports`; Stage 1.14 fixture + invite workflow.*

---

## Manual QA cheatsheet

Quick commands for supervisor manual testing (also printed at the end of `dev_setup.py` when the stack starts).

### Reset database to demo fixture

Returns contest **id=1** (RUNNING, locked), 16 teams, demo users. Wipes loader tables.

```bash
# Full reset (recommended)
uv run python src/scripts/dev_setup.py

# Same, plus start API + UI
uv run python src/scripts/dev_setup.py --run

# Loader step only (then restore staff + fixture state)
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
```

### Accept all pending invites (no SMTP)

List contests that still have **«Ожидает»** invitees:

```bash
uv run python src/scripts/dev_invite_setup.py list-pending
```

Example output:

```text
contest_id	pending	name
10	2	E2E Setup 1719580000
```

Confirms every `PENDING` temp-password participant for the given contest via `complete-setup`:

```bash
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id <ID>
```

**Password:** not the supervisor login — this is the **new password** assigned to each invited user.
By default the script reads `SEED_SUPERVISOR_PASSWORD` from `.env` (same value you use for `supervisor` login in dev).
Override with `--password '…'` if needed.

```bash
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id <ID> --password 'OtherPass1!'
```

Optional: export list + setup links first:

```bash
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id <ID> \
  --out src/scripts/dev_unconfirmed.tsv --links-out src/scripts/.tokens
```

### Remove extra / deleted contests

E2E (`admin_setup`, `supervisor_create_round`, …) creates many **DRAFT** and **RUNNING** contests named like `E2E Setup …`. They clutter the contest picker until removed.

#### Per-contest (UI)

| Contest status | Steps |
|----------------|-------|
| **DRAFT** | Select contest → `/admin/settings/parameters` → **Удалить конкурс** (instant soft-delete) |
| **RUNNING** | Same page → **Остановить конкурс** → wait **10 s** (`contest_delete_grace_seconds`, default 10) → **Удалить конкурс** |
| **PAUSED** | **Удалить конкурс** (after grace if delete button was disabled) |
| **FINISHED** | No delete in supervisor UI — skip or full DB reset below |

Soft-deleted contests disappear from `GET /contests` but remain in DB until purged. Support (ADMIN) may **restore** within the training window on `/admin/lifecycle`.

There is **no bulk script** for deleting many active DRAFT/RUNNING rows — loop in UI or reset DB.

#### Hard-delete soft-deleted rows from DB

```bash
uv run python src/scripts/purge_deleted_contests.py --all-deleted --dry-run
uv run python src/scripts/purge_deleted_contests.py --all-deleted
```

Purge by retention TTL only (default 30 days): `uv run python src/scripts/purge_deleted_contests.py` — see `contest_purge_retention_seconds` in [CONFIG.md](CONFIG.md).

#### Nuclear reset (back to single fixture contest `id=1`)

Wipes loader tables and all extra contests; restores demo users and finalized rounds on contest 1:

```bash
uv run python src/scripts/dev_setup.py
```

Use when the picker has dozens of E2E leftovers and you do not need to keep custom contests. Servers keep running if already up; only DB changes. To restart stack: `dev_setup.py --run-only`.

| Goal | Action |
|------|--------|
| Hide a draft from lists (soft delete) | UI: «Удалить конкурс» on parameters (DRAFT/PAUSED) |
| Restore within window | Support (ADMIN): `/admin/lifecycle` → «Восстановить» |
| **Hard-delete** soft-deleted rows from DB | `purge_deleted_contests.py --all-deleted` (see above) |
| Purge by retention TTL only | `uv run python src/scripts/purge_deleted_contests.py` |
| Reset everything to dev fixture | `uv run python src/scripts/dev_setup.py` |

### Typical new-contest flow (S1.x)

1. «+ Новый конкурс» → set parameters → add all teams → invite participants.
2. `confirm-all --contest-id <ID>` (or manual `setup_url` per invite).
3. Parameters page: readiness panel green → «Запустить конкурс».

See [SUPERVISOR_TESTING_SCENARIOS.md](SUPERVISOR_TESTING_SCENARIOS.md) for full checklist.
