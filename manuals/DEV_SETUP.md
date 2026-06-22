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
# Edit .env: set SEED_ADMIN_PASSWORD and SEED_SUPERVISOR_PASSWORD (plaintext)

# 2. Backend + demo data (idempotent)
uv run python src/scripts/dev_setup.py

# 3. API server — Terminal 1
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 4. Frontend — Terminal 2 (after Coder scaffolds frontend/)
cd frontend
cp .env.local.example .env.local   # if not created by scaffold
npm install
npm run dev                        # http://127.0.0.1:3000
```

**Verify API:** `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`

**Verify public contest list (B2):** after `dev_setup.py --full`, contest id `1` is **RUNNING** → `curl -s http://127.0.0.1:8000/api/v1/contests/public`

---

## Bootstrap script — `src/scripts/dev_setup.py`

Automates migrations, test data, admin users, and dev contest state.

```bash
uv run python src/scripts/dev_setup.py              # full frontend dev DB (default)
uv run python src/scripts/dev_setup.py --minimal    # empty contest + admin only (no CSV loader)
uv run python src/scripts/dev_setup.py --no-reset   # full without wiping loader tables first
uv run python src/scripts/dev_setup.py --check      # prerequisites only, no DB changes
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run python src/scripts/dev_setup.py --help
```

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
| USER (participant) | `user` | `user` | `load_test_data.py` CSV |
| SUPERVISOR | `supervisor` | value from `.env` `SEED_SUPERVISOR_PASSWORD` | `bootstrap_users.py` |
| ADMIN | `admin` | value from `.env` `SEED_ADMIN_PASSWORD` | `bootstrap_users.py` |

Other loader users (`shutov`, `volchenko`, …) use password **`user`** unless CSV specifies otherwise.

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
| Playwright E2E cannot find browser | `npx playwright install chromium` in `frontend/` |
| Port in use | Change ports or stop conflicting process |

---

## Daily workflow

| Task | Command |
|------|---------|
| Start API only | `uv run uvicorn main:app --reload --port 8000` |
| Start UI only | `cd frontend && npm run dev` |
| Reset DB to demo state | `uv run python src/scripts/dev_setup.py --reset` |
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

*Last updated: Stage 2.1 dev bootstrap — adjust this file when Docker Compose or `frontend/` scaffold lands.*
