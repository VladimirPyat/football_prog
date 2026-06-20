# Coder Instructions — Stage 1.4: Multi-Contest, Setup Phase & Full Contest Logic

> Status gate: `INSTRUCTIONS_READY`. **Prerequisite:** Stage 1.3 at `TEST_PASS` (minimum
> `READY_FOR_TEST` to start). Builds on 1.3 API, lifecycle, caching. Contracts:
> `api_v1.yaml` (authoritative), `contest_lifecycle_flow.md`, `db_schema.md`,
> `leaderboard_tiebreakers.md`, `bonus_rules.md`. Code/comments English; user report Russian.

## 1. Objective

Replace singleton `contest_settings` with **multi-contest** model; implement **SETUP phase**
(DRAFT CRUD) and full **OPERATIONAL phase** (close/auto-close, result deadline guards,
calculate on CLOSED, Free Tour). Refactor API to **contest-scoped paths**
`/api/v1/contests/{contest_id}/...` with **legacy shims** for 1.3 regression tests on loader data.

## 2. Scope — files you may create/modify

```
src/database/models.py
alembic/versions/<rev>_multi_contest_and_participants.py
src/services/contest_setup_service.py          # NEW — create contest, teams, participants, invites
src/services/contest_lifecycle_service.py      # REFACTOR — per contest_id
src/services/contest_teardown.py               # REFACTOR — wipe one contest
src/services/round_auto_close_service.py       # NEW — sync auto-close hook
src/services/round_service.py                  # EXTEND — close_round, free_tour; contest_id
src/services/match_service.py                  # EXTEND — result deadline guard
src/services/prediction_service.py             # REFACTOR — contest filter
src/services/scoring_persistence.py            # REFACTOR — contest filter
src/services/leaderboard_service.py            # REFACTOR — exceptional points from contest_participants
src/scripts/load_test_data.py                  # EXTEND — contest_id=1 seed
src/scripts/seed.py                            # EXTEND if used
src/api/deps.py                                # EXTEND — get_contest, auto_close hook, default contest shim
src/api/v1/contests.py                         # NEW — contest CRUD
src/api/v1/contest_teams.py                    # NEW
src/api/v1/contest_participants.py             # NEW
src/api/v1/{auth,rounds,predictions,admin_*}.py  # REFACTOR — mount under contest router OR shared handlers
src/schemas/{contest,admin,rounds,predictions,leaderboard}.py  # EXTEND
main.py                                        # Router registration
config/settings.py                             # optional: default_contest resolution flags
tests/unit/test_contest_setup_1_4.py           # NEW
tests/unit/test_multi_contest_1_4.py           # NEW
tests/unit/test_contest_lifecycle_1_3.py       # EXTEND — contest_id param
tests/unit/test_round_auto_close_1_4.py        # NEW
agent_docs/contracts/db_schema.md              # sync after migration
```

**Do NOT modify** `src/scoring/*` engine math. **Do NOT** implement newsletters/BackgroundTasks.

## 3. Migration spec (`1.4_multi_contest`)

### 3.1 Create `contests` (replaces `contest_settings`)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `name` | VARCHAR NOT NULL | |
| `slug` | VARCHAR UNIQUE NULL | optional |
| `is_locked` | BOOLEAN NOT NULL DEFAULT FALSE | |
| `status` | VARCHAR NOT NULL DEFAULT 'DRAFT' | CHECK enum |
| `paused_at`, `finished_at` | TIMESTAMPTZ NULL | |
| `total_teams`, `matches_per_round`, `total_rounds` | INTEGER NOT NULL | |
| `is_round_robin` | BOOLEAN NOT NULL | |
| `rules_json` | JSONB NOT NULL | from `contest_defaults.json` shape |

### 3.2 Create `contest_participants`

| Column | Type | Notes |
|--------|------|-------|
| `contest_id` | FK contests ON DELETE CASCADE | |
| `user_id` | FK users | |
| `status` | VARCHAR NOT NULL DEFAULT 'ACCEPTED' | `PENDING`, `ACCEPTED` |
| `exceptional_tiebreak_points` | INTEGER NOT NULL DEFAULT 0 | CHECK >= 0 |
| PK | `(contest_id, user_id)` | |

### 3.3 Add FKs

