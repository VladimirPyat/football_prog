# Coder Instructions — Stage 1.5: Cleanup (Errors, Logging, Docstrings)

> Status gate: `INSTRUCTIONS_READY`. **Prerequisite:** Stage 1.4 at `TEST_PASS`.
> No new business features. Contracts: `api_v1.yaml` (HTTP status codes unchanged).
> **Language policy:** code comments English; **HTTP `detail` messages Russian** (user-facing);
> **API handler docstrings Russian**; log messages English.

## 1. Objective

Make the Stage 1.4 codebase **readable and maintainable** by introducing:

1. **Russian docstrings** on all public HTTP handlers (what the endpoint does; `Args:` when ≥3 parameters).
2. **Typed exception hierarchy** with centralized HTTP mapping — remove per-router `try/except` + string heuristics.
3. **Three-tier error policy:** contest-rule violations (4xx to client), recoverable internal (fallback + WARNING),
   critical failures (500 + admin alert stub).
4. **Structured logging** (ERROR / WARNING / INFO / DEBUG) with app-level setup.

**Non-goals:** change scoring math (`src/scoring/*`), add email/BackgroundTasks, modify `docs/`,
change OpenAPI paths or RBAC matrix.

## 2. Scope — files you may create/modify

```
src/core/exceptions.py              # NEW — exception hierarchy
src/core/logging_config.py          # NEW — setup_logging()
src/api/error_handlers.py           # NEW — register on FastAPI app
src/api/handlers/                   # NEW (optional DRY) — shared route logic
  __init__.py
  predictions.py                    # GET/POST predictions view builder
  leaderboard.py                    # leaderboard/results GET helpers
src/services/notification_service.py  # NEW — notify_admin() stub
config/settings.py                  # ADD log_level
main.py                             # logging setup + exception handlers
src/api/deps.py                     # Russian docstrings; map decode errors consistently
src/api/v1/*.py                     # docstrings; remove try/except blocks
src/services/contest_lifecycle_service.py  # move exceptions to core; Russian user_message
src/services/prediction_service.py
src/services/round_service.py
src/services/match_service.py
src/services/contest_setup_service.py
src/services/leaderboard_service.py
src/services/scoring_persistence.py
src/services/round_auto_close_service.py
tests/unit/test_exceptions_1_5.py     # NEW — handler mapping unit tests
manuals/API_GUIDE.md                # ADD Error Response Format section
agent_docs/progress/stage_1.md      # append handoff entry (append-only)
```

**Do NOT modify** `src/scoring/*`, `alembic/`, `docs/`, existing test assertions on **status codes**
unless a test explicitly checks English `detail` text (grep and fix only those).

## 3. Exception hierarchy (`src/core/exceptions.py`)

### 3.1 Base class

```python
class AppError(Exception):
    """Domain error mapped to HTTP by error_handlers."""

    http_status: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message  # Russian — returned as JSON "detail"
        if code is not None:
            self.code = code
        super().__init__(message)
```

All subclasses set `http_status`, `code`, and pass a **Russian** `message` at raise site.

### 3.2 HTTP-mapped exceptions (Category 1 — contest rules / client errors)

| Class | `http_status` | `code` | When to raise |
|-------|---------------|--------|---------------|
| `NotFoundError` | 404 | `NOT_FOUND` | Contest, round, match, team, participant, user not found |
| `ValidationError` | 400 | `VALIDATION_ERROR` | Incomplete prediction batch, wrong round status for op, duplicate team name, bad transition input, grace confirm logic |
| `ScoreOutOfRangeError` | 422 | `SCORE_OUT_OF_RANGE` | Score ∉ [0, max_score_value] |
| `ContestRuleError` | 403 | `CONTEST_RULE_VIOLATION` | Deadline passed, round not ACTIVE, results before deadline, contest PAUSED/FINISHED blocking mutation |
| `ContestLockedError` | 403 | `CONTEST_LOCKED` | Structural/rule edit when `is_locked` |
| `GracePeriodError` | 400 | `GRACE_PERIOD_ACTIVE` | Delete before grace elapsed |
| `ContestNotPausedError` | 403 | `CONTEST_NOT_PAUSED` | Op requires PAUSED |
| `ContestDeleteDisabledError` | 403 | `CONTEST_DELETE_DISABLED` | Delete disabled in settings |
| `IllegalTransitionError` | 409 | `ILLEGAL_TRANSITION` | Invalid lifecycle or round status transition |
| `CriticalError` | 500 | `INTERNAL_ERROR` | DB read failure during calculate, unrecoverable scoring load |

