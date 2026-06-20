# API Guide

FastAPI application, authentication, RBAC, HTTP endpoints, and service layer integration.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Running the Application](#running-the-application)
- [Architecture](#architecture)
- [Authentication](#authentication)
- [Role-Based Access Control](#role-based-access-control)
- [Contest Lifecycle & Immutability](#contest-lifecycle--immutability)
- [Service Layer](#service-layer)
- [Endpoints Reference](#endpoints-reference)
- [HTTP Caching](#http-caching)
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
| FastAPI application | ✅ Stage 1.3 | `main.py` |
| JWT authentication (bcrypt + python-jose) | ✅ Stage 1.3 | `src/core/security.py`, `src/api/v1/auth.py` |
| Pydantic request/response schemas | ✅ Stage 1.3 | `src/schemas/` |
| Role-based access control | ✅ Stage 1.3 | `src/api/deps.py` — `RoleChecker` |
| OpenAPI contract | 📋 Authoritative spec | `agent_docs/contracts/api_v1.yaml` |

**Before → After:** Stage 1.2 exposed services only as Python callables. Stage 1.3 wires all contracted HTTP endpoints with thin routers (no business logic in routes).

## Running the Application [NEW]

```bash
uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET /health` → `{"status": "ok"}`  
Interactive docs: `http://localhost:8000/docs`

## Architecture [UPDATED]

```
Client → FastAPI (Uvicorn) → CORS → RoleChecker / auth deps → Pydantic validation → Services → SQLAlchemy async
```

| Layer | Path | Role |
|-------|------|------|
| Entry point | `main.py` | App factory, CORS, router mounting under `/api/v1` |
| Dependencies | `src/api/deps.py` | DB session, JWT user resolution, RBAC, cache headers |
| Routers | `src/api/v1/*.py` | HTTP mapping only — delegates to services |
| Schemas | `src/schemas/*.py` | Pydantic request/response models |
| Security | `src/core/security.py` | bcrypt password hash/verify, JWT encode/decode |
| Services | `src/services/` | Business logic (unchanged from 1.2 where possible) |

## Authentication [NEW]

JWT bearer tokens. Payload: `{sub: user_id, role, exp}`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | None | Verify credentials → `{access_token, token_type, is_temp_password}` |
| `POST` | `/api/v1/auth/change-password` | Bearer | Change password; clears `is_temp_password` |
| `GET` | `/api/v1/auth/me` | Bearer | Return current user profile |

**Temp password flow:** While `is_temp_password=true`, only `/auth/change-password` and `/auth/me` are allowed; all other authenticated endpoints return `403`.

Bad credentials → `401`. Invalid/expired token → `401`.

Configuration: [CONFIG.md — JWT settings](CONFIG.md#environment-variables).

## Role-Based Access Control [NEW]

`RoleChecker(*roles)` dependency in `src/api/deps.py`.

| Role | Capabilities |
|------|-------------|
| **Visitor** (no token) | Public GET: rounds list, leaderboard, results (CALCULATED/PUBLISHED rounds only) |
| **USER** | Own predictions read/write |
| **SUPERVISOR** | Round/match/result/VOID, calculate, publish, read contest settings |
| **ADMIN** | All SUPERVISOR actions + recalculate, contest lifecycle, exceptional tie-break, safe delete |

**Contest status guards:** When `contest_settings.status ∈ {PAUSED, FINISHED}`, all mutating round/match/prediction operations return `403`. Public GETs remain allowed.

## Contest Lifecycle & Immutability [NEW]

Status machine on `contest_settings.status` (managed by `contest_lifecycle_service.py`):

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
| Safe delete | ADMIN only; requires `PAUSED` + grace period elapsed (or instant flag in test env) |

**Domain error mapping:**

| Exception | HTTP |
|-----------|------|
| `ContestLockedError` | 403 |
| `GracePeriodError` | 400 |
| `IllegalTransitionError` | 409 |
| `ContestNotPausedError` | 400 |

## Service Layer [UPDATED]

All services are `async` functions using `AsyncSession`. Routers wrap calls in transactions via `get_db`.

### `round_service.py`

```python
async def transition_round(session, round_id, target_status: RoundStatus) -> Round
async def set_deadline(session, round_id, new_deadline: datetime) -> Round
```

**Status machine** (one-step only, illegal transitions raise `ValueError`):
```
DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED
```

**Activation side-effect:** `contest_settings.is_locked = True` when transitioning to `ACTIVE`. API hook then calls `ensure_running_on_first_activation` → `status=RUNNING`.

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
async def require_unlocked(session) -> ContestSettings
async def assert_contest_running(session) -> ContestSettings
async def ensure_running_on_first_activation(session) -> ContestSettings
async def pause_contest(session) / resume_contest(session) / finish_contest(session)
async def assert_deletable(session, *, instant: bool) -> ContestSettings
async def delete_contest_data(session, *, keep_admin_users: bool) -> ContestSettings
async def update_exceptional_tiebreak(session, user_id, points) -> int
```

### `leaderboard_service.py` [NEW]

Aggregates `Score` rows, calls `build_standings(manual_overrides=users.exceptional_tiebreak_points)`, and builds ETag hashes for cache headers.

## Endpoints Reference [UPDATED]

Base path: `/api/v1`

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/rounds` | List all rounds |
| `GET` | `/leaderboard` | Global standings (CALCULATED/PUBLISHED rounds) |
| `GET` | `/rounds/{id}/leaderboard` | Round standings |
| `GET` | `/rounds/{id}/results` | Match results + per-user points |

### User (Bearer, USER+)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/rounds/{id}/predictions` | Visibility-filtered predictions (auth required) |
| `POST` | `/rounds/{id}/predictions` | Batch prediction save (all matches required) |

### Supervisor (Bearer, SUPERVISOR or ADMIN)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/contest-settings` | Read contest configuration |
| `PATCH` | `/admin/contest-settings` | Update settings (blocked when `is_locked`) |
| `POST` | `/admin/rounds` | Create round with matches |
| `PATCH` | `/admin/rounds/{id}` | Update round deadline |
| `POST` | `/admin/rounds/{id}/activate` | DRAFT → ACTIVE |
| `POST` | `/admin/rounds/{id}/calculate` | CLOSED → CALCULATED |
| `POST` | `/admin/rounds/{id}/publish` | CALCULATED → PUBLISHED |
| `PUT` | `/admin/matches/{id}/result` | Enter final score |
| `PATCH` | `/admin/matches/{id}/status` | VOID / POSTPONED / CANCELED |

### Admin only (Bearer, ADMIN)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/contest/pause` | RUNNING → PAUSED |
| `POST` | `/admin/contest/resume` | PAUSED → RUNNING |
| `POST` | `/admin/contest/finish` | RUNNING\|PAUSED → FINISHED |
| `DELETE` | `/admin/contest` | FK-safe wipe; body `{confirm: "DELETE"}` |
| `PUT` | `/admin/users/{user_id}/exceptional-tiebreak` | Set tie-break points (allowed when locked) |
| `POST` | `/admin/recalculate` | Re-run scoring for all CALCULATED rounds |

> Legacy `POST /admin/leaderboard/{round_id}/override` removed — replaced by per-user exceptional tie-break endpoint.

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

**Not cached:** predictions GET/POST, all admin routes, contest-settings PATCH.

TTL configurable via [CONFIG.md](CONFIG.md#environment-variables).

## Related Documentation

| Topic | Document |
|-------|----------|
| Database tables & constraints | [DB_REFERENCE.md](DB_REFERENCE.md) |
| Env vars & seed | [CONFIG.md](CONFIG.md) |
| Points, bonuses & tie-breakers | [SCORING_LOGIC.md](SCORING_LOGIC.md) |
