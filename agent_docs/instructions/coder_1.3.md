# Coder Instructions — Stage 1.3: API Integration & Triggers

> Status gate: `INSTRUCTIONS_READY`, with 1.1 and 1.2 at `TEST_PASS`. **Prerequisite:**
> run `coder_1.2.1.md` migration first (lifecycle columns + `exceptional_tiebreak_points`).
> Code/comments English; user report Russian. Contracts: `api_v1.yaml` (authoritative),
> `leaderboard_tiebreakers.md`, `bonus_rules.md`, `db_schema.md`.

## 1. Objective
Expose the 1.1 engine and 1.2 services over FastAPI: authentication (JWT + bcrypt),
RBAC, all endpoints in `api_v1.yaml`, atomic `calculate` trigger, public leaderboard/results
with HTTP caching, **contest immutability after start**, **lifecycle** (pause/finish/safe
delete), and **exceptional tie-break points** (admin-only, not contest rules).

Thin routers — no business logic in routes. No magic numbers.

## 2. Scope — files you may create/modify
```
main.py
src/core/security.py
src/api/__init__.py
src/api/deps.py
src/schemas/{auth,predictions,rounds,admin,leaderboard,contest}.py
src/api/v1/{auth,rounds,predictions,admin_rounds,admin_results,admin_contest,admin_misc}.py
src/services/contest_lifecycle_service.py   # NEW — guards, pause/finish/delete
src/services/contest_teardown.py            # NEW — FK-safe wipe (reuse load_test_data order)
config/settings.py                          # EXTEND: jwt, cors, grace delete flags
tests/unit/test_api_unit_1_3.py
tests/unit/test_contest_lifecycle_1_3.py    # NEW — lock guards, status machine, delete confirm
```

Add dependencies via `uv add` (only after user approval per `draft_1.md` §9):
`fastapi`, `uvicorn[standard]`, `python-jose[cryptography]`, `passlib[bcrypt]`,
`python-multipart`. If not approved → HALT.

**Do NOT modify** 1.2 services except importing new model fields. HALT if 1.2.1 migration
columns are absent.

## 3. Auth & security (`src/core/security.py`, `src/api/v1/auth.py`)
- `POST /api/v1/auth/login`: bcrypt verify → `{access_token, token_type, is_temp_password}`.
  JWT `{sub, role, exp}` from settings. Bad creds → 401.
- `POST /api/v1/auth/change-password`: auth required; clears `is_temp_password`.
  While temp password: only change-password + `/auth/me` allowed (else 403).
- `GET /api/v1/auth/me`: return `UserOut`.

## 4. RBAC (`src/api/deps.py`)
- `get_current_user`, `RoleChecker(*roles)`.
- Public GETs: rounds list, leaderboard, results (CALCULATED/PUBLISHED) — no token.
- USER: own predictions r/w.
- SUPERVISOR: round/match/result/VOID/calculate/publish.
- ADMIN: + `/admin/recalculate`, contest lifecycle, exceptional tie-break, safe delete.

**Contest status guards:** when `contest_settings.status ∈ {PAUSED, FINISHED}` block
mutating round/match/prediction ops → 403 (public GETs still allowed).

## 5. Immutability — NO rule changes after start

After first round activation (`is_locked=true`):

- **Forbidden:** any change to `contest_settings` structural fields or `rules_json`
  (scoring points, bonuses, team/round limits, participants).
- `PATCH /admin/contest-settings` → **403 ContestLocked** when `is_locked`.
- `GET /admin/contest-settings` → always allowed (SUPERVISOR+), read-only snapshot when locked.

**Exception — NOT rules:** `users.exceptional_tiebreak_points` may be updated by ADMIN
at any time via dedicated endpoint (see §5c). Does not touch `rules_json`.

Implement in `contest_lifecycle_service.py`:
- `require_unlocked(session)` → raises if `is_locked` (for settings PATCH).
- `assert_contest_running(session)` → raises if status is PAUSED or FINISHED.

## 5a. Contest lifecycle (`contest_lifecycle_service.py`)

Status machine on `contest_settings.status`:
```
DRAFT ──(first activate)──► RUNNING ──(POST /pause)──► PAUSED
                                │                         │
                                │                    (POST /resume)
                                │                         │
                                └──(POST /finish)──► FINISHED ◄──┘
```

Functions:
- `ensure_running_on_first_activation(session)` — after `round_service.transition_round`
  to ACTIVE: if `status==DRAFT` → `RUNNING` (1.2 already sets `is_locked`).
- `pause_contest(session)` — RUNNING → PAUSED, `paused_at=now`.
- `resume_contest(session)` — PAUSED → RUNNING, clear `paused_at`.
- `finish_contest(session)` — RUNNING|PAUSED → FINISHED, `finished_at=now`; close ACTIVE
  rounds to CLOSED; idempotent if already FINISHED.