**Migrate** the five classes currently defined in `contest_lifecycle_service.py` into `core/exceptions.py`.
Update imports across services and tests. Remove duplicate class definitions from lifecycle service.

**Replace** `PermissionError` and generic `ValueError` in services with the table above.
`ValueError` may remain only for programmer bugs / internal asserts not exposed to HTTP.

### 3.3 Category 2 — recoverable internal (`RecoverableError`)

```python
class RecoverableError(Exception):
    """Non-fatal data issue; caller applies fallback. Never mapped to HTTP directly."""

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(message)
```

Use in services; **catch locally**, log `WARNING`, apply default. Do not propagate to routers.

**Mandatory fallback sites:**

| Location | Condition | Fallback | Log |
|----------|-----------|----------|-----|
| `leaderboard_service` | participant row missing for scored user | `exceptional_tiebreak_points=0` | WARNING |
| `contest_ops` / shared predictions handler | team name not resolved | `str(team_id)` | WARNING (once per request max) |
| `round_auto_close_service` | `close_round` raises (already CLOSED, etc.) | skip round | WARNING |
| `scoring_persistence._collect_round_data` | prediction row with NULL score1/score2 | skip row | WARNING with count |

### 3.4 Category 3 — critical + admin alert

`CriticalError` is raised when calculate/recalculate cannot load required data (contest/round missing
after prior validation, empty DB session errors). **Do not** use for user mistakes.

`notification_service.notify_admin(event, *, detail, context)` — single extension point:

```python
async def notify_admin(event: str, *, detail: str, context: dict | None = None) -> None:
    logger.error("ADMIN_ALERT event=%s detail=%s context=%s", event, detail, context)
```

Called from:
- `error_handlers` unhandled-exception handler
- explicit `CriticalError` handler (before returning 500)

## 4. HTTP error handlers (`src/api/error_handlers.py`)

Register in `main.py` via `register_error_handlers(app)`.

### 4.1 Response shape

```json
{ "detail": "Дедлайн тура истёк", "code": "CONTEST_RULE_VIOLATION" }
```

FastAPI `HTTPException` from `deps.py` (auth/RBAC) stays as-is (`detail` string only) — no `code` required for 401/403 RBAC.

### 4.2 Handlers

| Handler | Catches | Action |
|---------|---------|--------|
| `app_error_handler` | `AppError` | `JSONResponse(status, {"detail": exc.message, "code": exc.code})` |
| `unhandled_exception_handler` | `Exception` (not `HTTPException`, not `AppError`) | log ERROR + `await notify_admin(...)` + 500 generic Russian detail |

Log `WARNING` in `app_error_handler` for 4xx `AppError` (optional, include `code` + path).
Log `ERROR` for `CriticalError` and unhandled.

**Remove** from all routers:
- `except ValueError` / `except PermissionError` / `except ContestLockedError` blocks
- substring heuristics (`"out of range"`, `"deadline"`, `"not found"`)

Routers become thin: call service → `commit` → return. Exceptions propagate to handlers.

### 4.3 `deps.py` adjustments

Keep raising `HTTPException` for auth/RBAC (401/403). Use **Russian** `detail`:

| Situation | Status | `detail` (example) |
|-----------|--------|-------------------|
| Missing bearer | 401 | `Требуется авторизация` |
| Invalid/expired token | 401 | `Недействительный или просроченный токен` |
| User not found | 401 | `Пользователь не найден` |
| Role denied | 403 | `Недостаточно прав` |
| Temp password block | 403 | `Смените временный пароль перед выполнением операции` |
| Contest not found (context) | 404 | `Конкурс не найден` |

Fix: `GET /contests/{contest_id}` must return **404** when contest missing (use `get_contest` → `NotFoundError`, not uncaught `ValueError`).

## 5. Service-layer migration guide

Replace raises using **Russian messages**. Examples:

```python
# prediction_service — was PermissionError
raise ContestRuleError("Дедлайн тура истёк", code="DEADLINE_PASSED")

# prediction_service — was ValueError incomplete batch
raise ValidationError("Укажите прогнозы на все матчи тура")

# match_service — was ValueError out of range
raise ScoreOutOfRangeError(f"Счёт {value} вне диапазона [0, {max_value}]")

# round_service — was ValueError not found
raise NotFoundError(f"Тур {round_id} не найден")

# contest_lifecycle_service — keep semantics, Russian text
raise ContestLockedError("Конкурс заблокирован — изменение правил и структуры запрещено")
```

