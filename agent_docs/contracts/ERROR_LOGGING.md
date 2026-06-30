# Errors and Logging

Description of error handling and logging policy in the HTTP API and service layer (Stage 1.5).

## Contents

- [Architecture](#architecture)
- [Client response](#client-response)
- [Error categories](#error-categories)
- [Error codes](#error-codes)
- [Logging](#logging)
- [Administrator alerts](#administrator-alerts)
- [Where to look in the code](#where-to-look-in-the-code)

## Architecture

```
Client → FastAPI → deps (auth/RBAC) → router → service
                              ↓                    ↓
                         HTTPException         AppError
                              ↓                    ↓
                         detail (RU)     error_handlers → JSON {detail, code}
```

| Layer | File | Role |
|-------|------|------|
| Exceptions | `src/core/exceptions.py` | `AppError`, `RecoverableError` hierarchy |
| HTTP mapping | `src/api/error_handlers.py` | Unified handler → JSON |
| Auth/RBAC | `src/api/deps.py` | `HTTPException` without `code` field |
| Services | `src/services/*.py` | Raise `AppError`; no HTTP awareness |
| Logs | `src/core/logging_config.py` | `setup_logging()` at startup |
| Alerts | `src/services/notification_service.py` | `notify_admin()` stub |

Routers **do not** contain `try/except` for domain errors — exceptions bubble up to `error_handlers`.

## Client response

### Domain errors (`AppError`)

```json
{
  "detail": "Дедлайн тура истёк",
  "code": "DEADLINE_PASSED"
}
```

- `detail` — human-readable text in **Russian**
- `code` — stable machine-readable identifier for clients and tests

### Auth / RBAC (`deps.py`)

```json
{ "detail": "Недостаточно прав" }
```

The `code` field is **not** returned — only the `detail` string.

### Pydantic validation

Standard FastAPI **422** response (field list) — no `code` field.

## Error categories

### 1. Contest rule violations (client sees 4xx)

The user or supervisor performed an action that is not allowed under business rules.

Examples:
- prediction after deadline
- rule change when `is_locked`
- round calculation when status is not CLOSED
- contest paused or finished

**Behavior:** HTTP 400/403/409/422 + `detail` + `code`. Logged at **WARNING** (via `app_error_handler`).

### 2. Recoverable internal issues (contest continues)

Data is incomplete or inconsistent but does not block the main flow.

| Location | Issue | Fallback | Log |
|----------|-------|----------|-----|
| `scoring_persistence` | prediction with NULL score | skip row | WARNING |
| `leaderboard_service` | no participant for tiebreak | `0` points | WARNING |
| `handlers/predictions` | missing team name | `str(team_id)` | WARNING |
| `round_auto_close_service` | round already closed | skip | WARNING |

**Behavior:** operation completes successfully; the client **does not** receive an error.

### 3. Critical failures (500)

Cannot continue the operation: unhandled exception, infrastructure failure.

**Behavior:**
- HTTP 500, `detail`: «Внутренняя ошибка сервера», `code`: `INTERNAL_ERROR`
- log at **ERROR**
- call `notify_admin()` (stub — writes to log; email/Telegram later in one place)

## Error codes

| `code` | HTTP | When |
|--------|------|------|
| `NOT_FOUND` | 404 | contest, round, match, team, participant not found |
| `VALIDATION_ERROR` | 400 | incomplete prediction batch, duplicate team, early close |
| `SCORE_OUT_OF_RANGE` | 422 | score outside [0, max_score_value] |
| `CONTEST_RULE_VIOLATION` | 403 | general contest rule violation |
| `DEADLINE_PASSED` | 403 | round deadline expired |
| `CONTEST_NOT_RUNNING` | 403 | contest PAUSED / FINISHED |
| `CONTEST_LOCKED` | 403 | structural changes when `is_locked` |
| `GRACE_PERIOD_ACTIVE` | 400 | deletion before grace period ends after pause |
| `ILLEGAL_TRANSITION` | 409 | invalid status transition |
| `CONTEST_NOT_PAUSED` | 403 | operation requires PAUSED |
| `CONTEST_DELETE_DISABLED` | 403 | deletion disabled in settings |
| `INTERNAL_ERROR` | 500 | unhandled error |

Specific codes (`DEADLINE_PASSED`, `ROUND_NOT_CLOSED`, etc.) inherit the base HTTP status of the parent class.

## Logging

Configured via `config/settings.py` (default `log_level=INFO`). Override with env `LOG_LEVEL`. Full table: [CONFIG.md](CONFIG.md#application-defaults-configsettingspy).

Log line format:

```
2026-06-21 12:00:00 INFO [services.prediction_service] predictions saved user_id=3 round_id=10 count=8
```

Output: **stderr** (console) and, if `LOG_TO_FILE=true`, file **`app.log`**. The file is in `.gitignore`.

### Rotation / archival

Script `src/scripts/archive_logs.py` copies `app.log` to `logs/archive/app-YYYYMMDD-HHMMSS.log` and truncates the active file when:

- size ≥ `LOG_ARCHIVE_MAX_BYTES` (default 5 MiB), **or**
- ≥ `LOG_ARCHIVE_INTERVAL_DAYS` (default 7) have passed since the last archival.

```bash
uv run python src/scripts/archive_logs.py           # by thresholds
uv run python src/scripts/archive_logs.py --force   # now (if log is not empty)
```

Cron is recommended (e.g. once a week). When the API is running, prefer restarting Uvicorn after truncate — see the script docstring.

Future: separate **auth.log** for login audit — see `agent_docs/reports/todo.md`.

| Level | Purpose | Examples |
|-------|---------|----------|
| **ERROR** | requires admin attention | unhandled exception, `CriticalError`, `ADMIN_ALERT` |
| **WARNING** | recoverable | skipped prediction, auto-close skip, boundary 4xx `AppError` |
| **INFO** | key business events | predictions saved, round calculated, pause/resume/finish |
| **DEBUG** | heavy-path debugging | data volumes during scoring, auto-close |

**Not logged:** request bodies, passwords, every successful GET.

## Administrator alerts

```python
# src/services/notification_service.py
await notify_admin("unhandled_exception", detail="...", context={...})
```

Called from `error_handlers` on 500. Real integration (email, Telegram) is wired **only** in this module.

## Where to look in the code

| Task | File |
|------|------|
| Add a new error type | `src/core/exceptions.py` |
| Change JSON response format | `src/api/error_handlers.py` |
| User-facing message | message in `raise` in service (Russian) |
| Add INFO on mutation | corresponding `src/services/*.py` |
| Wire up alert | `src/services/notification_service.py` |

See also: [API_GUIDE.md — Error Response Format](API_GUIDE.md#error-response-format).
