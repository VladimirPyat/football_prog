# Server Deployment Guide

How to deploy the Football Predictions Contest stack on a server: API (FastAPI) + frontend (Next.js).

**Related docs:** [CONFIG.md](CONFIG.md) (full settings table), [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) (first ADMIN/SUPERVISOR), [API_GUIDE.md](API_GUIDE.md) (invite `setup_url`), [DEV_SETUP.md](DEV_SETUP.md) (local dev only).

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Configuration map (URLs & CORS)](#configuration-map-urls--cors)
- [Backend `.env` (secrets)](#backend-env-secrets)
- [Backend deployment env (non-secrets)](#backend-deployment-env-non-secrets)
- [Frontend env (build-time)](#frontend-env-build-time)
- [Production install — exclude dev/QA](#production-install--exclude-devqa)
- [Database: SQLite → PostgreSQL](#database-sqlite--postgresql)
- [First deploy checklist](#first-deploy-checklist)
- [Running services](#running-services)
- [Reverse proxy (typical)](#reverse-proxy-typical)
- [Persistent data](#persistent-data)
- [Invite links & SMTP](#invite-links--smtp)
- [Production checklist](#production-checklist)
- [Troubleshooting](#troubleshooting)

---

## Architecture

Two processes in production:

| Service | Default dev port | Role |
|---------|------------------|------|
| **FastAPI** (`uvicorn main:app`) | `8000` | REST API, JWT auth, static team logos under `/static/` |
| **Next.js** (`npm run build` + `npm start`) | `3000` | User/supervisor UI; browser calls API via `NEXT_PUBLIC_API_URL` |

The browser talks to **both** origins:

- UI pages → frontend host (e.g. `https://app.example.com`)
- `fetch` / login / setup → API host (e.g. `https://api.example.com`)

Invite links (`setup_url`) are built on the **backend** and must point at the **frontend** host (`FRONTEND_BASE_URL`), not the API.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | ≥ 3.12 | `uv sync` in repo root |
| **uv** | latest | dependency lockfile in `pyproject.toml` |
| Node.js | ≥ 20 LTS | for `frontend/` |
| PostgreSQL | 14+ recommended | production DB (SQLite is dev-only) |
| Reverse proxy | nginx / Caddy / Traefik | TLS termination, optional path routing |

---

## Configuration map (URLs & CORS)

Use this table when moving from local dev to a real server.

| What | Where to set | Dev default | Production example |
|------|--------------|-------------|------------------|
| **API base URL (browser → API)** | `frontend/.env.local` or build env: `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | `https://api.example.com` |
| **Frontend base URL (invite `setup_url`)** | Backend env: `FRONTEND_BASE_URL` → `config/settings.py` `frontend_base_url` | `http://127.0.0.1:3000` | `https://app.example.com` |
| **CORS allowed origins** | Backend env: `CORS_ORIGINS` → `cors_origins` | `["*"]` | `["https://app.example.com"]` |
| **Database** | Root `.env`: `DATABASE_URL` | `sqlite+aiosqlite:///./football.db` | `postgresql+asyncpg://user:pass@host:5432/football` |
| **JWT signing** | Root `.env`: `JWT_SECRET_KEY` | dev placeholder | long random secret, **stable across restarts** |
| **Display timezone (UI)** | `frontend`: `NEXT_PUBLIC_DISPLAY_TIMEZONE` | `Europe/Moscow` | same or browser-local |

**Critical:** `NEXT_PUBLIC_*` variables are embedded at **`npm run build`** time. Changing them on the server **after** build has no effect until you rebuild.

**Critical:** `FRONTEND_BASE_URL` is read when the **API** creates an invite. Old invites keep the URL that was active at invite time.

---

## Backend `.env` (secrets)

On the server, in the **project root** (gitignored):

```bash
cp .env.example .env
```

Minimum for production:

```env
# PostgreSQL (see below for URL format)
DATABASE_URL=postgresql+asyncpg://football:STRONG_PASSWORD@127.0.0.1:5432/football

# Required — generate a long random string; never rotate casually (invalidates JWTs)
JWT_SECRET_KEY=replace-with-64-plus-char-random-string

# One-time bootstrap (see First deploy)
SEED_ADMIN_PASSWORD=your-admin-password
SEED_SUPERVISOR_PASSWORD=your-supervisor-password
```

Full reference: [CONFIG.md — `.env`](CONFIG.md#env--secrets--deployment).

Do **not** put `FRONTEND_BASE_URL` or `CORS_ORIGINS` in `.env` unless your deployment policy allows it — they are non-secret and usually set in systemd/K8s/docker env. See next section.

---

## Backend deployment env (non-secrets)

Set these in the **API process environment** (systemd unit, docker-compose, K8s manifest, etc.). They override `config/settings.py` via pydantic-settings.

| Env var | Production example | Purpose |
|---------|-------------------|---------|
| `FRONTEND_BASE_URL` | `https://app.example.com` | Invite link: `{base}/auth/setup?token=…` |
| `CORS_ORIGINS` | `["https://app.example.com"]` | JSON array; **do not use `*`** with `allow_credentials=true` in production |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_TO_FILE` | `true` | Write `app.log` |
| `UPLOAD_DIR` | `/var/lib/football/uploads` | Persistent team logos |
| `ENFORCE_PASSWORD_SETUP` | `true` | Keep `true` in production |
| `SETUP_TOKEN_EXPIRE_HOURS` | `72` | Invite token TTL |

**CORS example** (systemd `Environment=` or shell):

```bash
export CORS_ORIGINS='["https://app.example.com"]'
export FRONTEND_BASE_URL='https://app.example.com'
```

If frontend and API share one domain (e.g. `example.com` + `/api` proxy), CORS may be unnecessary for same-origin requests — but `NEXT_PUBLIC_API_URL` must match how the browser reaches the API.

Full table: [CONFIG.md — Application defaults](CONFIG.md#application-defaults-configsettingspy).

---

## Frontend env (build-time)

Create `frontend/.env.production` (or export vars before build):

```env
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE=UTC
NEXT_PUBLIC_DISPLAY_TIMEZONE=Europe/Moscow

# Optional — remove or set per contest in multi-contest prod
# NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Build and run:

```bash
cd frontend
npm ci              # full deps required for `next build` (TypeScript, Tailwind, etc.)
npm run build
npm prune --omit=dev   # drop devDependencies after build (Playwright, Vitest, ESLint, …)
npm run start   # listens on :3000 by default; set PORT=3000 in process manager
```

> **Do not** run `npm run playwright:install` on the server — browsers (~800 MiB) are for local/CI E2E only.  
> See [Production install — exclude dev/QA](#production-install--exclude-devqa).

Template: [`frontend/.env.local.example`](../frontend/.env.local.example).

**Same host, different paths** (nginx serves app on `/`, API on `/api`):

- Proxy `/api` → uvicorn
- `NEXT_PUBLIC_API_URL=https://app.example.com` (no `/api` suffix if Next calls `/api/v1/...` — check `frontend/src/lib/api/endpoints.ts`; paths are absolute under `/api/v1`)

Verify in browser DevTools: login and `/auth/setup` must reach the API without CORS errors.

---

## Production install — exclude dev/QA

Production needs **API + built Next.js** only. Test runners, linters, and E2E browsers are **not** deployed.

### Backend (Python)

Install **runtime** dependencies only:

```bash
cd /path/to/football_prog
uv sync --no-dev
```

This skips the `[dependency-groups] dev` packages (`pytest`, `ruff`, `mypy`, `bandit`, …). They are not in `requires-python` runtime and are **not** pulled by `uv sync --no-dev`.

| Include on server | Exclude (dev/QA) |
|-------------------|------------------|
| `uvicorn`, FastAPI, SQLAlchemy, Alembic, … | `pytest`, `httpx` (test client), `ruff`, `mypy`, `bandit` |
| `uv run alembic upgrade head` | `uv run pytest` |
| `uv run python src/scripts/bootstrap_users.py` (once) | `load_test_data.py --reset` (dev fixture) |

### Frontend (Node)

| Phase | Command | Notes |
|-------|---------|-------|
| **Build** | `npm ci` then `npm run build` | Needs devDependencies (TypeScript, Tailwind, PostCSS) |
| **Runtime** | `npm prune --omit=dev` then `npm run start` | Removes test/lint tooling from `node_modules` |

**Never on production:**

| Artifact | Why |
|----------|-----|
| `npm run playwright:install` | Downloads Chromium + headless shell (~800 MiB); only for E2E |
| `frontend/.playwright-browsers/` | Gitignored local E2E cache — not in repo, do not create on server |
| `npm run test:e2e` | Playwright E2E — run in CI or dev machine only |
| `npm run test:unit` / `npm run lint` | Dev/CI gates, not runtime |

`@playwright/test` lives in `devDependencies`. It is **not** installed if you `npm prune --omit=dev` after build. There is **no** `postinstall` hook that downloads browsers — they appear only after an explicit `playwright:install`.

### Optional — omit from deploy artifact

Not required for serving traffic (safe to exclude from tarball/Docker context to save space):

- `tests/`, `frontend/e2e/`, `agent_docs/`, `docs/` (specs)
- `.venv` from dev machine — recreate on server with `uv sync --no-dev`
- `football.db` (SQLite dev DB)
- `frontend/.next/` from dev — **rebuild** on server or in CI with production `NEXT_PUBLIC_*`

### CI vs server (recommended split)

| Step | Where |
|------|-------|
| `uv run pytest`, `npm run test:unit`, `npm run test:e2e` | CI or developer machine |
| `npm run playwright:install` (once) | CI runner or dev (`frontend/.playwright-browsers/`) |
| `uv sync --no-dev`, `npm ci` + `build` + `prune --omit=dev` | Production server or release image |

---

## Database: SQLite → PostgreSQL

### 1. Create database and user

```sql
CREATE USER football WITH PASSWORD 'your-db-password';
CREATE DATABASE football OWNER football;
```

### 2. Set URL in `.env`

```env
DATABASE_URL=postgresql+asyncpg://football:your-db-password@127.0.0.1:5432/football
```

Driver is **asyncpg** (already in project dependencies). Format must use the `postgresql+asyncpg://` scheme.

### 3. Run migrations

```bash
cd /path/to/football_prog
uv sync
uv run alembic upgrade head
```

Alembic reads `DATABASE_URL` from settings (`.env`).

### 4. Bootstrap users (once per empty DB)

```bash
uv run python src/scripts/seed.py
uv run python src/scripts/bootstrap_users.py
```

See [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md). **Do not** re-run bootstrap on every deploy.

### 5. Optional test data

`load_test_data.py` is for **dev/QA**, not typical production. Use supervisor UI to create contests, or import via admin flows.

---

## First deploy checklist

1. Clone repo on server; `uv sync --no-dev`; configure frontend env (step 6) then build (step 7)
2. Configure root `.env` (PostgreSQL, `JWT_SECRET_KEY`, seed passwords)
3. Set deployment env: `FRONTEND_BASE_URL`, `CORS_ORIGINS`
4. `uv run alembic upgrade head`
5. `uv run python src/scripts/seed.py` + `bootstrap_users.py`
6. Configure `frontend/.env.production` with `NEXT_PUBLIC_API_URL`
7. `cd frontend && npm ci && npm run build && npm prune --omit=dev`
8. Start API + frontend (systemd/docker)
9. Configure TLS reverse proxy
10. Smoke test:
    - `curl -s https://api.example.com/health` → `{"status":"ok"}`
    - Open frontend, login as supervisor
    - Invite a test user → copy `setup_url` → complete setup → login as user

---

## Running services

### API (development-style — not for high load)

```bash
cd /path/to/football_prog
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

### API (production)

Use a process manager with multiple workers, e.g. **gunicorn** + uvicorn workers (install via `uv add gunicorn` when approved), or systemd:

```ini
# /etc/systemd/system/football-api.service (example)
[Service]
WorkingDirectory=/opt/football_prog
Environment=FRONTEND_BASE_URL=https://app.example.com
Environment=CORS_ORIGINS=["https://app.example.com"]
EnvironmentFile=/opt/football_prog/.env
ExecStart=/opt/football_prog/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
```

Bind to `127.0.0.1` if only nginx talks to the API.

### Frontend

```bash
cd /path/to/football_prog/frontend
PORT=3000 npm run start
```

Or systemd unit for `npm run start` after build.

---

## Reverse proxy (typical)

Example layout (two subdomains):

| Public URL | Upstream |
|------------|----------|
| `https://app.example.com` | `http://127.0.0.1:3000` (Next.js) |
| `https://api.example.com` | `http://127.0.0.1:8000` (uvicorn) |

nginx must forward:

- `Authorization` header (JWT)
- WebSocket if you add it later (not required today)
- Large enough `client_max_body_size` for team logo uploads (default API limit 2 MiB — see `MAX_LOGO_BYTES` in [CONFIG.md](CONFIG.md))

Static files: team logos are served by FastAPI from `UPLOAD_DIR` at `/static/teams/...`. Ensure `uploads/` is on persistent disk.

---

## Persistent data

| Path | Git | Backup |
|------|-----|--------|
| PostgreSQL data | — | DB dumps |
| `uploads/` (team logos) | gitignored | copy volume |
| `app.log`, `logs/archive/` | gitignored | optional log shipping |
| `football.db` | gitignored | SQLite dev only — use PostgreSQL in prod |

---

## Invite links & SMTP

- **SMTP is not configured** in v1. Invite `setup_url` is shown in the admin UI modal after `POST …/participants`.
- Links are **real** signed JWTs; base URL = `FRONTEND_BASE_URL` at invite time.
- When SMTP is added later, it will reuse `build_setup_url()` in `src/core/setup_tokens.py` — only `FRONTEND_BASE_URL` must be correct on the API host.

Dev workflow without mail: [DEV_SETUP.md — confirm participants](DEV_SETUP.md#new-contest-confirm-participants-without-email-stage-112).

---

## Production checklist

| Item | Action |
|------|--------|
| `JWT_SECRET_KEY` | Strong random value; backup securely |
| `DATABASE_URL` | PostgreSQL, not SQLite |
| `CORS_ORIGINS` | Explicit frontend origin(s), not `*` |
| `FRONTEND_BASE_URL` | Public HTTPS frontend URL |
| `NEXT_PUBLIC_API_URL` | Set before `npm run build`; matches live API |
| `ENFORCE_PASSWORD_SETUP` | `true` |
| `SEED_*_PASSWORD` | Strong; bootstrap once, then remove from deploy secrets if desired |
| TLS | HTTPS on both app and API (or same-origin proxy) |
| Migrations | `alembic upgrade head` on each deploy **before** restarting API |
| Uploads | Persistent `UPLOAD_DIR` |
| Dev/QA excluded | `uv sync --no-dev`; no Playwright install; `npm prune --omit=dev` after frontend build |

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| CORS error in browser | `CORS_ORIGINS` missing frontend URL; or API URL mismatch |
| Invite link points to `127.0.0.1:3000` | `FRONTEND_BASE_URL` not set on **API** process |
| Setup page loads but API fails | Wrong `NEXT_PUBLIC_API_URL` at build time — rebuild frontend |
| `setup_url` works once, then “invalid token” | Token expired (`SETUP_TOKEN_EXPIRE_HOURS`) or `JWT_SECRET_KEY` changed |
| Login 403 `PASSWORD_SETUP_REQUIRED` | User must open `setup_url`, not temp password (when `ENFORCE_PASSWORD_SETUP=true`) |
| Logos disappear after redeploy | `uploads/` not on persistent volume |
| Alembic errors on PostgreSQL | Check `postgresql+asyncpg://` URL; DB user permissions |

---

*Last updated: 2026-07-08 — production install excludes dev/QA (Playwright, pytest, prune devDeps).*