### 5.1 Files to update (checklist)

- [ ] `contest_lifecycle_service.py` — all raises; import from `core.exceptions`
- [ ] `prediction_service.py` — deadline, ACTIVE, batch coverage, scores
- [ ] `round_service.py` — transitions, deadlines, free tour, close
- [ ] `match_service.py` — result guard, VOID, score range
- [ ] `contest_setup_service.py` — locked, caps, duplicates
- [ ] `contest_teardown.py` — not found
- [ ] `leaderboard_service.py` — status guards, not found; fallback for missing participant
- [ ] `scoring_persistence.py` — not found, wrong status; `CriticalError` if data load fails unexpectedly

**Do not** change function signatures or business rules — only exception types and messages.

## 6. Logging (`src/core/logging_config.py`)

### 6.1 Settings

```python
# config/settings.py
log_level: str = "INFO"  # env LOG_LEVEL
```

### 6.2 Setup

`setup_logging(level: str)` in `logging_config.py`:
- format: `%(asctime)s %(levelname)s [%(name)s] %(message)s`
- call from `main.py` before router mount
- do not reconfigure uvicorn loggers aggressively — use standard propagation

### 6.3 What to log

| Level | Where | Examples |
|-------|-------|----------|
| ERROR | `error_handlers`, `notification_service` | unhandled exception, CriticalError |
| WARNING | fallback sites, `app_error_handler` (4xx) | skipped prediction row, auto-close skip |
| INFO | mutation services | `predictions saved user=%s round=%s count=%s`, `round calculated contest=%s round=%s`, `contest paused id=%s` |
| DEBUG | `scoring_persistence`, `round_auto_close_service` | `scoring round=%s matches=%s predictions=%s participants=%s` |

**Do not** log request bodies or passwords. Do not add DEBUG to every SQL call.

## 7. API docstrings (Russian)

Add docstring to **every** `@router.*` handler in `src/api/v1/*.py` and public deps (`RoleChecker`, `get_contest_context`, `require_not_temp_password`, `resolve_default_contest_id`).

### 7.1 Template

```python
@router.post("/rounds/{round_id}/predictions", ...)
async def post_predictions(...):
    """Сохранить пакет прогнозов пользователя на тур.

    Все матчи тура обязательны. Запрещено после дедлайна или при паузе/завершении конкурса.
    """
```

With ≥3 handler parameters (excluding `Depends`):

```python
    """...

    Args:
        contest_id: идентификатор конкурса
        round_id: идентификатор тура
        body: пакет прогнозов
    """
```

Legacy shims: one line + «Устаревший shim: default contest».

Module-level docstrings (English) may stay.

### 7.2 Coverage list (~55 handlers)

| File | Handlers |
|------|----------|
| `auth.py` | login, change_password, me |
| `contests.py` | list, create, get, patch, pause, resume, finish, delete |
| `contest_teams.py` | get, post, patch, delete |
| `contest_participants.py` | get, post, delete, exceptional_tiebreak |
| `contest_ops.py` | all 16 route handlers (not `_get_contest`) |
| `rounds.py`, `predictions.py`, `admin_*` | all deprecated handlers |
| `main.py` | `health` |
| `deps.py` | 4 public dependencies |

## 8. DRY refactor (recommended, same PR)

Extract duplicated logic into `src/api/handlers/`:

### 8.1 `handlers/predictions.py`

- `build_round_predictions_view(session, contest_id, round_id, user) -> RoundPredictionsView`
- Used by `contest_ops.get_predictions` and `predictions.get_predictions` (legacy)

### 8.2 `handlers/leaderboard.py`

- `get_global_leaderboard_response(session, contest_id) -> LeaderboardOut`
- `get_round_leaderboard_response(session, contest_id, round_id) -> LeaderboardOut`
- `get_round_results_response(session, contest_id, round_id) -> RoundResultsOut`

Legacy `admin_misc.py` calls the same helpers after `resolve_default_contest_id`.

**Goal:** zero copy-paste between `contest_ops.py` and legacy shims for predictions/leaderboard.

Admin round/match legacy routers may keep delegating to services directly (smaller duplication).

## 9. Documentation update

