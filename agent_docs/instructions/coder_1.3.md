# Coder Instructions — Stage 1.3: API Integration & Triggers

> Status gate: `INSTRUCTIONS_READY`, with 1.1 and 1.2 at `TEST_PASS`. Code/comments
> English; user report Russian. Contracts: `agent_docs/contracts/api_v1.yaml` (authoritative
> endpoint shapes + RBAC), `leaderboard_tiebreakers.md`, `bonus_rules.md`, `db_schema.md`.

## 1. Objective
Expose the 1.1 engine and 1.2 services over FastAPI: authentication (JWT + bcrypt),
RBAC via a RoleChecker dependency, all endpoints in `api_v1.yaml`, the atomic
`calculate` trigger, and public leaderboard/results with HTTP caching headers.
Thin routers — no business logic in routes. No magic numbers.

## 2. Scope — files you may create/modify
```
main.py                              # FastAPI app, CORS, router mounting, error handlers
src/core/security.py                 # bcrypt hashing, JWT encode/decode
src/api/__init__.py
src/api/deps.py                      # DB session, current_user, RoleChecker
src/schemas/{auth,predictions,rounds,admin,leaderboard}.py   # Pydantic v2 DTOs
src/api/v1/{auth,rounds,predictions,admin_rounds,admin_results,admin_misc}.py
config/settings.py                   # EXTEND: jwt secret/alg/expiry, cors origins (env-driven)
tests/unit/test_api_unit_1_3.py      # your unit tests (§7): security + schema validation
```
Add dependencies (with the project's `uv add`, **only after the user has approved** the
list in `draft_1.md` §9): `fastapi`, `uvicorn[standard]`, `python-jose[cryptography]`,
`passlib[bcrypt]`, `python-multipart`. If not yet approved → HALT and ask.

## 3. Auth & security (`src/core/security.py`, `src/api/v1/auth.py`)
- `POST /api/v1/auth/login`: verify bcrypt hash; return `{access_token, token_type, is_temp_password}`.
  JWT payload `{sub: user_id, role, exp}`; secret/alg/expiry from settings (env). Bad creds → 401.
- `POST /api/v1/auth/change-password`: requires auth; verifies old password, sets new
  hash, clears `is_temp_password`. While `is_temp_password` is true, restrict the user to
  only this endpoint + `/auth/me` (any other → 403).
- `GET /api/v1/auth/me`: return current `UserOut`.

## 4. RBAC (`src/api/deps.py`)
- `get_current_user` decodes JWT, loads user. `RoleChecker(*roles)` dependency authorizes.
- Matrix: public GETs (rounds list, leaderboard, results of CALCULATED/PUBLISHED rounds)
  need no token; USER → own predictions r/w + own data; SUPERVISOR → round/match/result/VOID/
  calculate/override; ADMIN → also `/admin/recalculate`. Unauthorized role → 403; missing
  token on protected route → 401.

## 5. Endpoints — implement exactly per `api_v1.yaml`
Wire each route to the 1.2 services; map domain errors to HTTP codes:
- Predictions: `POST /rounds/{id}/predictions` (batch-only; incomplete → 400; deadline/not
  ACTIVE → 403; bad score → 422). `GET /rounds/{id}/predictions` applies the privacy filter
  (`prediction_service.visible_predictions`).
- Admin rounds: `POST /admin/rounds` (max `matches_per_round`, unique teams, 24h → 400),
  `PATCH /admin/rounds/{id}`, `/activate`, `/calculate`, `/publish`.
- Admin matches: `PUT /admin/matches/{id}/result`, `PATCH /admin/matches/{id}/status` (VOID
  triggers atomic recalculation via 1.2).
- `POST /admin/leaderboard/{round_id}/override`: persist manual tie-break priorities into
  `contest_settings.rules_json.tiebreakers.manual_overrides` (per `leaderboard_tiebreakers.md`).
- `POST /admin/recalculate` (ADMIN): recompute all CALCULATED/PUBLISHED rounds atomically.

## 6. `calculate` trigger, leaderboard & caching
- `POST /admin/rounds/{id}/calculate` → calls `scoring_persistence.calculate_round` (atomic),
  returns `{round_id, status: CALCULATED, users_scored}`. Idempotent re-runs allowed before PUBLISH.
- `GET /rounds/{id}/leaderboard`, `GET /rounds/{id}/results`, `GET /leaderboard`:
  build responses from persisted `scores` via a `LeaderboardService` that applies the
  tie-break ordering from `leaderboard_tiebreakers.md` (use `src/scoring/standings.py`
  aggregation; counts come from the `count_*` columns). Results before CALCULATED → 404/empty
  per contract. Set `Cache-Control: public, max-age=300, stale-while-revalidate=60` + `ETag`
  on these public GETs; private/forms endpoints are not cached.

## 7. MANDATORY unit tests (`tests/unit/test_api_unit_1_3.py`)
Pure, fast units (no full server needed): 
- **Security**: bcrypt hash/verify round-trip; JWT encode→decode returns sub/role; expired
  token rejected; tampered token rejected.
- **Schema validation (Pydantic)**: score `21` → validation error; `0` accepted; batch with
  missing `match_id` rejected; negative score rejected. Confirms NULL/0 boundary at the edge.
- **RoleChecker**: USER token denied on a SUPERVISOR dependency; SUPERVISOR allowed.
- Run: `uv run pytest tests/unit/test_api_unit_1_3.py -v` → green.

## 8. Acceptance criteria
- App boots: `uv run uvicorn main:app` imports without error; OpenAPI matches `api_v1.yaml`
  routes. All limits/secrets from config/env; no hardcoding. Routers contain no business logic.
- Unit tests pass. (Full HTTP integration incl. RBAC/calculate/leaderboard is @Tester, 1.3.)
- All flows (login → submit/load → calculate → results/leaderboard) must be fully drivable
  over plain HTTP with NO test-only hooks/backdoors — @Tester's manual `verify_via_api.py`
  driver (see `tester_1.3.md` §6) uses ONLY these public endpoints.

## 9. Handoff
Append to `agent_docs/progress/stage_1.md`:
```
## YYYY-MM-DD — Coder (1.3)
- STATUS: READY_FOR_TEST
- Files: <paths>
- Verified: app import OK; pytest tests/unit/test_api_unit_1_3.py -> N passed
- Deps added (approved): <list or "none">
```
Report to user in Russian and point to `tester_1.3.md`.