- `assert_deletable(session, *, instant: bool)` — requires PAUSED + grace elapsed unless
  `contest_allow_instant_delete`.
- `delete_contest_data(session, *, keep_admin_users: bool)` — FK-safe wipe via
  `contest_teardown.py`; re-seed `contest_settings` from defaults, `status=DRAFT`,
  `is_locked=false`.

Config (`settings.py`):
```python
contest_delete_grace_seconds: int = 10
contest_delete_enabled: bool = True
contest_allow_instant_delete: bool = False  # env: CONTEST_ALLOW_INSTANT_DELETE
```

## 5b. Contest admin endpoints (`admin_contest.py`)
Wire per `api_v1.yaml`:
- `GET /admin/contest-settings` — SUPERVISOR, ADMIN.
- `PATCH /admin/contest-settings` — only when `!is_locked`; else 403.
- `POST /admin/contest/pause` — ADMIN.
- `POST /admin/contest/resume` — ADMIN.
- `POST /admin/contest/finish` — ADMIN (early termination).
- `DELETE /admin/contest` — ADMIN only; body `{confirm: "DELETE"}`; PAUSED + grace.

Map domain errors: `ContestLockedError`→403, `GracePeriodError`→400, `IllegalTransitionError`→409.

## 5c. Exceptional tie-break (`PUT /admin/users/{user_id}/exceptional-tiebreak`)
- ADMIN only. Body: `{points: int >= 0}`.
- Updates `users.exceptional_tiebreak_points` — **allowed even when `is_locked`**.
- `LeaderboardService` reads column and passes to `build_standings(manual_overrides=...)`.
- Include `exceptional_tiebreak_points` in `GET /leaderboard` rows.
- **Remove** legacy `POST /admin/leaderboard/{round_id}/override` (replaced by per-user points).

## 6. Core endpoints — wire to 1.2 services

**Integration hooks (call lifecycle guards before mutating):**
- `POST /admin/rounds/{id}/activate` → after transition: `ensure_running_on_first_activation`.
- `POST /rounds/{id}/predictions` → `assert_contest_running` + existing deadline checks.
- All admin round/match mutators → `assert_contest_running`.

**Predictions:**
- `POST`: batch-only; incomplete→400; deadline/not ACTIVE/contest not RUNNING→403; bad score→422.
- `GET`: `prediction_service.visible_predictions`. Visitor without token → 401.

**Admin rounds/matches:** per existing §5 in prior spec + status guards.

**Calculate & leaderboard:**
- `POST /admin/rounds/{id}/calculate` → `scoring_persistence.calculate_round`.
- `GET` leaderboard/results → `LeaderboardService` + tie-break per `leaderboard_tiebreakers.md`.
- `POST /admin/recalculate` — ADMIN; allowed even when FINISHED.

**Caching (§6):**
- Public GET leaderboard/results: `Cache-Control: public, max-age=300, stale-while-revalidate=60` + `ETag`.
- ETag derived from content hash (scores version / max ids) — changes after calculate/VOID.
- Do NOT cache: predictions GET/POST, admin routes, contest-settings PATCH.

## 7. MANDATORY unit tests

**`tests/unit/test_api_unit_1_3.py`:** security, JWT, Pydantic schemas, RoleChecker (unchanged scope).

**`tests/unit/test_contest_lifecycle_1_3.py`:**
- `require_unlocked` when `is_locked` → rejected.
- PATCH settings allowed before lock; blocked after.
- Status transitions: illegal DRAFT→FINISHED; pause/resume/finish happy paths.
- Delete: wrong confirm rejected; grace math with mocked `paused_at`.
- Exceptional tie-break: update points when locked → OK (service-level).

Run: `uv run pytest tests/unit/test_contest_lifecycle_1_3.py tests/unit/test_api_unit_1_3.py -v`

## 8. Acceptance criteria
- App boots; OpenAPI matches `api_v1.yaml`.
- First activate → `is_locked=true` AND `status=RUNNING`.
- PATCH settings when locked → 403; exceptional tie-break when locked → 200.
- Safe delete with `contest_allow_instant_delete=true` in test env works.
- All limits/secrets from config; routers contain no business logic.
- Unit tests pass. HTTP integration is @Tester.

## 9. Explicitly OUT OF SCOPE
Newsletters, BackgroundTasks, participant CRUD, Free Tour.

## 10. Handoff
Append to `agent_docs/progress/stage_1.md`:
```
## YYYY-MM-DD — Coder (1.3)
- STATUS: READY_FOR_TEST
- Files: <paths>
- Verified: app import OK; pytest tests/unit/test_*_1_3.py -> N passed
- Deps added (approved): <list>
```
Report to user in Russian; point to `tester_1.3.md`.
