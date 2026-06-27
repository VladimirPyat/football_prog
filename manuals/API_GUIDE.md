# API Guide

FastAPI application, authentication, RBAC, HTTP endpoints, and service layer integration.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Running the Application](#running-the-application)
- [Architecture](#architecture)
- [Authentication](#authentication)
- [Password Setup & Invite Links (Stage 1.12)](#password-setup--invite-links-stage-112)
- [Role-Based Access Control](#role-based-access-control)
- [Multi-Contest API](#multi-contest-api)
- [Contest Discovery & User Contacts](#contest-discovery--user-contacts)
- [Admin User Management](#admin-user-management)
- [Contest Lifecycle & Immutability](#contest-lifecycle--immutability)
- [Service Layer](#service-layer)
- [Endpoints Reference](#endpoints-reference)
- [HTTP Caching](#http-caching)
- [Error Response Format](#error-response-format)
- [Logging](#logging)
- [Related Documentation](#related-documentation)

## Implementation Status [UPDATED]

| Component | Status | Path |
|-----------|--------|------|
| Round service (status machine + 24h rule) | ✅ Stage 1.2 | `src/services/round_service.py` |
| Match service (results + VOID) | ✅ Stage 1.2 | `src/services/match_service.py` |
| Prediction service (batch submit + visibility) | ✅ Stage 1.2 | `src/services/prediction_service.py` |
| Scoring persistence (calculate/recalculate) | ✅ Stage 1.2 | `src/services/scoring_persistence.py` |
| Contest lifecycle (pause/finish/delete guards) | ✅ Stage 1.3 | `src/services/contest_lifecycle_service.py` |
| Leaderboard aggregation + ETag | ✅ Stage 1.3 | `src/services/leaderboard_service.py` |
| Multi-contest API + setup phase | ✅ Stage 1.4 | `src/api/v1/contests.py`, `contest_ops.py`, … |
| FastAPI application | ✅ Stage 1.3 | `main.py` |
| JWT authentication (bcrypt + python-jose) | ✅ Stage 1.3 | `src/core/security.py`, `src/api/v1/auth.py` |
| Pydantic request/response schemas | ✅ Stage 1.3 | `src/schemas/` |
| Role-based access control | ✅ Stage 1.3 | `src/api/deps.py` — `RoleChecker` |
| Typed errors + centralized handlers | ✅ Stage 1.5 | `src/core/exceptions.py`, `src/api/error_handlers.py` |
| Structured logging | ✅ Stage 1.5 | `src/core/logging_config.py`, `LOG_LEVEL` |
| Admin alert stub | ✅ Stage 1.5 | `src/services/notification_service.py` |
| Shared HTTP handlers (DRY) | ✅ Stage 1.5 | `src/api/handlers/` |
| Organizer creation API | ✅ Stage 1.6 | `src/api/v1/admin_users.py`, `src/services/user_admin_service.py` |
| User bootstrap CLI | ✅ Stage 1.6 | `src/scripts/bootstrap_users.py`, `.env.example` |
| Contest discovery & user contacts | ✅ Stage 1.8 | `src/api/v1/me.py`, `contest_discovery_service`, `contact_service` |
| Leaderboard count columns + invite accept | ✅ Stage 1.7 | `leaderboard_service`, `participant_service`, `prediction_service` |
| Team logo upload & static assets | ✅ Stage 1.9 | `team_logo_service`, `contest_teams.py`, `main.py` static routes |
| Auth setup links + invite accept via token | ✅ Stage 1.12 | `setup_tokens.py`, `auth_setup_service.py`, `auth.py` |
| Purge unconfirmed participants on contest start | ✅ Stage 1.12 | `contest_setup_service.purge_unconfirmed_participants`, `purge_before_first_activation` |
| Supervisor training mode + contest restore | ✅ Stage 1.12 | `contest_restore_service.py`, `contests.py` restore route |
| OpenAPI contract | 📋 Authoritative spec | `agent_docs/contracts/api_v1.yaml` (v1.2.1) |
| HTTP integration tests | ✅ Stage 1.6 | `tests/api/` — loader DB + httpx ASGI |

**Before → After (Stage 1.6):** ADMIN can create global `SUPERVISOR` accounts via `POST /admin/users/supervisor`. Initial ADMIN/SUPERVISOR on a fresh DB via `bootstrap_users.py` + `SEED_*` env vars (see [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md)).

## Running the Application [NEW]

```bash
uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET /health` → `{"status": "ok"}`  
Interactive docs: `http://localhost:8000/docs`

## Architecture [UPDATED]

```
Client → FastAPI (Uvicorn) → CORS → logging
       → RoleChecker / auth deps → Pydantic validation
       → Router (thin) → Services → SQLAlchemy async
       → AppError → error_handlers → JSON {detail, code}
```

| Layer | Path | Role |
|-------|------|------|
| Entry point | `main.py` | App factory, CORS, `setup_logging()`, `register_error_handlers()`, routers under `/api/v1`, static assets mount [UPDATED] |
| Error mapping | `src/api/error_handlers.py` | `AppError` → HTTP JSON; unhandled → 500 + `notify_admin()` |
| Exceptions | `src/core/exceptions.py` | `AppError` hierarchy (`NotFoundError`, `ValidationError`, `ContestRuleError`, …) |
| Logging | `src/core/logging_config.py` | Root logger format; level from `LOG_LEVEL` |
| Dependencies | `src/api/deps.py` | DB session, JWT user resolution, RBAC, contest context, auto-close hook |
| Routers | `src/api/v1/*.py` | HTTP mapping only — delegates to services or `src/api/handlers/` |
| Admin users | `src/api/v1/admin_users.py` | `POST /admin/users/supervisor` (ADMIN only) [NEW] |
| Shared handlers | `src/api/handlers/` | DRY builders for predictions view and leaderboard/results |
| Schemas | `src/schemas/*.py` | Pydantic request/response models |
| Security | `src/core/security.py` | bcrypt password hash/verify, JWT encode/decode |
| Services | `src/services/` | Business logic; raise `AppError`, never `HTTPException` |
| Alerts | `src/services/notification_service.py` | `notify_admin()` stub for critical failures [NEW] |

## Authentication [UPDATED]

JWT bearer tokens. Payload: `{sub: user_id, role, exp}`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | None | Verify credentials → `{access_token, token_type, is_temp_password}` |
| `POST` | `/api/v1/auth/change-password` | Bearer | Change password; clears `is_temp_password`; accepts all pending contest invites (`PENDING` → `ACCEPTED`) |
| `GET` | `/api/v1/auth/me` | Bearer | Return current user profile |
| `GET` | `/api/v1/auth/me/contacts` | Bearer | Profile contacts (email, VK, TG, notify toggle) |
| `PATCH` | `/api/v1/auth/me/contacts` | Bearer | Partial update / upsert contacts |

**Before → After (Stage 1.12):** When `enforce_password_setup=true` (default), login with a temp password returns **403** `{detail, code: "PASSWORD_SETUP_REQUIRED"}` — user must complete `/auth/setup` via signed link (see [Password Setup & Invite Links](#password-setup--invite-links-stage-112)). When `enforce_password_setup=false`, legacy temp-password login + `/auth/change-password` path remains.

**Temp password flow (legacy / `enforce_password_setup=false`):** While `is_temp_password=true`, `/auth/change-password`, `/auth/me`, and `/auth/me/contacts` (GET/PATCH) are allowed without restriction. `POST .../predictions` returns `403` with `code=PARTICIPANT_NOT_ACCEPTED` until the user changes the temporary password (which also flips `contest_participants.status` to `ACCEPTED`).

Bad credentials → `401` (`Неверный логин или пароль`). Invalid/expired token → `401`. Auth/RBAC responses from `deps.py` use Russian `detail` only (no `code` field); domain errors from services include `code`.

Configuration: [CONFIG.md — auth & training settings](CONFIG.md#application-defaults-configsettingspy).

## Password Setup & Invite Links (Stage 1.12) [NEW]

Signed JWT tokens (`purpose: setup_password`) power invite acceptance and password reset without SMTP.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/auth/setup-preview?token=…` | None | Preview link: `{login, mode, already_completed}` |
| `POST` | `/api/v1/auth/complete-setup` | None | Idempotent accept + optional password set `{token, new_password?}` |
| `POST` | `/api/v1/auth/request-password-reset` | None | Always **200**; re-issues temp password when email known |

**`mode` values** (from `setup-preview`, driven by `ENFORCE_PASSWORD_SETUP`):

| `enforce_password_setup` | `mode` | UI behaviour |
|--------------------------|--------|--------------|
| `true` | `password_form` | User must submit `new_password` in `complete-setup` |
| `false` | `confirm_only` | Confirm participation only; login with temp password from letter |

**Invite response** (`POST /contests/{id}/participants`):

```json
{
  "user_id": 42,
  "login": "ivanov",
  "temp_password": "…",
  "status": "PENDING",
  "setup_url": "http://127.0.0.1:3000/auth/setup?token=…"
}
```

Link base URL from `FRONTEND_BASE_URL`; token TTL from `SETUP_TOKEN_EXPIRE_HOURS` (default 72h). Implementation: `src/core/setup_tokens.py`, `src/services/auth_setup_service.py`.

**Accept path:** `complete-setup` with `contest_id` in token sets `contest_participants.status` to `ACCEPTED`. Success does **not** auto-issue JWT — frontend redirects to login.

Dev workflow without SMTP: [DEV_SETUP.md — New contest: confirm participants](DEV_SETUP.md#new-contest-confirm-participants-without-email-stage-112).

## Role-Based Access Control [NEW]

`RoleChecker(*roles)` dependency in `src/api/deps.py`.

| Role | Capabilities |
|------|-------------|
| **Visitor** (no token) | Public GET: rounds list, leaderboard, results (CALCULATED/PUBLISHED rounds only); **`GET /contests/public`** (RUNNING contests) |
| **USER** | Own predictions read/write; **`GET /me/contests`** (enrolled contests only) |
| **SUPERVISOR** | Round/match/result/VOID, calculate, publish, read contest settings; **same pre-deadline prediction privacy as USER** (own scores only) |
| **ADMIN** | All SUPERVISOR actions + recalculate, contest lifecycle, exceptional tie-break, safe delete, **create organizers** (`POST /admin/users/supervisor`); **only role that may see all predictions before deadline** (support/troubleshooting) |

**Contest status guards:** When `contests.status ∈ {PAUSED, FINISHED}` for the target contest, all mutating round/match/prediction operations return `403`. Public GETs remain allowed.

### Organizer vs participant (same person) [NEW]

The system separates two concepts:

| Concept | Storage | Meaning |
|---------|---------|---------|
| **Global role** | `users.role` | One value per login: `USER`, `SUPERVISOR`, or `ADMIN` |
| **Contest membership** | `contest_participants` | Whether this login plays in a given contest (`PENDING` / `ACCEPTED`) |

An organizer (`SUPERVISOR`) **may** also want to submit predictions and appear on the leaderboard. There is **no** rule forbidding that in business terms, but the product model assumes **separate logins** for the two hats:

| Need | Recommended approach |
|------|----------------------|
| Run the contest (teams, rounds, results, calculate) | `SUPERVISOR` account — `bootstrap_users.py`, `POST /admin/users/supervisor`, or admin UI |
| Play as a participant | **`USER` account** — invite via `POST /contests/{id}/participants` like any other player |

**Why not one login for both?**

1. **Single global role** — `users.role` cannot be `USER` and `SUPERVISOR` at once. Invite flow always creates a new `USER`; bootstrap and organizer API create `SUPERVISOR` without enrolling them in `contest_participants`.
2. **Prediction privacy** — before a round deadline, `USER` and `SUPERVISOR` see only their own prediction scores; others appear as submitted-only. Only `ADMIN` bypasses this filter (`prediction_service.visible_predictions`). There is no supervisor “god mode” for pre-deadline picks.
3. **UI/API routing** — organizers pick contests via `GET /contests`; players via `GET /me/contests`. Two accounts keep flows clear.

**What organizers can do without playing:** manage setup and scoring, publish results, and (ADMIN only) set `exceptional_tiebreak_points` when standings are tied — they do **not** need a participant row for that.

**Operational pattern:** same human, two logins (e.g. `ivan_org` / `ivan_player`). Invite the player email through the normal participant flow; use the organizer login only for back-office work.

> **Not supported:** assigning per-contest “organizer role” or dual-role on one account. Manual `contest_participants` insert for a `SUPERVISOR` user is possible at DB level but discouraged (confusing UX; use a separate `USER` invite for playing).

## Multi-Contest API [NEW]

Stage 1.4 introduces contest-scoped routes under `/api/v1/contests/{contest_id}/…`. Legacy 1.3 paths (no `contest_id`) remain as **deprecated shims** resolving the default contest (`resolve_default_contest_id`).

### Contest management (SUPERVISOR+ / ADMIN)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/contests` | SUPERVISOR+ | List all contests |
| `POST` | `/contests` | SUPERVISOR+ | Create contest (setup phase) |
| `GET` | `/contests/{id}` | SUPERVISOR+ | Contest details |
| `PATCH` | `/contests/{id}` | SUPERVISOR+ | Update settings (blocked when `is_locked`) |
| `POST` | `/contests/{id}/pause` | SUPERVISOR+ | RUNNING → PAUSED |
| `POST` | `/contests/{id}/resume` | SUPERVISOR+ | PAUSED → RUNNING |
| `POST` | `/contests/{id}/finish` | ADMIN; SUPERVISOR when `supervisor_training_mode=true` | RUNNING\|PAUSED → FINISHED |
| `DELETE` | `/contests/{id}` | ADMIN; SUPERVISOR when `supervisor_training_mode=true` | FK-safe wipe; body `{confirm: "DELETE"}` |
| `POST` | `/contests/{id}/restore` | SUPERVISOR+ when `supervisor_training_mode=true` | Replay training-mode snapshot within restore window |

### Setup phase (SUPERVISOR+)

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST/PATCH/DELETE` | `/contests/{id}/teams` | Team CRUD |
| `POST` | `/contests/{id}/teams/{team_id}/logo` | Multipart logo upload (PNG/JPEG/GIF, max 2 MiB; SETUP only) |
| `GET/POST/DELETE` | `/contests/{id}/participants` | Invite/list/remove participants |
| `PUT` | `/contests/{id}/participants/{user_id}/exceptional-tiebreak` | Per-contest tie-break (ADMIN) |

### Contest operations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/contests/{id}/rounds` | Public | List rounds |
| `GET/POST` | `/contests/{id}/rounds/{rid}/predictions` | USER+ | Predictions view / batch save |
| `GET` | `/contests/{id}/rounds/{rid}/leaderboard` | Public | Round standings |
| `GET` | `/contests/{id}/rounds/{rid}/results` | Public | Results + points |
| `GET` | `/contests/{id}/leaderboard` | Public | Global standings |
| `POST/PATCH/…` | `/contests/{id}/admin/rounds`, `/admin/matches/…` | SUPERVISOR+ | Round/match admin (same semantics as legacy) |
| `POST` | `/contests/{id}/admin/recalculate` | ADMIN | Recalculate all CALCULATED rounds |

**Leaderboard row fields (Stage 1.7) [UPDATED]:** Each entry includes tie-break count columns from persisted scores / `StandingRow` aggregates:

| Field | Meaning |
|-------|---------|
| `count_exact_high` | Exact score with high tie-break weight |
| `count_exact` | Exact score (standard) |
| `count_diff` | Correct goal difference |
| `count_outcome` | Correct outcome only |

Round leaderboard reads per-round `scores` columns; global leaderboard uses cross-round `StandingRow` sums (same source as rank tie-breakers).

**Team logos (Stage 1.9) [UPDATED]:** `TeamOut.logo_url` is never `null` in JSON — when `teams.logo_url` is unset, the API returns `DEFAULT_TEAM_LOGO_URL` (default `/static/assets/default-team-logo.jpg`). Uploaded files are stored under `uploads/teams/{contest_id}/{team_id}.jpg` and served at `{STATIC_URL_PREFIX}/teams/{contest_id}/{team_id}.jpg`. Images are center-cropped and resized to `TEAM_LOGO_TARGET_PX` (default 64×64). Clear a custom logo with `PATCH .../teams/{id}` and `"logo_url": null`.

| Static path | Serving mechanism | Content |
|-------------|-------------------|---------|
| `/static/assets/*` | `StaticFiles` mount on `static/assets/` | Bundled read-only assets (default team logo) |
| `/static/teams/*` | Dynamic `FileResponse` route in `main.py` (path traversal guard) | Supervisor-uploaded team logos from `uploads/teams/` |

`ContestContext` dependency validates `contest_id` exists (404 if not).

## Contest Discovery & User Contacts [NEW]

Stage 1.8 closes frontend blockers B1–B3 for Stage 2.1 (Visitor home + User contest picker + profile contacts).

### User contest list (B1)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/me/contests` | Bearer (any role) | Contests where the user has a `contest_participants` row |

Response items include `participant_status` (`PENDING` \| `ACCEPTED`), global `role` (from `users.role`), contest `status`, and optional `slug`. Ordered by contest name. Organizers who are not enrolled use `GET /contests` (SUPERVISOR+), not this endpoint.

### Public discovery (B2)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/contests/public` | None | RUNNING contests only (id, name, status, slug) |

Route registered **before** `/contests/{contest_id}` to avoid path capture. Returns `Cache-Control` (same pattern as other public GETs). PAUSED and FINISHED contests are excluded by design.

### User contacts (B3)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/auth/me/contacts` | Bearer | Read contacts; defaults when no row exists |
| `PATCH` | `/auth/me/contacts` | Bearer | Partial update (upsert); empty string clears email |

Allowed while `is_temp_password=true`. Invite flow (`POST /contests/{id}/participants`) pre-populates `email` on the new user's `contacts` row.

## Admin User Management [UPDATED]

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/admin/users/supervisor` | ADMIN | Create global contest organizer (`users.role = SUPERVISOR`) |

**Request** (`CreateSupervisorRequest`):

```json
{
  "login": "org1",
  "password": "initial-password",
  "first_name": "Ivan",
  "last_name": "Organizer",
  "is_temp_password": false
}
```

**Response:** `{ "user": { "id", "login", "role": "SUPERVISOR", "first_name", "last_name", "is_temp_password" } }`

| Condition | HTTP | `code` |
|-----------|------|--------|
| Success | 200 | — |
| Duplicate login | 400 | `VALIDATION_ERROR` |
| Not ADMIN | 403 | (RBAC, no `code`) |
| Invalid body | 422 | (Pydantic) |

Does **not** auto-enroll the new user in `contest_participants` — organizer is a global role, not a player.

**First deploy:** use CLI once per empty database — [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md). Users persist in DB; bootstrap is not run on every API restart.

### `user_admin_service.py` [NEW]

```python
async def create_supervisor(session, *, login, password, first_name, last_name, is_temp_password=False) -> User
```

Hashes `password` with bcrypt; raises `ValidationError` if login taken.

## Contest Lifecycle & Immutability [UPDATED]

Status machine on `contests.status` (managed by `contest_lifecycle_service.py`):

```
DRAFT ──(first activate)──► RUNNING ──(POST /pause)──► PAUSED
                                │                         │
                                │                    (POST /resume)
                                │                         │
                                └──(POST /finish)──► FINISHED ◄──┘
```

| Rule | Enforcement |
|------|-------------|
| First round activation | **Before lock:** `purge_before_first_activation` removes all `PENDING` USER participants; then `transition_round` sets `is_locked=true`; lifecycle sets `status=RUNNING` |
| Unconfirmed purge | On first activate, `contest_setup_service.purge_unconfirmed_participants` removes `contest_participants` rows with `status=PENDING` and `users.role=USER`; orphan users deleted unless enrolled in another contest |
| Settings PATCH when locked | `403 ContestLocked` — structural fields and `rules_json` frozen |
| Settings GET when locked | Always allowed (SUPERVISOR+) — read-only snapshot |
| Exceptional tie-break update | Allowed by ADMIN even when locked — not part of contest rules |
| Safe delete | ADMIN always; SUPERVISOR when `supervisor_training_mode=true`; requires `PAUSED` + grace (or instant delete when training mode / `CONTEST_ALLOW_INSTANT_DELETE`) |
| Training restore | After delete wipe, snapshot stored in `contest_restore_snapshots`; `POST /restore` replays within `contest_restore_window_seconds` |

**Before → After (Stage 1.12):** Pause/resume opened to SUPERVISOR (not ADMIN-only). Finish/delete/restore gated by `supervisor_training_mode`. Delete creates a JSON snapshot before wipe for optional undo in training mode.

**Safe delete wipe** (`contest_teardown.wipe_contest_data`): deletes contest-scoped operational data and resets contest to empty DRAFT (contest row retained). When training mode is on, a restore snapshot is written first — see `contest_restore_service.py`.

**Domain error mapping** (defined in `src/core/exceptions.py`, mapped in `src/api/error_handlers.py`):

| Exception | HTTP | `code` (typical) |
|-----------|------|------------------|
| `NotFoundError` | 404 | `NOT_FOUND` |
| `ValidationError` | 400 | `VALIDATION_ERROR` |
| `ScoreOutOfRangeError` | 422 | `SCORE_OUT_OF_RANGE` |
| `ContestRuleError` | 403 | `CONTEST_RULE_VIOLATION` / `DEADLINE_PASSED` / `PARTICIPANT_NOT_ENROLLED` / `PARTICIPANT_NOT_ACCEPTED` / … |
| `ContestLockedError` | 403 | `CONTEST_LOCKED` |
| `GracePeriodError` | 400 | `GRACE_PERIOD_ACTIVE` |
| `IllegalTransitionError` | 409 | `ILLEGAL_TRANSITION` |
| `ContestNotPausedError` | 403 | `CONTEST_NOT_PAUSED` |
| `ContestDeleteDisabledError` | 403 | `CONTEST_DELETE_DISABLED` |
| `PasswordSetupRequiredError` | 403 | `PASSWORD_SETUP_REQUIRED` [NEW] |
| `SnapshotNotFoundError` | 404 | `SNAPSHOT_NOT_FOUND` [NEW] |
| `SnapshotExpiredError` | 410 | `SNAPSHOT_EXPIRED` [NEW] |
| Unhandled / `CriticalError` | 500 | `INTERNAL_ERROR` |

Response body: `{"detail": "<Russian message>", "code": "<CODE>"}`. See [Error Response Format](#error-response-format) and [ERROR_LOGGING.md](ERROR_LOGGING.md).

**DELETE `/contests/{id}` body:** `{ "confirm": "DELETE" }` (Pydantic `Literal`). Wrong confirm value → **422** (schema validation). Valid confirm but grace not elapsed → **400** (`GracePeriodError`).

Legacy shim: `DELETE /admin/contest` (default contest only, deprecated).

> **SQLite note:** `paused_at` may round-trip as naive datetime. Grace-period comparison in `assert_deletable` expects timezone-aware values; normalize to UTC in production code or use PostgreSQL for production.

## Service Layer [UPDATED]

All services are `async` functions using `AsyncSession`. Routers wrap calls in transactions via `get_db`.

### `round_service.py`

```python
async def transition_round(session, round_id, target_status: RoundStatus) -> Round
async def set_deadline(session, round_id, new_deadline: datetime) -> Round
```

**Status machine** (one-step only; illegal transitions raise `IllegalTransitionError`):
```
DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED
```

**Activation side-effect:** `contests.is_locked = True` when transitioning to `ACTIVE`. API calls `purge_before_first_activation` **before** lock, then `transition_round`, then `ensure_running_on_first_activation` → `status=RUNNING`.

### `match_service.py`

```python
async def set_result(session, match_id, score1: int, score2: int) -> Match
async def change_status(session, match_id, new_status: MatchStatus) -> Match
```

- `set_result`: validates `0 ≤ score ≤ max_score_value`; sets `FINISHED`.
- `change_status(VOID)`: if round is `CALCULATED`, triggers `recalculate_round` atomically.

### `prediction_service.py` [UPDATED]

```python
async def submit_batch(session, user_id, round_id, items: list[tuple[int,int,int]]) -> int
async def visible_predictions(session, round_id, viewer_role, viewer_id) -> list[dict]
```

Before deadline: own scores only for `USER` and `SUPERVISOR`; `ADMIN` sees all. After deadline: full table.

API adds `assert_contest_running` before submit. Incomplete batch → `400`; deadline/not ACTIVE/contest not RUNNING → `403`.

**Before → After (Stage 1.7):** Prediction submit no longer uses router-level `require_not_temp_password`. `submit_batch` enforces enrollment and accept status:

| Condition | HTTP | `code` |
|-----------|------|--------|
| `users.is_temp_password=true` | 403 | `PARTICIPANT_NOT_ACCEPTED` |
| No `contest_participants` row | 403 | `PARTICIPANT_NOT_ENROLLED` |
| `participant.status != ACCEPTED` | 403 | `PARTICIPANT_NOT_ACCEPTED` |

Password change (`POST /auth/change-password`) flips all `PENDING` participations to `ACCEPTED` via `participant_service.accept_pending_participations`.

### `scoring_persistence.py`

See [SCORING_LOGIC.md — Scoring Persistence](SCORING_LOGIC.md#scoring-persistence).

### `contest_lifecycle_service.py` [UPDATED]

```python
async def purge_before_first_activation(session, contest_id: int) -> int
async def require_unlocked(session, contest_id: int) -> Contest
async def assert_contest_running(session, contest_id: int) -> Contest
async def ensure_running_on_first_activation(session, contest_id: int) -> Contest
async def pause_contest(session, contest_id: int) / resume_contest(session, contest_id: int) / finish_contest(session, contest_id: int)
async def assert_deletable(session, contest_id: int, *, instant: bool) -> Contest
async def delete_contest_data(session, contest_id: int, *, deleted_by_user_id: int | None) -> None
async def update_exceptional_tiebreak(session, contest_id: int, user_id, points) -> int
```

### `auth_setup_service.py` [NEW]

Stage 1.12 — signed-link preview, complete-setup, password reset.

```python
async def preview_setup(session, token: str) -> dict
async def complete_setup(session, token: str, new_password: str | None) -> dict
async def request_password_reset(session, email: str) -> dict
```

### `contest_restore_service.py` [NEW]

Stage 1.12 — training-mode snapshot on delete and replay via `POST /contests/{id}/restore`.

```python
async def restore_contest_from_snapshot(session, contest_id: int) -> None
```

Snapshot payload (minimal): contest scalars + `rules_json`, teams, rounds, matches, participant `user_id` list.

### `contest_setup_service.py` [UPDATED]

```python
async def purge_unconfirmed_participants(session, contest_id: int) -> int
```

Removes all `PENDING` USER participants before first activation (called while contest still unlocked).

### `leaderboard_service.py` [UPDATED]

Aggregates `Score` rows, reads `contest_participants.exceptional_tiebreak_points`, calls `build_standings(manual_overrides=…)`, serializes `count_exact_high`, `count_exact`, `count_diff`, `count_outcome` on each leaderboard row, and builds ETag hashes for cache headers.

### `team_logo_service.py` [NEW]

Stage 1.9 — validate, resize (64×64 center-crop), persist team logos; resolve default URL for API responses.

```python
async def save_team_logo(session, *, contest_id, team_id, file_bytes, content_type, settings) -> str
def resolve_team_logo_url(logo_url: str | None, settings) -> str
def delete_uploaded_logo_if_custom(logo_url: str | None, settings) -> None
```

### `participant_service.py` [NEW]

Stage 1.7 — flip pending invites to accepted on password change.

```python
async def accept_pending_participations(session, user_id: int) -> int
```

### `contest_discovery_service.py` [NEW]

Stage 1.8 — contest lists for enrolled users and anonymous visitors.

```python
async def list_user_contests(session, *, user_id: int, role: str) -> list[UserContestOut]
async def list_public_contests(session) -> list[PublicContestOut]
```

- `list_user_contests`: JOIN `contests` + `contest_participants` for `user_id`; ordered by `contests.name`; echoes global `users.role`.
- `list_public_contests`: `contests.status = RUNNING` only; ordered by name.

### `contact_service.py` [NEW]

Stage 1.8 — read/upsert `contacts` row for profile endpoints.

```python
async def get_contacts(session, user_id: int) -> ContactOut
async def upsert_contacts(session, user_id: int, patch: dict) -> ContactOut
```

- Missing row → defaults (`email/vk_id/tg_id` null, `notify_enabled=false`).
- Partial PATCH via `model_dump(exclude_unset=True)` in router; empty string clears `email`.
- Invalid email → `ValidationError` (`400`, `VALIDATION_ERROR`).

## Endpoints Reference [UPDATED]

Base path: `/api/v1`. **Preferred:** contest-scoped paths from [Multi-Contest API](#multi-contest-api). Legacy paths below are deprecated shims (default contest).

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/contests/public` | RUNNING contests for Visitor discovery |
| `GET` | `/rounds` | List rounds (default contest) ⚠️ deprecated |
| `GET` | `/leaderboard` | Global standings ⚠️ deprecated |
| `GET` | `/rounds/{id}/leaderboard` | Round standings ⚠️ deprecated |
| `GET` | `/rounds/{id}/results` | Match results + per-user points ⚠️ deprecated |

### User (Bearer, USER+)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/me/contests` | Enrolled contests with `participant_status` |
| `GET` | `/auth/me/contacts` | Profile contacts |
| `PATCH` | `/auth/me/contacts` | Partial contacts update |
| `GET` | `/rounds/{id}/predictions` | Visibility-filtered predictions ⚠️ deprecated |
| `POST` | `/rounds/{id}/predictions` | Batch prediction save ⚠️ deprecated |

### Supervisor (Bearer, SUPERVISOR or ADMIN) — legacy shims

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/contest-settings` | Read contest configuration ⚠️ deprecated |
| `PATCH` | `/admin/contest-settings` | Update settings ⚠️ deprecated |
| `POST` | `/admin/rounds` | Create round with matches ⚠️ deprecated |
| `PATCH` | `/admin/rounds/{id}` | Update round deadline ⚠️ deprecated |
| `POST` | `/admin/rounds/{id}/activate` | DRAFT → ACTIVE ⚠️ deprecated |
| `POST` | `/admin/rounds/{id}/calculate` | CLOSED → CALCULATED ⚠️ deprecated |
| `POST` | `/admin/rounds/{id}/publish` | CALCULATED → PUBLISHED ⚠️ deprecated |
| `PUT` | `/admin/matches/{id}/result` | Enter final score ⚠️ deprecated |
| `PATCH` | `/admin/matches/{id}/status` | VOID / POSTPONED / CANCELED ⚠️ deprecated |

### Admin only (Bearer, ADMIN)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/users/supervisor` | Create organizer (SUPERVISOR) account |

### Admin only (Bearer, ADMIN) — legacy shims

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/contest/pause` | RUNNING → PAUSED ⚠️ deprecated |
| `POST` | `/admin/contest/resume` | PAUSED → RUNNING ⚠️ deprecated |
| `POST` | `/admin/contest/finish` | RUNNING\|PAUSED → FINISHED ⚠️ deprecated |
| `DELETE` | `/admin/contest` | FK-safe wipe ⚠️ deprecated |
| `PUT` | `/admin/users/{user_id}/exceptional-tiebreak` | Tie-break (default contest) ⚠️ deprecated |
| `POST` | `/admin/recalculate` | Re-run scoring ⚠️ deprecated |

### `POST /rounds/{id}/predictions`

**Request:**

```json
{
  "predictions": [
    { "match_id": 1, "score1": 0, "score2": 0 }
  ]
}
```

**Rules:** All round matches required (atomic save). Scores `0..20`; `0` is valid. Missing fields → `422`; incomplete batch → `400`; after deadline / not ACTIVE / contest PAUSED|FINISHED → `403`.

**Response:** `{ "success": true, "saved_count": 8 }`

## HTTP Caching [NEW]

Public GET leaderboard and results endpoints return:

```
Cache-Control: public, max-age=300, stale-while-revalidate=60
ETag: <16-char sha256 hash of score state>
```

ETag derived from `max(Score.id)` and round status — changes after calculate/VOID/recalculate.

**Not cached:** predictions GET/POST, all admin routes, contest PATCH.

TTL configurable via [CONFIG.md](CONFIG.md#environment-variables).

## Error Response Format [NEW]

Domain errors (`AppError` subclasses from `src/core/exceptions.py`) return:

```json
{ "detail": "Дедлайн тура истёк", "code": "DEADLINE_PASSED" }
```

| `code` | Typical HTTP |
|--------|----------------|
| `NOT_FOUND` | 404 |
| `VALIDATION_ERROR` | 400 |
| `SCORE_OUT_OF_RANGE` | 422 |
| `CONTEST_RULE_VIOLATION` / `DEADLINE_PASSED` / `CONTEST_NOT_RUNNING` | 403 |
| `PARTICIPANT_NOT_ENROLLED` / `PARTICIPANT_NOT_ACCEPTED` | 403 |
| `CONTEST_LOCKED` | 403 |
| `PASSWORD_SETUP_REQUIRED` | 403 [NEW] |
| `SNAPSHOT_NOT_FOUND` | 404 [NEW] |
| `SNAPSHOT_EXPIRED` | 410 [NEW] |
| `GRACE_PERIOD_ACTIVE` | 400 |
| `ILLEGAL_TRANSITION` | 409 |
| `INTERNAL_ERROR` | 500 |

- Pydantic validation: **422**, FastAPI default body (no `code`).
- Auth/RBAC (`deps.py`): `detail` only, Russian text, no `code`.
- Full policy (RU): [ERROR_LOGGING.md](ERROR_LOGGING.md).

## Logging [NEW]

Configured at startup in `main.py` via `setup_logging(settings.log_level)`.

| Level | Typical use |
|-------|-------------|
| `ERROR` | Unhandled exceptions, `notify_admin` alerts |
| `WARNING` | Recoverable fallbacks, 4xx `AppError` at HTTP boundary |
| `INFO` | Predictions saved, round calculated, contest pause/resume/finish |
| `DEBUG` | Scoring data counts, auto-close details |

Log format: `%(asctime)s %(levelname)s [%(name)s] %(message)s`

Set level with env var `LOG_LEVEL` (default `INFO`). See [CONFIG.md](CONFIG.md#environment-variables).

Recoverable internal issues (e.g. skipped NULL prediction rows) log `WARNING` and apply defaults without failing the request — see [ERROR_LOGGING.md](ERROR_LOGGING.md#категории-ошибок).

## Related Documentation

| Topic | Document |
|-------|----------|
| Database tables & constraints | [DB_REFERENCE.md](DB_REFERENCE.md) |
| Env vars & seed | [CONFIG.md](CONFIG.md) |
| Points, bonuses & tie-breakers | [SCORING_LOGIC.md](SCORING_LOGIC.md) |
| Initial ADMIN/SUPERVISOR bootstrap | [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) |
| Errors & logging policy (RU) | [ERROR_LOGGING.md](ERROR_LOGGING.md) |
