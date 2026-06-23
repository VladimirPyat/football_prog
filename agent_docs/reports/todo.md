# Future features & improvements backlog

Append-only notes for ideas not yet scheduled in a stage. When an item lands in a Planner draft, mark it **Done** with stage reference — do not delete history.

---

## Logging & observability

### Auth audit log (`auth.log`) — **Open**

**Goal:** Record successful and failed login attempts separately from the main application log.

**Why deferred:** Current auth uses plain `HTTPException(401)` in `src/api/v1/auth.py` with no `logger` calls (Stage 1.5 policy: no passwords in logs). Adding ad-hoc `logger.warning` in the handler works but couples auth to logging.

**Preferred direction (later):**
- Dedicated file e.g. `logs/auth.log` or `auth.log` next to `app.log`
- **Middleware** on `/api/v1/auth/login` (and optionally `/change-password`) that logs:
  - timestamp, client IP (if available), login from JSON body (**never password**), HTTP status, outcome (`success` / `failed`)
- Or structured `AppError` subclass for auth failures routed through `error_handlers` — evaluate vs middleware for minimal router churn

**Related:** `agent_docs/reports/test_2.1.md` — `[ENV-LOADER-AUTH]` (loader users cannot login with password `user`)

---

## Dev environment

### Fix loader user passwords for out-of-box login — **Open**

After `dev_setup.py`, document login should match CSV (`shutov` / `user`) or hash real password `user` in `load_test_data.py`. See `test_2.1.md` § `[ENV-LOADER-AUTH]`.

---

## Infrastructure

### Docker Compose one-command stack — **Open (Stage 3)**

Replace manual `dev_setup.py --run` with compose services for API, UI, and optional cron sidecar for `archive_logs.py`.

---

*Last updated: 2026-06-24 — file logging + log archive script added; auth.log noted for future middleware approach.*
