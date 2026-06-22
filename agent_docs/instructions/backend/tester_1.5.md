# Tester Instructions — Stage 1.5: Errors, Logging & Cleanup

> Status gate: @Coder `READY_FOR_TEST` for 1.5. **Prerequisite:** Stage 1.4 at `TEST_PASS`.
> Tests/reports English; user verdict Russian. Reference: `instructions/coder_1.5.md`,
> `manuals/API_GUIDE.md` (Error Response Format section).

## 1. Objective

Verify Stage 1.5 **infrastructure cleanup** without re-running the full 1.4 E2E scoring gate:

1. **Error contract** — domain errors return correct HTTP status, Russian `detail`, and machine-readable `code`.
2. **Centralized handlers** — no per-router `try/except` heuristics; known bug `GET /contests/{id}` → 404 (not 500).
3. **Logging policy** — INFO on key mutations, WARNING on recoverable fallbacks, ERROR + `notify_admin` on unhandled 500.
4. **Recoverable fallbacks** — non-fatal data issues do not abort contest flow.
5. **Regression** — core 1.4 scenarios still pass (status codes and business behaviour unchanged).

**Non-goals:** re-verify 90/90 scoring, manual DBeaver scripts, docstring review in CI.

## 2. Scope — files you may create

```
tests/unit/test_exceptions_1_5.py       # NEW — AppError → HTTP mapping, notify_admin
tests/api/test_errors_1_5.py            # NEW — [ERR-*] HTTP error matrix
tests/unit/test_recoverable_1_5.py      # NEW (optional) — fallback + WARNING
agent_docs/reports/test_1.5.md          # NEW — Russian report with [TEST-ID] table
```

You may **extend** `tests/api/conftest.py` with helpers (`assert_error_body`, auth helpers) if needed.

**Do NOT modify** `src/`. Grep/read-only checks on `src/` are allowed for static audit.

## 3. Error response contract

All domain errors (`AppError` subclasses) must return:

```json
{ "detail": "<русский текст>", "code": "<MACHINE_CODE>" }
```

| Layer | Shape | `code` field |
|-------|-------|--------------|
| `AppError` subclasses | `detail` + `code` | required |
| Pydantic / FastAPI validation | FastAPI default 422 | not required |
| RBAC / auth (`deps.py` HTTPException) | `detail` only | not required |

### 3.1 Assertion helper (recommended)

```python
def assert_app_error(resp, *, status: int, code: str, detail_substr: str | None = None) -> dict:
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert "detail" in body
    assert body.get("code") == code, body
    if detail_substr:
        assert detail_substr.lower() in body["detail"].lower()
    return body
```

Use **substring** match on Russian `detail` — exact wording may vary; `code` must be exact.

### 3.2 Expected `code` catalog

| `code` | HTTP | Typical trigger |
|--------|------|-----------------|
| `NOT_FOUND` | 404 | contest / round / match / team missing |
| `VALIDATION_ERROR` | 400 | incomplete prediction batch, duplicate team, early close |
| `SCORE_OUT_OF_RANGE` | 422 | score ∉ [0, max_score_value] |
| `CONTEST_RULE_VIOLATION` | 403 | generic contest rule block |
| `DEADLINE_PASSED` | 403 | prediction after deadline |
| `CONTEST_NOT_RUNNING` | 403 | PAUSED / FINISHED blocks mutation |
| `CONTEST_LOCKED` | 403 | structural edit when `is_locked` |
| `GRACE_PERIOD_ACTIVE` | 400 | delete before grace elapsed |
| `ILLEGAL_TRANSITION` | 409 | invalid lifecycle / round status transition |
| `CONTEST_NOT_PAUSED` | 403 | op requires PAUSED |
| `CONTEST_DELETE_DISABLED` | 403 | delete disabled in settings |
| `INTERNAL_ERROR` | 500 | unhandled / CriticalError |

