# API Guide

FastAPI routes, authentication, and request/response schemas.

## Table of Contents

- [Implementation Status](#implementation-status)
- [Planned Architecture](#planned-architecture)
- [Planned User Endpoints](#planned-user-endpoints)
- [Planned Supervisor Endpoints](#planned-supervisor-endpoints)
- [Related Documentation](#related-documentation)

## Implementation Status [NEW]

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI application | ❌ Not implemented | `main.py` is a placeholder stub |
| JWT authentication | ❌ Stage 1 | Planned: python-jose + bcrypt |
| Pydantic request/response schemas | ❌ Stage 1 | — |
| Role-based access control | ❌ Stage 1 | `RoleChecker` middleware planned |
| OpenAPI contract | 📋 Draft | `agent_docs/contracts/api_v1.yaml` |

**Before → After:** No HTTP API existed. Stage 0 delivered only the [database layer](DB_REFERENCE.md) and [configuration](CONFIG.md).

## Planned Architecture [NEW]

```
Client → FastAPI (Uvicorn) → RoleChecker → Pydantic validation → Services → SQLAlchemy async
```

Dependencies to be added in Stage 1: `fastapi`, `uvicorn`, `python-jose`, `bcrypt`, `httpx` (tests).

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
