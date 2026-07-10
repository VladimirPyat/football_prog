# Initial Users Bootstrap

One-time setup for **Support (ADMIN)** and **SUPERVISOR** on a **new database** (local or server).  
After bootstrap, users live in `football.db` (or your `DATABASE_URL`) — **you do not re-run the script** on every app start, only when the DB is empty again (fresh deploy, new server, wiped DB).

## When to run

| Situation | Run `bootstrap_users.py`? |
|-----------|---------------------------|
| First deploy / empty `users` table | **Yes** |
| Daily dev, restart API, run tests | **No** — users already in DB |
| Changed password in `.env` only | **No** — script skips existing logins; change password via API or DB |
| New server / `alembic upgrade` on empty DB | **Yes** |

## 1. Configure `.env`

Copy template: `cp .env.example .env`

Minimum (passwords only — logins `support` / `supervisor` are in `config/settings.py`):

```env
SEED_SUPPORT_PASSWORD=your-support-password
SEED_SUPERVISOR_PASSWORD=your-supervisor-password
JWT_SECRET_KEY=change-me-to-a-long-random-string
```

Use **plaintext passwords** — the script hashes them with bcrypt before saving.  
Alternative: `SEED_SUPPORT_PASSWORD_HASH` / `SEED_SUPERVISOR_PASSWORD_HASH` (see [CONFIG.md](CONFIG.md#env--secrets--deployment)).

Also set `DATABASE_URL` for non-SQLite deployments.

## 2. One-time setup

```bash
uv run alembic upgrade head
uv run python src/scripts/seed.py              # contest row (if missing)
uv run python src/scripts/bootstrap_users.py   # Support (ADMIN) + SUPERVISOR
```

**Idempotent:** if `support` / `supervisor` already exist, the script logs “skipping” and does nothing.

## 3. Check in DBeaver

Before bootstrap (fresh DB): `users` is empty (or no Support/SUPERVISOR).

After bootstrap:

```sql
SELECT id, login, role, is_temp_password FROM users;
```

Expect rows like `support` → `SUPPORT`, `supervisor` → `SUPERVISOR`.  
Column `password_hash` is bcrypt (`$2b$12$...`), not your plain password.

## 4. Test login and organizer API

Start API: `uv run uvicorn main:app --reload`

### Login as support

Bootstrap login is `support` (configurable via `SEED_SUPPORT_LOGIN`). Password from `SEED_SUPPORT_PASSWORD`.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"support","password":"your-support-password"}'
```

Save `access_token`. If `is_temp_password` is `true`, call `POST /api/v1/auth/change-password` first.

### Create another organizer (optional API check)

You only need **Support (ADMIN)** in DB to test this; the supervisor from bootstrap is separate.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/admin/users/supervisor \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "org_api",
    "password": "orgpass123",
    "first_name": "Ivan",
    "last_name": "Org"
  }'
```

Expect `200` and `"role": "SUPERVISOR"`. New row appears in DBeaver.  
Same flow in Swagger: `/docs` → Authorize → `POST /api/v1/admin/users/supervisor`.

| Caller | Result |
|--------|--------|
| Support (ADMIN) | 200 — user created |
| SUPERVISOR / USER | 403 |
| Duplicate login | 400 |

## Two ways to get SUPERVISOR

| Method | When |
|--------|------|
| `bootstrap_users.py` + `SEED_SUPERVISOR_*` | First organizer on server |
| `POST /admin/users/supervisor` | More organizers later (Support token) |

When the supervisor UI exists, you can stop creating organizers via CLI (comment out `seed_supervisor_user` in `bootstrap_users.py` on the server).

## See also

- [.env.example](../.env.example) — all variable names  
- [CONFIG.md](CONFIG.md) — settings reference  
- [API_GUIDE.md](API_GUIDE.md) — RBAC and routes  