Coder may use a single `CONTEST_RULE_VIOLATION` or specific codes (`DEADLINE_PASSED`) — tests must match **implemented** codes from `src/core/exceptions.py`.

## 4. Unit tests — exception mapping (`[EXC-*]`)

File: `tests/unit/test_exceptions_1_5.py`

Use `TestClient(main.app)` and/or direct handler tests. Minimum cases:

| ID | Test | Assert |
|----|------|--------|
| `[EXC-404]` | `NotFoundError` via missing contest | 404, `NOT_FOUND`, Russian detail |
| `[EXC-403-RULE]` | `ContestRuleError` / deadline | 403, code present, Russian detail |
| `[EXC-422-SCORE]` | `ScoreOutOfRangeError` | 422, `SCORE_OUT_OF_RANGE` |
| `[EXC-409-TRANS]` | `IllegalTransitionError` | 409, `ILLEGAL_TRANSITION` |
| `[EXC-400-GRACE]` | `GracePeriodError` | 400, `GRACE_PERIOD_ACTIVE` |
| `[EXC-403-LOCK]` | `ContestLockedError` | 403, `CONTEST_LOCKED` |
| `[EXC-400-VAL]` | `ValidationError` | 400, `VALIDATION_ERROR` |
| `[EXC-500-UNHANDLED]` | Unhandled exception (mock service or test route) | 500, generic Russian detail; `notify_admin` called once (patch mock) |
| `[EXC-GET-CONTEST-404]` | `GET /api/v1/contests/99999` as SUPERVISOR | **404 not 500** |

For `[EXC-500-UNHANDLED]`:

```python
with patch("services.notification_service.notify_admin", new_callable=AsyncMock) as mock_notify:
    ...
    mock_notify.assert_awaited_once()
```

## 5. API integration — error matrix (`[ERR-*]`)

File: `tests/api/test_errors_1_5.py`

Use existing fixtures from `tests/api/conftest.py` (`loaded_contest_api`, `empty_contest_db`, etc.).
One test per category — do not duplicate full 1.4 operational suite.

| ID | Scenario | HTTP | Expected `code` |
|----|----------|------|-----------------|
| `[ERR-404-CONTEST]` | `GET /contests/99999` | 404 | `NOT_FOUND` |
| `[ERR-404-ROUND]` | `GET .../rounds/99999/predictions` | 404 | `NOT_FOUND` |
| `[ERR-401-NOAUTH]` | mutating endpoint without token | 401 | no `code` |
| `[ERR-403-RBAC]` | USER calls admin-only endpoint | 403 | no `code` (RBAC) |
| `[ERR-403-PAUSE]` | POST predictions while contest PAUSED | 403 | `CONTEST_NOT_RUNNING` or `CONTEST_RULE_VIOLATION` |
| `[ERR-403-LOCK]` | POST team after first activate | 403 | `CONTEST_LOCKED` |
| `[ERR-400-BATCH]` | partial prediction batch | 400 | `VALIDATION_ERROR` |
| `[ERR-422-PYDANTIC]` | malformed JSON body (missing required field) | 422 | FastAPI default (no `code`) |
| `[ERR-422-SCORE]` | PUT match result score=99 | 422 | `SCORE_OUT_OF_RANGE` |
| `[ERR-400-GRACE]` | DELETE contest without grace (instant=false) | 400 | `GRACE_PERIOD_ACTIVE` |
| `[ERR-409-LIFECYCLE]` | illegal lifecycle transition (if reproducible) | 409 | `ILLEGAL_TRANSITION` |

**Deadline test `[ERR-403-DEADLINE]`** (optional, needs time mock or round with past deadline):
POST predictions after deadline → 403, `DEADLINE_PASSED` or `CONTEST_RULE_VIOLATION`.

## 6. Recoverable fallbacks (`[REC-*]`)

File: `tests/unit/test_recoverable_1_5.py` (optional but recommended)

