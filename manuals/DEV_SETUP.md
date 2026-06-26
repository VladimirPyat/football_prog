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

Optional for E2E (Stage 2.1+ tester): Playwright browsers — `cd frontend && npx playwright install chromium`

---

## Quick start (recommended)

From the repository root:

```bash
# 1. Environment (once)
cp .env.example .env
# Edit .env: set SEED_ADMIN_PASSWORD and SEED_SUPERVISOR_PASSWORD (see .env.example)

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
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run python src/scripts/dev_setup.py --help
```

### What `--run` / `--run-only` do

1. Ensure `frontend/.env.local` exists (copy from `.env.local.example` if missing)
2. Run `npm install` in `frontend/` when `node_modules/` is absent
3. Start **API**: `uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000`
4. Start **UI**: `npm run dev` in `frontend/` → `http://127.0.0.1:3000`
5. Poll `/health` and UI root until ready (or timeout ~90s)
6. On **Ctrl+C** or SIGTERM — stop both child processes

`--run` = default full setup, then steps 1–6. `--run-only` = steps 1–6 without touching the DB.

### What `--full` (default) does

1. `uv sync` (install Python deps from `pyproject.toml`)
2. Warn if `.env` missing (copy from `.env.example` manually)
3. `alembic upgrade head`
4. `load_test_data.py --reset` — contest **id=1**, 16 teams, 10 users (`user`/`user`, …), rounds 1–9 published, round **10 ACTIVE**
5. `bootstrap_users.py` — **after loader** (loader `--reset` deletes all `users`; bootstrap restores `admin` / `supervisor` from `.env`)
6. **Dev contest state** — sets contest `1` to `RUNNING` + `is_locked=true` so `GET /contests/public` and frontend discovery work

### What `--minimal` does

1–3 as above, then `seed.py` + `bootstrap_users.py` (no CSV loader, no `user/user` test login).

Use `--minimal` for a blank SETUP-phase contest; use **`--full`** for Stage 2 frontend / E2E.

---

## Manual steps (without script)

```bash
uv sync
cp .env.example .env   # edit passwords

uv run alembic upgrade head

# Full dev data (order matters — bootstrap AFTER loader):
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only   # or run full dev_setup once

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
| USER (demo) | `user` | `user` | `bootstrap_users.py` (`SEED_DEMO_USER_*`; defaults work without `.env`) |
| SUPERVISOR | `supervisor` | value from `.env` `SEED_SUPERVISOR_PASSWORD` | `bootstrap_users.py` |
| ADMIN | `admin` | value from `.env` `SEED_ADMIN_PASSWORD` | `bootstrap_users.py` |

> **Note:** `load_test_data.py` CSV also defines a `user` row, but its password hash is a placeholder — after `--reset`, only `bootstrap_users.py` provides a working `user/user` login. Other loader users (`shutov`, `volchenko`, …) may still use password **`user`** if their CSV hash matches; rely on the demo row above for E2E.

Do **not** commit `.env` or real passwords.

---

## Running tests

### Backend

```bash
uv run pytest tests/ --ignore=tests/manual -q
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
| `bootstrap_users` skips / no admin | Set `SEED_ADMIN_PASSWORD` in `.env` |
| `GET /contests/public` returns `[]` | Re-run `dev_setup.py` (contest must be **RUNNING**) |
| CORS errors from `:3000` | Ensure `CORS_ORIGINS` includes frontend origin or `["*"]` |
| `load_test_data` unique constraint | Use `--reset` or run full `dev_setup.py` |
| Admin missing after loader | Run `bootstrap_users.py` **after** `load_test_data --reset` |
| `user/user` login fails (401) | Re-run `dev_setup.py` — demo USER is created by `bootstrap_users.py` after loader |
| Playwright E2E cannot find browser | `npx playwright install chromium` in `frontend/` |
| Port in use | Stop process on :8000/:3000 or change ports in script / `frontend/package.json` |
| `--run` exits immediately | Check logs — missing `frontend/`, `node`, or `npm`; run `--check` |
| UI not ready after `--run` | Wait up to 90s on first `npm install`; re-run `cd frontend && npm run dev` |

---

## Invite confirm without SMTP — `dev_invite_setup.py` (Stage 1.12)

When SMTP is not configured, use the dev script to export PENDING invitees and confirm via `complete-setup`:

```bash
# Export unconfirmed participants (optional: regenerate setup links)
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id 2 \
  --out src/scripts/dev_unconfirmed.tsv \
  --links-out src/scripts/.tokens

# Confirm rows from TSV (# lines skipped)
uv run python src/scripts/dev_invite_setup.py confirm-list \
  --file src/scripts/dev_unconfirmed.tsv \
  --password 'DevPass123!'

# Export + confirm all in one step
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id 2
```

`src/scripts/.tokens` is gitignored (one JSON object per line with `setup_url`).  
Recommended local flags: `ENFORCE_PASSWORD_SETUP=false`, `SUPERVISOR_TRAINING_MODE=true`, `CONTEST_DELETE_GRACE_SECONDS=0` — see [CONFIG.md](CONFIG.md).

---

## Daily workflow

| Task | Command |
|------|---------|
| Bootstrap + start stack | `uv run python src/scripts/dev_setup.py --run` |
| Start stack (DB already OK) | `uv run python src/scripts/dev_setup.py --run-only` |
| Start API only | `uv run uvicorn main:app --reload --port 8000` |
| Start UI only | `cd frontend && npm run dev` |
| Reset DB to demo state | `uv run python src/scripts/dev_setup.py` |
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

*Last updated: Stage 2.1 — `dev_setup.py --run` / `--run-only` for one-command local stack.*