- `teams.contest_id` NOT NULL FK → contests; drop global UNIQUE on `name`; add UNIQUE `(contest_id, name)`.
- `rounds.contest_id` NOT NULL FK → contests; drop global UNIQUE on `number`; add UNIQUE `(contest_id, number)`.

### 3.4 Backfill & drop

1. INSERT `contests` FROM `contest_settings` (id=1, name='Default').
2. UPDATE all teams/rounds SET contest_id=1.
3. INSERT `contest_participants` for each user in DB (or each user with predictions):
   copy `users.exceptional_tiebreak_points`.
4. DROP `contest_settings`; DROP COLUMN `users.exceptional_tiebreak_points`.
5. Backfill status: `UPDATE contests SET status='RUNNING' WHERE is_locked=TRUE` (same as 1.2.1).

### 3.5 Model changes

- Rename/replace `ContestSettings` → `Contest` model (`contests` table).
- Add `ContestParticipant` model.
- Add relationships on `Team`, `Round`.

Run: `uv run alembic upgrade head`; existing `tests/integration/` must stay green after loader update.

## 4. Service layer

### 4.1 `contest_setup_service.py`

Functions (all take `contest_id` or create and return id):

- `create_contest(session, name, rules_from_defaults=True)` → DRAFT contest.
- `update_contest(session, contest_id, patch)` → calls `require_unlocked(contest_id)`.
- `create_team / update_team / delete_team` — only when `!is_locked`; validate `total_teams` cap on create.
- `add_participant(session, contest_id, email, first_name, last_name)` → create User+Contact if needed,
  `contest_participants` row `PENDING`, generate temp password (bcrypt), return `{user_id, temp_password}`.
- `remove_participant` — only when `!is_locked`; do not delete global user if enrolled in other contests.
- `list_participants`, `list_teams`.

Invite flow per `docs/04_supervisor_scenario.md` §2: temp password; `is_temp_password=true`.
**No email send** (out of scope) — return temp password in API response for tests.

### 4.2 `contest_lifecycle_service.py` refactor

All functions accept `contest_id: int`. Replace `get_contest_settings` → `get_contest(session, contest_id)`.
Delete/teardown scoped to one contest. `reseed` not global — either delete row or reset to DRAFT empty contest.

### 4.3 `round_auto_close_service.py`

```python
async def auto_close_expired_rounds(session, contest_id: int) -> list[int]:
    """ACTIVE rounds with deadline <= now(UTC) → CLOSED. Returns closed round ids."""
```

Call from `deps.get_contest_context` (or equivalent) **before** handler body on all
`/contests/{contest_id}/...` routes.

### 4.4 `round_service.py` extensions

- All helpers resolve contest via `round.contest_id`.
- `close_round(session, contest_id, round_id)` — ACTIVE → CLOSED if `now >= deadline`.
- `create_free_tour(session, contest_id, matches: list[{match_id, new_date_time}], deadline)`:
  - Validate each match POSTPONED and belongs to contest.
  - New round number = max+1; move matches; update `matches_count` on source rounds.
  - Return new round (DRAFT).

- `transition_round`: lock **`contests`** row for that round's contest on first ACTIVE.

### 4.5 `match_service.py` — result guard

In `set_result`, before applying scores:

```python
now = datetime.now(timezone.utc)
round_ = await session.get(Round, match.round_id)
assert round_.contest_id == contest_id  # from caller
if now < round_.deadline:
    raise ValueError("Results allowed only after round deadline")
if RoundStatus(round_.status) not in {RoundStatus.CLOSED, ...}:  # must be CLOSED
    raise ValueError("Round must be CLOSED before entering results")
await assert_contest_running(session, contest_id)
```

Map to HTTP 403 in router.

### 4.6 `leaderboard_service.py`

Load `exceptional_tiebreak_points` from `contest_participants` WHERE `contest_id` matches round's contest.
Remove reads from `users.exceptional_tiebreak_points`.

## 5. API — contest-scoped paths (wire per `api_v1.yaml`)

Prefix: `/api/v1/contests/{contest_id}`

### 5.1 Contest & setup (SETUP phase guards)