| ID | Scenario | Assert |
|----|----------|--------|
| `[REC-PRED-NULL]` | prediction row with NULL scores during `_collect_round_data` | calculate succeeds; row skipped; WARNING in `caplog` |
| `[REC-AUTOCLOSE-SKIP]` | auto-close on already CLOSED round | no exception; WARNING in `caplog` |
| `[REC-TIEBREAK-DEFAULT]` | participant missing from join in leaderboard | `exceptional_tiebreak_points=0`; WARNING optional |

Pattern:

```python
def test_recoverable_skips_null_prediction(caplog):
    caplog.set_level(logging.WARNING)
    # ... trigger calculate with fixture data ...
    assert result is not None
    assert any(r.levelname == "WARNING" for r in caplog.records)
```

Do not assert exact log message text — only level and that operation completed.

## 7. Logging smoke (`[LOG-*]`)

| ID | Scenario | Assert |
|----|----------|--------|
| `[LOG-INFO-PRED]` | successful POST predictions | at least one INFO record (e.g. "saved") |
| `[LOG-INFO-CALC]` | successful calculate round | at least one INFO record |
| `[LOG-ERROR-500]` | unhandled exception | ERROR in `caplog` + `notify_admin` mocked |

Use `caplog.set_level(logging.DEBUG)` only when testing DEBUG sites documented in coder_1.5.md
(`scoring_persistence`, `round_auto_close_service`).

## 8. Static audit (read-only, report in test_1.5.md)

Run and record results in the report (PASS = zero matches where noted):

```bash
# No per-router ValueError/PermissionError handlers (should be empty or deps-only)
rg 'except (ValueError|PermissionError|ContestLockedError)' src/api/v1/

# No string-heuristic HTTP mapping
rg 'out of range.*in msg|deadline.*in msg' src/api/

# Exception classes live in core (not duplicated in lifecycle service)
rg 'class ContestLockedError' src/
```

| Check | PASS criterion |
|-------|----------------|
| Router try/except removed | no matches in `src/api/v1/*.py` |
| No substring heuristics | no matches in `src/api/` |
| Single exception home | `ContestLockedError` defined only in `src/core/exceptions.py` |
| `manuals/API_GUIDE.md` | Error Response Format section exists |

Docstrings on handlers: **manual review** in report (sample 3–5 endpoints), not automated.

## 9. Regression — 1.4 smoke (mandatory)

After all 1.5 tests pass, run **1.5 suite + selected 1.4 tests** to confirm business logic intact.
Status codes from 1.4 must remain the same; new `code` field in JSON must not break clients/tests.

### 9.1 Stage 1.5 tests (full)

```bash
uv run pytest tests/unit/test_exceptions_1_5.py -v
uv run pytest tests/api/test_errors_1_5.py -v
uv run pytest tests/unit/test_recoverable_1_5.py -v   # if created
```

Or combined:

```bash
uv run pytest tests/unit/test_exceptions_1_5.py tests/api/test_errors_1_5.py tests/unit/test_recoverable_1_5.py -v
```

### 9.2 Stage 1.4 regression subset (mandatory)

Run these **core 1.4 tests** — they cover SETUP guards, lifecycle, operational guards, and scoring gate:

```bash
uv run pytest \
  tests/api/test_setup_phase_1_4.py \
  tests/api/test_contest_lifecycle_1_4.py \
  tests/api/test_operational_gaps_1_4.py \
  tests/api/test_calculate_leaderboard_1_4.py \
  tests/api/test_multi_contest_1_4.py \
  -v
```

| File | Why included |
|------|----------------|
| `test_setup_phase_1_4.py` | locked contest 403, duplicate team 400 |
| `test_contest_lifecycle_1_4.py` | pause/finish/delete guards |
| `test_operational_gaps_1_4.py` | deadline, result guards, privacy |
| `test_calculate_leaderboard_1_4.py` | **90/90 + 10/10** — proves scoring path not broken |
| `test_multi_contest_1_4.py` | contest isolation |

### 9.3 Integration canary (recommended)

```bash
uv run pytest tests/integration/test_calculate_persistence_1_2.py -v
```