Add section to `manuals/API_GUIDE.md`:

### Error Response Format

- JSON: `detail` (Russian, human-readable) + `code` (machine-readable)
- Table mapping `code` → typical HTTP status
- Note: Pydantic validation still returns 422 with FastAPI default shape
- RBAC/auth errors: `detail` only (no `code`)

Link from Related Documentation table.

## 10. Unit tests (`tests/unit/test_exceptions_1_5.py`)

Minimum cases (use `TestClient` on `main.app` or handler functions directly):

| Test | Assert |
|------|--------|
| `NotFoundError` mapping | 404, `code=NOT_FOUND`, Russian detail |
| `ContestRuleError` / deadline | 403, `code` present |
| `ScoreOutOfRangeError` | 422 |
| `IllegalTransitionError` | 409 |
| `GracePeriodError` | 400 |
| Unhandled exception | 500, `notify_admin` called (mock patch) |
| `GET /contests/99999` | 404 (not 500) |

Run full regression:

```bash
uv run pytest tests/ -v --ignore=tests/manual
```

All existing tests must pass without weakening assertions.

## 11. Russian message catalog (reference)

Use consistent phrasing; adjust grammar but keep meaning:

| `code` | Example `detail` |
|--------|------------------|
| `NOT_FOUND` | `Конкурс не найден` / `Тур не найден` / `Матч не найден` |
| `VALIDATION_ERROR` | `Укажите прогнозы на все матчи тура` |
| `SCORE_OUT_OF_RANGE` | `Счёт 25 вне диапазона [0, 20]` |
| `DEADLINE_PASSED` | `Дедлайн тура истёк` |
| `CONTEST_NOT_RUNNING` | `Конкурс приостановлен — операция недоступна` |
| `CONTEST_LOCKED` | `Конкурс заблокирован — изменение правил и структуры запрещено` |
| `GRACE_PERIOD_ACTIVE` | `Период ожидания после паузы ещё не истёк` |
| `ILLEGAL_TRANSITION` | `Недопустимый переход статуса: RUNNING → DRAFT` |
| `INTERNAL_ERROR` | `Внутренняя ошибка сервера` (generic for unhandled) |

## 12. Acceptance criteria

- [ ] `src/core/exceptions.py` exists; no duplicate exception classes in lifecycle service
- [ ] No `try/except ValueError|PermissionError|ContestLockedError` in `src/api/v1/*.py`
- [ ] No string-heuristic HTTP mapping (`"out of range" in msg`, etc.)
- [ ] All route handlers have Russian docstrings
- [ ] HTTP `detail` for domain errors is Russian; responses include `code` for `AppError`
- [ ] `setup_logging` runs at app start; INFO logs on key mutations
- [ ] `notify_admin` stub exists; called on unhandled 500
- [ ] Recoverable fallbacks implemented at 4 sites (§3.3)
- [ ] `manuals/API_GUIDE.md` updated with error format
- [ ] `tests/unit/test_exceptions_1_5.py` passes
- [ ] Full `pytest tests/` green (excluding manual)
- [ ] OpenAPI `/docs` still loads; no path changes

## 13. Explicitly OUT OF SCOPE

- Email/Telegram notifications (only stub)
- Changing `api_v1.yaml` or adding new endpoints
- Translating log messages or code comments to Russian
- Refactoring `src/scoring/*`
- `tester_1.5.md` (Planner provides separately if needed)

## 14. Implementation order

1. **Infrastructure:** `exceptions.py`, `logging_config.py`, `notification_service.py`, `error_handlers.py`, `main.py`, `settings.py`
2. **Services:** migrate raises + fallbacks + INFO/DEBUG logs
3. **API:** remove try/except, add docstrings, optional `handlers/` DRY
4. **Tests + docs:** `test_exceptions_1_5.py`, `API_GUIDE.md`
5. **Verify:** full pytest

## 15. Handoff

Append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Coder (1.5 cleanup)
- STATUS: READY_FOR_TEST
- Files: src/core/exceptions.py, src/core/logging_config.py, src/api/error_handlers.py, ...
- Verified: pytest tests/ -> N passed; test_exceptions_1_5.py -> M passed
- Notes: HTTP detail Russian; AppError.code in JSON; notify_admin stub at notification_service
```

Report to user in **Russian**. Point to existing 1.4 test suite for regression (no new tester doc required unless Planner adds `tester_1.5.md`).
