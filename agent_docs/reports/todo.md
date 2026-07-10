# Future features & improvements backlog

Append-only notes for ideas not yet scheduled in a stage. When an item lands in a Planner draft, mark it **Done** with stage reference — do not delete history.

---

## Logging & observability

### Auth audit log (`auth.log`) — **Done (todo_backend_fix)**

**Goal:** Record successful and failed login attempts separately from the main application log.

**Implemented:** `AuthAuditMiddleware` on `POST /api/v1/auth/login` → `logs/auth.log` (see `src/core/auth_audit.py`, `config/settings.py` `auth_log_file`).

**Why deferred (original):** Current auth uses plain `HTTPException(401)` in `src/api/v1/auth.py` with no `logger` calls (Stage 1.5 policy: no passwords in logs). Adding ad-hoc `logger.warning` in the handler works but couples auth to logging.

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

### Remove demo user from bootstrap after 2.3 invite UI — **Done (todo_backend_fix)**

**When:** Sub-stage **2.3** delivers supervisor participant invite UI (`POST …/participants`).

**Action:** Remove `seed_demo_user()` from `src/scripts/bootstrap_users.py` and `SEED_DEMO_USER_*` from settings; update `DEV_SETUP.md` test logins to document invite-created users or a documented test fixture.

**Tracked in:** `bootstrap_users.py` TEMPORARY comment; `coder_2.1.1.md` §3.1.

### CONTEST_LOCKED vs invite E2E on dev_setup contest — **Closed (documented)**

After `dev_setup.py`, contest `id=1` is **RUNNING** and **`is_locked=true`**. Supervisor invite (`POST …/participants`) returns `403` with code `CONTEST_LOCKED`.

**For 2.3 E2E:** use a **fresh DRAFT contest** (`POST /api/v1/contests`) for SETUP/invite flows — not contest `1`.

**Not in scope for 2.1.1:** backend dev flag to unlock contest `1` or auto-create DRAFT contest in dev_setup.

**Referenced in:** `tester_2.3.md` §2.1, `coder_2.1.1.md` §3.5.

---

## Infrastructure

### Docker Compose one-command stack — **Deferred (Stage 3 / deploy)**

Replace manual `dev_setup.py --run` with compose services for API, UI, and optional cron sidecar for `archive_logs.py`.

---

## Stage 2 — Supervisor rounds UX

### Backend: block ACTIVE round structure edits — **Done (todo_backend_fix)**

**When:** After frontend policy (2026-06-27) forbids team changes on ACTIVE tours in UI.

**Action:** Harden `PATCH …/admin/rounds/{id}` in `contest_ops.py` / `admin_rounds.py` — reject `team1_id` / `team2_id` on `ACTIVE` rounds regardless of prediction deadline (supervisor mistakes → admin rebuilds tour).

**Priority:** Low — frontend-only guard is sufficient for normal supervisor flow.

---

## Stage 2 — QA / supervisor setup

### «Создать по образцу» — frontend wizard (phase 1, no new API) — **Deferred**

**Goal:** Speed up manual QA (e.g. [SUPERVISOR_TESTING_SCENARIOS.md §11](../../manuals/SUPERVISOR_TESTING_SCENARIOS.md#11-кросс-проверка-организатора-и-участников-end-to-end)) when the same contest setup is created and deleted many times — avoid re-entering parameters, teams, and invite rows by hand.

**Phase 1 — frontend-only** (orchestrate existing endpoints; **no** `POST …/duplicate` on backend yet):

| Copy from source contest | How | Notes |
|--------------------------|-----|-------|
| Contest parameters | `GET /contests/{id}` → `POST /contests` + `PATCH` new id | `total_teams`, `matches_per_round`, `total_rounds`, `is_round_robin`, `rules_json` (scoring, tiebreakers, constraints) |
| Team names | `GET …/teams` → `POST …/teams` per row | `name`, `short_name` only; **no** logo file copy — new teams get **default logo** |
| Participant invites | `GET …/participants` → `POST …/participants` per row | `email`, `first_name`, `last_name` (optional `login`); all land as **PENDING** with new `temp_password` / `setup_url` |
| Rounds, predictions, results | **Do not copy** | New contest stays DRAFT until supervisor starts and creates tours |

**UX sketch:** button near «+ Новый конкурс» or on contest picker — «Создать по образцу» → pick source → progress «параметры → команды → приглашения (N/M)» → redirect to new DRAFT settings. Show partial-failure summary if an invite fails mid-batch.

**Dev workflow after wizard:** `dev_invite_setup.py confirm-all --contest-id <new_id>` (see [DEV_SETUP.md](../../manuals/DEV_SETUP.md)). Not used in real contests — participants complete setup via email link.

**Explicit non-goals (phase 1):**
- Re-enroll **existing** `user_id` / same logins in new contest (requires backend `duplicate` or `enroll_existing` — defer to phase 2 if needed).
- Copy uploaded team logo files (only default logo on new teams).
- Atomic all-or-nothing clone (acceptable partial state for QA; user can delete DRAFT and retry).

**Phase 2 (later, optional):** `POST /contests/{id}/duplicate` on backend for atomic clone + `enroll_existing` users — only if product needs «season 2» with same accounts without re-invite.

**Referenced in:** manual cross-check route §11; supervisor SETUP flows S1.1–S1.5.

---

## Stage 2 — Supervisor participants UI

### Participants table: login column — **Done (todo_front_fix)**

Supervisor settings → participants: show `login` column (distinct from email when invite uses custom login).

---

*Last updated: 2026-07-10 — todo_backend_fix + todo_front_fix (auth audit, demo user removal, ACTIVE round API guard, participants login column).*
