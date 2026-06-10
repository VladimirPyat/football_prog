# API Guide

Service layer, FastAPI routes, authentication, and request/response schemas.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Service Layer](#service-layer)
- [Planned Architecture](#planned-architecture)
- [Planned User Endpoints](#planned-user-endpoints)
- [Planned Supervisor Endpoints](#planned-supervisor-endpoints)
- [Related Documentation](#related-documentation)

## Implementation Status [UPDATED]

| Component | Status | Notes |
|-----------|--------|-------|
| Round service (status machine + 24h rule) | ✅ Stage 1.2 | `src/services/round_service.py` |
| Match service (results + VOID) | ✅ Stage 1.2 | `src/services/match_service.py` |
| Prediction service (batch submit + visibility) | ✅ Stage 1.2 | `src/services/prediction_service.py` |
| Scoring persistence (calculate/recalculate) | ✅ Stage 1.2 | `src/services/scoring_persistence.py` |
| FastAPI application | ❌ Stage 1.3 | HTTP routing not yet wired |
| JWT authentication | ❌ Stage 1.3 | Planned: python-jose + bcrypt |
| Pydantic request/response schemas | ❌ Stage 1.3 | — |
| Role-based access control | ❌ Stage 1.3 | `RoleChecker` middleware planned |
| OpenAPI contract | 📋 Draft | `agent_docs/contracts/api_v1.yaml` |

## Service Layer [NEW]

All services are `async` functions using `AsyncSession`. The caller is responsible for wrapping in a transaction (`async with session.begin()`).

### `round_service.py`

```python
async def transition_round(session, round_id, target_status: RoundStatus) -> Round
async def set_deadline(session, round_id, new_deadline: datetime) -> Round
```

**Status machine** (one-step only, illegal transitions raise `ValueError`):
```
DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED
```

**Activation side-effect:** `contest_settings.is_locked = True` when transitioning to `ACTIVE`.

**24h deadline rule:** `new_deadline` must be strictly before `earliest_match_datetime − deadline_rule_hours` (default 24h). The change window also closes when `now > cutoff`. All datetimes timezone-aware.

### `match_service.py`

```python
async def set_result(session, match_id, score1: int, score2: int) -> Match
async def change_status(session, match_id, new_status: MatchStatus) -> Match
```

- `set_result`: validates `0 ≤ score ≤ max_score_value` (from `contest_settings`); sets `FINISHED`.
- `change_status(VOID)`: if the match's round is `CALCULATED`, triggers `recalculate_round` atomically in the same session.
- Allowed status targets for `change_status`: `VOID`, `POSTPONED`, `CANCELED`.

### `prediction_service.py`

```python
async def submit_batch(session, user_id, round_id, items: list[tuple[int,int,int]]) -> int
async def visible_predictions(session, round_id, viewer_role, viewer_id) -> list[dict]
```

**`submit_batch` rules:**
- Requires **exactly** `matches_per_round` items covering all match IDs → `ValueError` otherwise (→ HTTP 400).
- Rejects if `now >= deadline` or `round.status != ACTIVE` → `PermissionError` (→ HTTP 403).
- Each score validated `0..max_score_value`; **0 is valid**.
- Replaces existing predictions for `(user, round)` in one transaction (all-or-nothing).

**`visible_predictions` privacy:**

| Condition | What viewer sees |
|-----------|-----------------|
| Before deadline, regular user | Own predictions (full scores) + others: `{submitted: bool}` |
| Before deadline, SUPERVISOR/ADMIN | All predictions with full scores |
| After deadline | All predictions with full scores for everyone |

### `scoring_persistence.py`

See [SCORING_LOGIC.md — Scoring Persistence](SCORING_LOGIC.md#scoring-persistence).

## Planned Architecture [UPDATED]

```
Client → FastAPI (Uvicorn) → RoleChecker → Pydantic validation → Services → SQLAlchemy async
```

Service layer (Stage 1.2) is complete. Stage 1.3 wires FastAPI routing, JWT auth, and RBAC on top.
Dependencies to be added in Stage 1.3: `fastapi`, `uvicorn`, `python-jose`, `bcrypt`, `httpx` (tests).

## Planned User Endpoints [NEW]

Base path: `/api/v1`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/rounds/{id}/leaderboard` | Visitor+ | Round/overall leaderboard |
| `POST` | `/rounds/{id}/predictions` | User | Batch prediction save (all matches required) |
| `GET` | `/rounds/{id}/results` | Visitor+ | Match results + per-user points |

### `POST /rounds/{id}/predictions` (contract sketch)

**Request:**

```json
{
  "predictions": [
    { "match_id": 1, "score1": 0, "score2": 0 }
  ]
}
```

**Rules:**

- All round matches required (atomic save)
- Scores: integers `0..20`; `0` is valid
- Rejected after round deadline → `403`
- Missing fields → `422`

**Response:** `{ "success": true, "saved_count": 8 }`

Scoring behavior: [SCORING_LOGIC.md](SCORING_LOGIC.md). DB constraints: [DB_REFERENCE.md](DB_REFERENCE.md).

## Planned Supervisor Endpoints [NEW]

Base path: `/api/v1/admin`

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `POST` | `/rounds` | Supervisor | Create round with matches |
| `PUT` | `/matches/{id}/result` | Supervisor | Enter final score, trigger calculation |
| `PATCH` | `/matches/{id}/status` | Supervisor | VOID / POSTPONED / CANCELED |
| `POST` | `/rounds/free-tour` | Supervisor | Create free tour from postponed matches |

### Key validation rules (planned)

- Max 8 matches per round
- Unique teams per round
- Deadline ≥ 24h before first match
- Result scores `0..20`; triggers batch scoring transaction

## Related Documentation [NEW]

| Topic | Document |
|-------|----------|
| Database tables & constraints | [DB_REFERENCE.md](DB_REFERENCE.md) |
| Env vars & seed | [CONFIG.md](CONFIG.md) |
| Points & bonuses | [SCORING_LOGIC.md](SCORING_LOGIC.md) |