| Method | Path | Role | Notes |
|--------|------|------|-------|
| POST | `/contests` | SUPERVISOR+ | Create DRAFT contest |
| GET | `/contests` | SUPERVISOR+ | List contests |
| GET | `/contests/{id}` | SUPERVISOR+ | Detail |
| PATCH | `/contests/{id}` | SUPERVISOR+ | `require_unlocked` |
| GET/POST/PATCH/DELETE | `.../teams`, `.../teams/{id}` | SUPERVISOR+ | CRUD when unlocked |
| GET/POST/DELETE | `.../participants`, `.../participants/{user_id}` | SUPERVISOR+ | CRUD when unlocked |
| PUT | `.../participants/{user_id}/exceptional-tiebreak` | ADMIN | **Allowed when locked** |

### 5.2 Lifecycle (unchanged semantics, contest-scoped)

`POST .../pause`, `.../resume`, `.../finish`, `DELETE .../` with confirm body.

### 5.3 Operational

| Method | Path | Notes |
|--------|------|-------|
| GET | `.../rounds` | Public list |
| POST | `.../admin/rounds` | Create round |
| PATCH | `.../admin/rounds/{id}` | Edit ACTIVE |
| POST | `.../admin/rounds/{id}/activate` | + `ensure_running_on_first_activation` |
| POST | `.../admin/rounds/{id}/close` | **NEW** ACTIVE→CLOSED |
| POST | `.../admin/rounds/{id}/calculate` | CLOSED only |
| POST | `.../admin/rounds/{id}/publish` | |
| POST | `.../admin/rounds/free-tour` | **NEW** Free Tour |
| PUT | `.../admin/matches/{id}/result` | After deadline + CLOSED |
| PATCH | `.../admin/matches/{id}/status` | VOID/etc. |
| GET/POST | `.../rounds/{id}/predictions` | |
| GET | `.../rounds/{id}/leaderboard`, `.../results`, `.../leaderboard` (global) | Cache headers unchanged |
| POST | `.../admin/recalculate` | ADMIN |

### 5.4 Legacy shims (deprecated)

Mount existing 1.3 routers at old paths; internally resolve `default_contest_id` via
`deps.resolve_default_contest(session)` and delegate to contest-scoped handlers.
Document in OpenAPI `deprecated: true`.

Auth routes stay global: `/api/v1/auth/*`.

## 6. RBAC & guards (unchanged + extended)

- PAUSED/FINISHED → block mutating round/match/prediction (403).
- SETUP locked operations → 403 ContestLocked.
- Temp password restriction unchanged.
- Public GET leaderboard/results per contest.

## 7. MANDATORY unit tests

**`tests/unit/test_contest_setup_1_4.py`:**
- Create contest DRAFT; PATCH rules; create 16 teams; add 10 participants.
- PATCH/team CRUD blocked after first activate (`is_locked`).
- Participant invite sets temp password.

**`tests/unit/test_round_auto_close_1_4.py`:**
- ACTIVE round past deadline → auto_close → CLOSED.
- Result before deadline → rejected; after auto-close → OK.

**`tests/unit/test_multi_contest_1_4.py`:**
- Two contests isolated: teams/rounds do not cross-contaminate.
- Same global user in two contests with different exceptional tie-break points.

**Extend `test_contest_lifecycle_1_3.py`:** pass `contest_id=1`.

Run:
```
uv run pytest tests/unit/test_*_1_4.py tests/unit/test_contest_lifecycle_1_3.py tests/unit/test_api_unit_1_3.py -v
```

## 8. Acceptance criteria

- App boots; OpenAPI matches `api_v1.yaml` contest paths.
- Migration backfills loader DB; `tests/integration/` still pass.
- Multi-contest: second contest creatable in DRAFT while first RUNNING.
- Auto-close on API call transitions expired ACTIVE rounds.
- `POST close` and result guard enforce deadline.
- Free tour moves POSTPONED matches to new round.
- Exceptional tie-break on `contest_participants`; works when locked.
- Legacy shims resolve contest id=1 for loader regression.
- Unit tests pass.

## 9. Explicitly OUT OF SCOPE

Newsletters, email BackgroundTasks, Playwright E2E, frontend.

## 10. Handoff

Append to `agent_docs/progress/stage_1.md`:
```
## YYYY-MM-DD — Coder (1.4)
- STATUS: READY_FOR_TEST
- Files: <paths>
- Verified: alembic upgrade head; pytest tests/unit/test_*_1_4.py -> N passed; tests/integration/ green
- Migration: <rev>_multi_contest_and_participants
```
Report to user in Russian; point to `tester_1.4.md`.
