# Server Deployment Guide

How to deploy the Football Predictions Contest stack: API (FastAPI) + frontend (Next.js).

**Related docs:** [CONFIG.md](CONFIG.md) (full settings table), [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) (first Support/SUPERVISOR), [API_GUIDE.md](API_GUIDE.md) (invite `setup_url`), [DEV_SETUP.md](DEV_SETUP.md) (local dev only).

## Table of Contents

- [Deployment modes (`APP_MODE`)](#deployment-modes-app_mode)
- [What to change where](#what-to-change-where)
- [Docker deploy (recommended)](#docker-deploy-recommended)
- [First deploy checklist (Docker)](#first-deploy-checklist-docker)
- [Update deploy (git pull)](#update-deploy-git-pull)
- [Architecture](#architecture)
- [Local dev (no Docker)](#local-dev-no-docker)
- [Manual / systemd deploy](#manual--systemd-deploy)
- [Reverse proxy (typical)](#reverse-proxy-typical)
- [Persistent data](#persistent-data)
- [Invite links & SMTP](#invite-links--smtp)
- [Production checklist](#production-checklist)
- [Troubleshooting](#troubleshooting)

---

## Deployment modes (`APP_MODE`)

The server keeps its own **gitignored** `.env`. Code updates via `git pull` must **not** overwrite production URLs, CORS, or secrets.

Set one mode in `.env`:

| `APP_MODE` | When | Database | URLs / CORS |
|------------|------|----------|-------------|
| `local` | Laptop (`uv run`, `npm run dev`) | SQLite (`./football.db`) | `127.0.0.1`, CORS `*` |
| `web_dev` | Server/docker staging | SQLite (`./data/football.db`) | `PUBLIC_*` or `localhost` defaults |
| `web_prod` | Production | PostgreSQL (compose `--profile prod`) | **`PUBLIC_FRONTEND_URL` required** |

Presets live in ``resolve_app_mode_preset()`` (`config/settings.py`) — one readable block per mode. Server secrets and URLs stay in gitignored ``.env``.

**Rule:** on a server, edit **only** `.env` (and `data/` volumes). Do not commit server URLs into the repo.

---

## What to change where

| What | File / location | `local` | `web_dev` / `web_prod` |
|------|-----------------|---------|------------------------|
| Mode | root `.env` → `APP_MODE` | `local` | `web_dev` or `web_prod` |
| Public UI URL (invites, CORS) | root `.env` → `PUBLIC_FRONTEND_URL` | — | `https://app.example.com` |
| Public API URL (browser) | root `.env` → `PUBLIC_API_URL` | — | `https://api.example.com` |
| DB password (Docker) | root `.env` → `POSTGRES_PASSWORD` | — | `web_prod` only |
| JWT / seed passwords | root `.env` | dev placeholders | production secrets |
| Custom DB URL | root `.env` → `DATABASE_URL` | optional | overrides mode default |
| SQLite file (`web_dev`) | host `./data/football.db` | `./football.db` | Docker volume `./data` |
| Frontend API URL at build | Docker build arg from `PUBLIC_API_URL` | `frontend/.env.local` | `.env` → rebuild frontend |
| Uploads & logs | host `./data/uploads`, `./data/logs` | `./uploads`, `./logs` | Docker volumes |
| PostgreSQL files | Docker volume `pgdata` | — | automatic |

**Critical:** `PUBLIC_API_URL` is embedded at **`docker compose build`** (Next.js). Changing it requires **rebuild** of the `frontend` service.

**Critical:** invite `setup_url` uses `PUBLIC_FRONTEND_URL` (via `FRONTEND_BASE_URL` preset) on the **API** at invite time.

---

## Docker deploy (recommended)

Stack files (committed):

| File | Role |
|------|------|
| [`docker-compose.yml`](../docker-compose.yml) | `db` + `api` + `frontend` |
| [`Dockerfile`](../Dockerfile) | API image (`uv`, Alembic on start) |
| [`frontend/Dockerfile`](../frontend/Dockerfile) | Next.js multi-stage build |
| [`.env.example`](../.env.example) | Template for server `.env` |

### Prerequisites (server)

| Tool | Version |
|------|---------|
| Docker Engine | 24+ |
| Docker Compose | v2 (`docker compose`) |
| Git | clone/pull repo |
| Reverse proxy (prod) | nginx / Caddy / Traefik + TLS |

### 1. Clone and create persistent layout

```bash
sudo mkdir -p /opt/football_prog
sudo chown "$USER":"$USER" /opt/football_prog
git clone <repo-url> /opt/football_prog
cd /opt/football_prog

mkdir -p data/uploads data/logs
cp .env.example .env
chmod 600 .env
```

### 2. Configure server `.env`

Example for **production**:

```env
APP_MODE=web_prod

PUBLIC_FRONTEND_URL=https://app.example.com
PUBLIC_API_URL=https://api.example.com

POSTGRES_PASSWORD=replace-with-strong-db-password
JWT_SECRET_KEY=replace-with-64-plus-char-random-string

SEED_SUPPORT_PASSWORD=your-support-password
SEED_SUPERVISOR_PASSWORD=your-supervisor-password

# Optional host port mapping (defaults 8000 / 3000)
# API_PORT=8000
# FRONTEND_PORT=3000
```

Example for **staging on the same machine** (`web_dev`):

```env
APP_MODE=web_dev
PUBLIC_FRONTEND_URL=http://localhost:3000
PUBLIC_API_URL=http://localhost:8000
POSTGRES_PASSWORD=staging-db-password
JWT_SECRET_KEY=staging-jwt-secret
```

Compose reads `.env` for variable substitution **and** passes it to the API container (`env_file`). This file is **never** in git — safe across `git pull`.

### 3. Build and start

```bash
cd /opt/football_prog
docker compose build

# web_dev (SQLite, no PostgreSQL container):
docker compose up -d

# web_prod (adds PostgreSQL):
docker compose --profile prod up -d
```

On first start the API container runs `alembic upgrade head` automatically (`docker/entrypoint-api.sh`).

### 4. Bootstrap users (once per empty database)

```bash
docker compose exec api uv run python src/scripts/seed.py
docker compose exec api uv run python src/scripts/bootstrap_users.py
```

See [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md). **Do not** re-run on every deploy.

### 5. Smoke test

```bash
curl -s http://127.0.0.1:8000/health
# → {"status":"ok"}

curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/
# → 200
```

Then configure TLS reverse proxy (below) and test login + invite flow in the browser.

### 6. Production reverse proxy

Point public hostnames at container ports (default `127.0.0.1:3000` and `:8000`):

| Public URL | Upstream |
|------------|----------|
| `https://app.example.com` | `http://127.0.0.1:3000` |
| `https://api.example.com` | `http://127.0.0.1:8000` |

Ensure `PUBLIC_FRONTEND_URL` / `PUBLIC_API_URL` in `.env` match the **HTTPS** URLs users see in the browser.

---

## First deploy checklist (Docker)

1. Install Docker + Compose on server
2. Clone repo to `/opt/football_prog`
3. `mkdir -p data/uploads data/logs`
4. Copy `.env.example` → `.env`; set `APP_MODE=web_prod`, `PUBLIC_*`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, seed passwords
5. `docker compose build && docker compose up -d`
6. `docker compose exec api uv run python src/scripts/seed.py`
7. `docker compose exec api uv run python src/scripts/bootstrap_users.py`
8. Configure TLS reverse proxy
9. Smoke test: `/health`, frontend login, invite → `setup_url` → user setup

---

## Update deploy (git pull)

Server `.env` and `data/` volumes are **outside git** — they survive updates.

```bash
cd /opt/football_prog
git pull

# Rebuild when code or frontend PUBLIC_API_URL changed
docker compose build

docker compose up -d
```

| Changed | Action |
|---------|--------|
| API / Python code | `docker compose build api && docker compose up -d api` |
| Frontend code | `docker compose build frontend && docker compose up -d frontend` |
| `PUBLIC_API_URL` in `.env` | **Must** rebuild frontend |
| `PUBLIC_FRONTEND_URL` only | Restart API: `docker compose up -d api` |
| Alembic migrations in repo | Automatic on API container start |
| `.env` secrets only | `docker compose up -d` (recreate if needed) |

Migrations run before uvicorn on each API start. For zero-downtime at scale, run migrations in a one-off job instead — not required for a single-server deploy.

Useful commands:

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f frontend
docker compose down          # stop (volumes kept)
docker compose down -v       # ⚠ removes PostgreSQL volume
```

---

## Architecture

Three containers in Docker production:

| Service | Image / build | Default port | Role |
|---------|---------------|--------------|------|
| **db** | `postgres:16-alpine` | internal `5432` | PostgreSQL (`pgdata` volume); **`--profile prod` only** |
| **api** | `Dockerfile` | `8000` | FastAPI, JWT, static logos |
| **frontend** | `frontend/Dockerfile` | `3000` | Next.js UI |

The browser talks to **both** public origins:

- UI → `PUBLIC_FRONTEND_URL`
- API calls → `PUBLIC_API_URL`

---

## Local dev (no Docker)

```bash
cp .env.example .env
# APP_MODE=local (default)

uv sync
uv run alembic upgrade head
uv run python src/scripts/seed.py
uv run python src/scripts/bootstrap_users.py
uv run uvicorn main:app --reload --port 8000

cd frontend
cp .env.local.example .env.local
npm ci && npm run dev
```

See [DEV_SETUP.md](DEV_SETUP.md).

Optional: run Docker stack locally with `APP_MODE=web_dev` in `.env` to mirror server DB layout.

---

## Manual / systemd deploy

If you prefer bare-metal (no Docker):

```bash
uv sync --no-dev
uv run alembic upgrade head
# set APP_MODE=web_prod + PUBLIC_* in .env
cd frontend && npm ci && npm run build && npm prune --omit=dev
```

Run API and frontend via systemd — example API unit:

```ini
# /etc/systemd/system/football-api.service
[Service]
WorkingDirectory=/opt/football_prog
EnvironmentFile=/opt/football_prog/.env
ExecStart=/opt/football_prog/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
```

With `APP_MODE=web_prod`, set `PUBLIC_FRONTEND_URL` in `.env` instead of separate `FRONTEND_BASE_URL` / `CORS_ORIGINS`.

PostgreSQL: create DB/user manually ([CONFIG.md — Database URL](CONFIG.md#database-url)).

---

## Reverse proxy (typical)

nginx must forward:

- `Authorization` header (JWT)
- `client_max_body_size` ≥ 2 MiB (team logo uploads)

Static team logos: served by API from `/static/teams/...` (`UPLOAD_DIR` → `data/uploads` in Docker).

---

## Persistent data

| Path / volume | Git | Survives `compose up` | Backup |
|---------------|-----|------------------------|--------|
| `.env` | ignored | yes (host file) | secure copy |
| `data/uploads/` | ignored | yes (bind mount) | copy volume |
| `data/logs/` | ignored | yes (bind mount) | optional log shipping |
| Docker volume `pgdata` | — | yes | `pg_dump` |
| `data/football.db` | ignored | yes (`web_dev` SQLite) | copy file |

Create host dirs before first start: `mkdir -p data/uploads data/logs`.

---

## Invite links & SMTP

- **SMTP is not configured** in v1. Invite `setup_url` is shown in the supervisor UI after `POST …/participants`.
- Links use `PUBLIC_FRONTEND_URL` (via mode preset) at invite time.
- When SMTP is added, it will reuse `build_setup_url()` — keep `PUBLIC_FRONTEND_URL` correct on the server.

---

## Production checklist

| Item | Action |
|------|--------|
| `APP_MODE` | `web_prod` on server |
| `PUBLIC_FRONTEND_URL` | Public HTTPS UI URL |
| `PUBLIC_API_URL` | Public HTTPS API URL; rebuild frontend after change |
| `POSTGRES_PASSWORD` | Strong; only in server `.env` |
| `JWT_SECRET_KEY` | Long random; stable across restarts |
| `DATABASE_URL` | PostgreSQL (compose sets automatically unless overridden) |
| CORS | Derived from `PUBLIC_FRONTEND_URL` — no `*` in prod |
| `ENFORCE_PASSWORD_SETUP` | `true` (forced in `web_prod`) |
| Bootstrap passwords | Run once; remove from `.env` later if desired |
| TLS | HTTPS on app + API (or same-origin proxy) |
| Volumes | `data/uploads`, `data/logs`, `pgdata` |
| `.dockerignore` | Docs/tests excluded from images |

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| CORS error | Wrong `PUBLIC_FRONTEND_URL`; restart API |
| Invite link → `127.0.0.1:3000` | `APP_MODE=local` or missing `PUBLIC_FRONTEND_URL` on API |
| UI loads, API calls fail | Wrong `PUBLIC_API_URL` at **build** time — `docker compose build frontend` |
| Config reset after `git pull` | Edited committed files instead of `.env` |
| Logos gone after redeploy | `data/uploads` not mounted |
| DB empty after redeploy | Ran `docker compose down -v` (drops `pgdata`) |
| `PUBLIC_FRONTEND_URL is required` | Set it for `APP_MODE=web_prod` |
| Alembic / DB connection errors | Check `POSTGRES_PASSWORD`, `docker compose ps`, db health |

---

*Last updated: 2026-07-11 — APP_MODE presets, Docker Compose deploy, persistent volumes.*