### 9.4 Full regression (optional, before Stage 1 sign-off)

```bash
uv run pytest tests/ -v --ignore=tests/manual
```

Use when time permits or before merging to main.

## 10. Fixtures & setup notes

- Reuse `loaded_contest_api` / `DEFAULT_CONTEST_ID` from `tests/api/conftest.py`.
- For `[ERR-403-LOCK]` and SETUP errors: use `empty_contest_db` or create contest via HTTP then activate.
- For grace-period delete: use `delete_contest_api` fixture pattern from `test_contest_lifecycle_1_4.py`.
- Auth: `api_login`, `auth_header`, `contest_url` helpers.
- If Coder added `handlers/` DRY refactor: predictions/leaderboard legacy + contest-scoped paths should behave identically — spot-check one legacy shim (`POST /rounds/{id}/predictions`) returns same status as contest-scoped path.

## 11. Automated execution & report

```bash
# Primary 1.5 gate
uv run pytest tests/unit/test_exceptions_1_5.py tests/api/test_errors_1_5.py tests/unit/test_recoverable_1_5.py -v

# 1.5 + 1.4 regression subset (required for TEST_PASS)
uv run pytest \
  tests/unit/test_exceptions_1_5.py \
  tests/api/test_errors_1_5.py \
  tests/unit/test_recoverable_1_5.py \
  tests/api/test_setup_phase_1_4.py \
  tests/api/test_contest_lifecycle_1_4.py \
  tests/api/test_operational_gaps_1_4.py \
  tests/api/test_calculate_leaderboard_1_4.py \
  tests/api/test_multi_contest_1_4.py \
  -v
```

- **PASS** → `agent_docs/reports/test_1.5.md` (Russian) with [TEST-ID] table covering
  `[EXC-*]`, `[ERR-*]`, `[REC-*]`, `[LOG-*]`, static audit, 1.4 regression subset;
  append `STATUS: TEST_PASS` to `agent_docs/progress/stage_1.md`.
- **FAIL** → expected vs actual per [TEST-ID]; append `STATUS: TEST_FAIL`. Never edit `src/`.

## 12. Acceptance criteria

- [ ] All `[EXC-*]` unit tests pass
- [ ] All `[ERR-*]` API error matrix tests pass
- [ ] `[EXC-GET-CONTEST-404]` / `[ERR-404-CONTEST]` — 404 not 500
- [ ] `[EXC-500-UNHANDLED]` — `notify_admin` stub invoked
- [ ] At least one `[LOG-INFO-*]` and one `[REC-*]` or documented N/A with reason
- [ ] Static audit checks documented in report
- [ ] `manuals/API_GUIDE.md` Error Response Format section present (Coder deliverable)
- [ ] 1.4 regression subset (§9.2) green — including **90/90** in `test_calculate_leaderboard_1_4.py`
- [ ] No weakening of existing assertions (status codes unchanged)

## 13. Verdict to user (Russian)

Этап 1.5, PASS/FAIL: контракт ошибок (`detail` русский + `code`), централизованные handlers,
логирование (INFO/WARNING/ERROR), fallback без 500, `notify_admin` stub,
регрессия ключевых тестов 1.4 (setup, lifecycle, operational, 90/90 scoring, multi-contest).
Дефекты с [TEST-ID]. Полный 1.4 E2E и manual scripts **не** повторяем, если regression subset зелёный.

## 14. Execution order

1. Confirm Coder 1.5 handoff (`READY_FOR_TEST` in `progress/stage_1.md`).
2. Read `src/core/exceptions.py` for actual `code` strings.
3. Implement and run `[EXC-*]` unit tests.
4. Implement and run `[ERR-*]` API tests.
5. Implement `[REC-*]` / `[LOG-*]` if feasible.
6. Run static audit; sample docstring review.
7. Run **1.5 suite + 1.4 regression subset** (§11).
8. Write `agent_docs/reports/test_1.5.md`; update progress.
