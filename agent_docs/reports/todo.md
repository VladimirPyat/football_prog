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

### Fix loader user passwords for out-of-box login — **Resolved (2.1.1)**

Demo USER `user/user` seeded in `bootstrap_users.py` after loader. Loader CSV users still have placeholder hashes — use `shutov`/`user` only if hash fixed separately. See `test_2.1.md` § `[ENV-LOADER-AUTH]`.

---

## Stage 2 — Frontend cleanup

### Remove demo user from bootstrap after 2.3 invite UI — **Open**

**When:** Sub-stage **2.3** delivers supervisor participant invite UI (`POST …/participants`).

**Action:** Remove `seed_demo_user()` from `src/scripts/bootstrap_users.py` and `SEED_DEMO_USER_*` from settings; update `DEV_SETUP.md` test logins to document invite-created users or a documented test fixture.

**Tracked in:** `bootstrap_users.py` TEMPORARY comment; `coder_2.1.1.md` §3.1.

### CONTEST_LOCKED vs invite E2E on dev_setup contest — **Open (documented for 2.3 tester)**

After `dev_setup.py`, contest `id=1` is **RUNNING** and **`is_locked=true`**. Supervisor invite (`POST …/participants`) returns `403` with code `CONTEST_LOCKED`.

**For 2.3 E2E:** use a **fresh DRAFT contest** (`POST /api/v1/contests`) for SETUP/invite flows — not contest `1`.

**Not in scope for 2.1.1:** backend dev flag to unlock contest `1` or auto-create DRAFT contest in dev_setup.

**Referenced in:** `tester_2.3.md` §2.1, `coder_2.1.1.md` §3.5.

---

## Infrastructure

### Docker Compose one-command stack — **Open (Stage 3)**

Replace manual `dev_setup.py --run` with compose services for API, UI, and optional cron sidecar for `archive_logs.py`.

---

## Stage 2 — Supervisor rounds UX

### Backend: block ACTIVE round structure edits — **Open**

**When:** After frontend policy (2026-06-27) forbids team changes on ACTIVE tours in UI.

**Action:** Harden `PATCH …/admin/rounds/{id}` in `contest_ops.py` / `admin_rounds.py` — reject `team1_id` / `team2_id` on `ACTIVE` rounds regardless of prediction deadline (supervisor mistakes → admin rebuilds tour).

**Priority:** Low — frontend-only guard is sufficient for normal supervisor flow.

---

*Last updated: 2026-06-27 — ACTIVE match schedule UX; backend structure lock backlog.*
