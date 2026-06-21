# API Guide

FastAPI application, authentication, RBAC, HTTP endpoints, and service layer integration.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Running the Application](#running-the-application)
- [Architecture](#architecture)
- [Authentication](#authentication)
- [Role-Based Access Control](#role-based-access-control)
- [Multi-Contest API](#multi-contest-api)
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
| OpenAPI contract | 📋 Authoritative spec | `agent_docs/contracts/api_v1.yaml` |
| HTTP integration tests | ✅ Stage 1.5 | `tests/api/` — loader DB + httpx ASGI |

**Before → After (Stage 1.5):** Routers no longer map `ValueError`/`PermissionError` locally. Services raise `AppError` subclasses; `error_handlers` returns JSON `{detail, code}` with Russian `detail` for domain errors.

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
| Entry point | `main.py` | App factory, CORS, `setup_logging()`, `register_error_handlers()`, routers under `/api/v1` |
| Error mapping | `src/api/error_handlers.py` | `AppError` → HTTP JSON; unhandled → 500 + `notify_admin()` |
| Exceptions | `src/core/exceptions.py` | `AppError` hierarchy (`NotFoundError`, `ValidationError`, `ContestRuleError`, …) |
| Logging | `src/core/logging_config.py` | Root logger format; level from `LOG_LEVEL` |
| Dependencies | `src/api/deps.py` | DB session, JWT user resolution, RBAC, contest context, auto-close hook |
| Routers | `src/api/v1/*.py` | HTTP mapping only — delegates to services or `src/api/handlers/` |
| Shared handlers | `src/api/handlers/` | DRY builders for predictions view and leaderboard/results [NEW] |
| Schemas | `src/schemas/*.py` | Pydantic request/response models |
| Security | `src/core/security.py` | bcrypt password hash/verify, JWT encode/decode |
| Services | `src/services/` | Business logic; raise `AppError`, never `HTTPException` |
| Alerts | `src/services/notification_service.py` | `notify_admin()` stub for critical failures [NEW] |

## Authentication [NEW]

JWT bearer tokens. Payload: `{sub: user_id, role, exp}`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | None | Verify credentials → `{access_token, token_type, is_temp_password}` |
| `POST` | `/api/v1/auth/change-password` | Bearer | Change password; clears `is_temp_password` |
| `GET` | `/api/v1/auth/me` | Bearer | Return current user profile |

**Temp password flow:** While `is_temp_password=true`, only `/auth/change-password` and `/auth/me` are allowed without restriction. Mutating endpoints (e.g. `POST /rounds/{id}/predictions`) return `403` via `require_not_temp_password`.

Bad credentials → `401` (`Неверный логин или пароль`). Invalid/expired token → `401`. Auth/RBAC responses use Russian `detail` only (no `code` field).

Configuration: [CONFIG.md — JWT settings](CONFIG.md#environment-variables).

## Role-Based Access Control [NEW]

`RoleChecker(*roles)` dependency in `src/api/deps.py`.

| Role | Capabilities |
|------|-------------|
| **Visitor** (no token) | Public GET: rounds list, leaderboard, results (CALCULATED/PUBLISHED rounds only) |
| **USER** | Own predictions read/write |
| **SUPERVISOR** | Round/match/result/VOID, calculate, publish, read contest settings |
| **ADMIN** | All SUPERVISOR actions + recalculate, contest lifecycle, exceptional tie-break, safe delete, **create organizers** |

**Contest status guards:** When `contests.status ∈ {PAUSED, FINISHED}` for the target contest, all mutating round/match/prediction operations return `403`. Public GETs remain allowed.

## Multi-Contest API [NEW]

Stage 1.4 introduces contest-scoped routes under `/api/v1/contests/{contest_id}/…`. Legacy 1.3 paths (no `contest_id`) remain as **deprecated shims** resolving the default contest (`resolve_default_contest_id`).

### Contest management (SUPERVISOR+ / ADMIN)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/contests` | SUPERVISOR+ | List all contests |
| `POST` | `/contests` | SUPERVISOR+ | Create contest (setup phase) |
| `GET` | `/contests/{id}` | SUPERVISOR+ | Contest details |
| `PATCH` | `/contests/{id}` | SUPERVISOR+ | Update settings (blocked when `is_locked`) |
| `POST` | `/contests/{id}/pause` | ADMIN | RUNNING → PAUSED |
| `POST` | `/contests/{id}/resume` | ADMIN | PAUSED → RUNNING |
| `POST` | `/contests/{id}/finish` | ADMIN | RUNNING\|PAUSED → FINISHED |
| `DELETE` | `/contests/{id}` | ADMIN | FK-safe wipe; body `{confirm: "DELETE"}` |

### Setup phase (SUPERVISOR+)

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST/PATCH/DELETE` | `/contests/{id}/teams` | Team CRUD |
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

`ContestContext` dependency validates `contest_id` exists (404 if not).

## Admin User Management [NEW]

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/admin/users/supervisor` | ADMIN | Create contest organizer (`SUPERVISOR` role) |

Request body: `login`, `password`, `first_name`, `last_name`, optional `is_temp_password` (default `false`).

CLI/bootstrap alternative before admin UI: [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md).

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
| First round activation | `round_service` sets `is_locked=true`; lifecycle sets `status=RUNNING` |
| Settings PATCH when locked | `403 ContestLocked` — structural fields and `rules_json` frozen |
| Settings GET when locked | Always allowed (SUPERVISOR+) — read-only snapshot |
| Exceptional tie-break update | Allowed by ADMIN even when locked — not part of contest rules |
| Safe delete | ADMIN only; requires `PAUSED` + grace period elapsed (or `CONTEST_ALLOW_INSTANT_DELETE=true`) |

**Safe delete wipe** (`contest_teardown.wipe_contest_data`): deletes contest-scoped `predictions`, `scores`, `matches`, `rounds`, `teams`, `contest_participants`, and the `contests` row; keeps ADMIN users by default.

**Domain error mapping** (defined in `src/core/exceptions.py`, mapped in `src/api/error_handlers.py`):

| Exception | HTTP | `code` (typical) |
|-----------|------|------------------|
| `NotFoundError` | 404 | `NOT_FOUND` |
| `ValidationError` | 400 | `VALIDATION_ERROR` |
| `ScoreOutOfRangeError` | 422 | `SCORE_OUT_OF_RANGE` |
| `ContestRuleError` | 403 | `CONTEST_RULE_VIOLATION` / `DEADLINE_PASSED` / … |
| `ContestLockedError` | 403 | `CONTEST_LOCKED` |
| `GracePeriodError` | 400 | `GRACE_PERIOD_ACTIVE` |
| `IllegalTransitionError` | 409 | `ILLEGAL_TRANSITION` |
| `ContestNotPausedError` | 403 | `CONTEST_NOT_PAUSED` |
| `ContestDeleteDisabledError` | 403 | `CONTEST_DELETE_DISABLED` |
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

**Activation side-effect:** `contests.is_locked = True` when transitioning to `ACTIVE`. API hook then calls `ensure_running_on_first_activation` → `status=RUNNING`.

### `match_service.py`

```python
async def set_result(session, match_id, score1: int, score2: int) -> Match
async def change_status(session, match_id, new_status: MatchStatus) -> Match
```

- `set_result`: validates `0 ≤ score ≤ max_score_value`; sets `FINISHED`.
- `change_status(VOID)`: if round is `CALCULATED`, triggers `recalculate_round` atomically.

### `prediction_service.py`

```python
async def submit_batch(session, user_id, round_id, items: list[tuple[int,int,int]]) -> int
async def visible_predictions(session, round_id, viewer_role, viewer_id) -> list[dict]
```

API adds `assert_contest_running` before submit. Incomplete batch → `400`; deadline/not ACTIVE/contest not RUNNING → `403`.

### `scoring_persistence.py`

See [SCORING_LOGIC.md — Scoring Persistence](SCORING_LOGIC.md#scoring-persistence).

### `contest_lifecycle_service.py` [NEW]

```python
async def require_unlocked(session, contest_id: int) -> Contest
async def assert_contest_running(session, contest_id: int) -> Contest
async def ensure_running_on_first_activation(session, contest_id: int) -> Contest
async def pause_contest(session, contest_id: int) / resume_contest(session, contest_id: int) / finish_contest(session, contest_id: int)
async def assert_deletable(session, contest_id: int, *, instant: bool) -> Contest
async def delete_contest_data(session, contest_id: int, *, keep_admin_users: bool) -> None
async def update_exceptional_tiebreak(session, contest_id: int, user_id, points) -> int
```

### `leaderboard_service.py` [UPDATED]

Aggregates `Score` rows, reads `contest_participants.exceptional_tiebreak_points`, calls `build_standings(manual_overrides=…)`, and builds ETag hashes for cache headers.

## Endpoints Reference [UPDATED]

Base path: `/api/v1`. **Preferred:** contest-scoped paths from [Multi-Contest API](#multi-contest-api). Legacy paths below are deprecated shims (default contest).

### Public (no auth) — legacy shims

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/rounds` | List rounds (default contest) ⚠️ deprecated |
| `GET` | `/leaderboard` | Global standings ⚠️ deprecated |
| `GET` | `/rounds/{id}/leaderboard` | Round standings ⚠️ deprecated |
| `GET` | `/rounds/{id}/results` | Match results + per-user points ⚠️ deprecated |

### User (Bearer, USER+) — legacy shims

| Method | Path | Description |
|--------|------|-------------|
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
| `POST` | `/admin/users/supervisor` | Create organizer (SUPERVISOR) account [NEW] |

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
| `CONTEST_LOCKED` | 403 |
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
| Errors & logging policy (RU) | [ERROR_LOGGING.md](ERROR_LOGGING.md) |
