# Отчёт тестирования — Stage 1.4 + 1.4.1

**Дата:** 2026-06-21  
**Статус:** TEST_FAIL (1 дефект блокирует полный PASS)  
**Coder:** READY_FOR_TEST подтверждён; `src/` не изменялся.

## Сводка выполнения

| Набор | Результат |
|-------|-----------|
| `tests/api/` | **79 passed**, **1 failed**, 2 skipped (~265 s) |
| `tests/integration/` | **36 passed** (~5.5 s) |
| **Итого** | **117 passed**, **1 failed**, 2 skipped |

Ключевые gates:
- **[API-RESULTS] 90/90** — PASS (`test_api_results_90_of_90`)
- **[API-LB-GLOBAL] 10/10** — PASS (`test_api_lb_global_10_of_10`)
- **[CALC-ROUND] 90/90** (regression) — PASS
- **[CANARY-PYTEST-*]** — PASS

## Таблица TEST-ID

| TEST-ID | Файл | Статус |
|---------|------|--------|
| [SETUP-CREATE] | test_setup_phase_1_4.py | PASS |
| [SETUP-PATCH] | test_setup_phase_1_4.py | PASS |
| [SETUP-TEAMS] | test_setup_phase_1_4.py | PASS |
| [SETUP-TEAMS-LOCK] | test_setup_phase_1_4.py | PASS |
| [SETUP-PART] | test_setup_phase_1_4.py | PASS |
| [SETUP-PART-LOCK] | test_setup_phase_1_4.py | PASS |
| [SETUP-LIST] | test_setup_phase_1_4.py | PASS |
| [SETUP-PART-AUTH] | test_operational_gaps_1_4.py | PASS |
| [OP-ACTIVATE] | test_operational_phase_1_4.py | PASS |
| [OP-PRED] | test_operational_phase_1_4.py | PASS |
| [OP-PRED-DEADLINE] | test_operational_phase_1_4.py | PASS |
| [OP-AUTOCLOSE] | test_operational_phase_1_4.py | PASS * |
| [OP-CLOSE] | test_operational_phase_1_4.py | **FAIL** |
| [OP-CLOSE-EARLY] | test_operational_phase_1_4.py | PASS |
| [OP-RESULT-GUARD] | test_operational_phase_1_4.py | PASS |
| [OP-RESULT-OK] | test_operational_phase_1_4.py | PASS |
| [OP-CALC] | test_operational_phase_1_4.py | PASS |
| [OP-CALC-ACTIVE] | test_operational_phase_1_4.py | PASS |
| [OP-PUBLISH] | test_operational_phase_1_4.py | PASS |
| [OP-VOID] | test_operational_phase_1_4.py | PASS |
| [OP-PAUSE] | test_operational_phase_1_4.py | PASS |
| [OP-FREE-TOUR] | test_free_tour_1_4.py | PASS |
| [OP-PRED-PRIVACY] | test_operational_gaps_1_4.py | PASS |
| [OP-24H-RULE] | test_operational_gaps_1_4.py | PASS |
| [OP-ROUND-EDIT] | test_operational_gaps_1_4.py | PASS |
| [OP-ROUND-CREATE] | test_operational_gaps_1_4.py | PASS |
| [OP-ROUNDS-LIST] | test_operational_gaps_1_4.py | PASS |
| [OP-RECALC] | test_operational_gaps_1_4.py | PASS |
| [MULTI-ISOLATE] | test_multi_contest_1_4.py | PASS |
| [MULTI-RUNNING] | test_multi_contest_1_4.py | PASS |
| [MULTI-TIEBREAK] | test_multi_contest_1_4.py | PASS |
| [API-CALC] | test_calculate_leaderboard_1_4.py | PASS |
| [API-RESULTS] | test_calculate_leaderboard_1_4.py | PASS |
| [API-LB-GLOBAL] | test_calculate_leaderboard_1_4.py | PASS |
| [API-VOID] | test_calculate_leaderboard_1_4.py | PASS |
| [API-CACHE] | test_calculate_leaderboard_1_4.py | PASS |
| [API-CACHE-ETAG] | test_calculate_leaderboard_1_4.py | PASS |
| [API-TB-SET] | test_calculate_leaderboard_1_4.py | PASS |
| [API-TB-RANK] | test_calculate_leaderboard_1_4.py | SKIP |
| [API-TB-RBAC] | test_calculate_leaderboard_1_4.py | PASS |
| [API-CONTEST-FINISH] | test_contest_lifecycle_1_4.py | PASS |
| [API-CONTEST-FINISH-IDEM] | test_contest_lifecycle_1_4.py | PASS |
| [API-CONTEST-PAUSE-BLOCK] | test_contest_lifecycle_1_4.py | PASS |
| [API-CONTEST-DELETE-RBAC] | test_contest_lifecycle_1_4.py | PASS |
| [API-CONTEST-DELETE-NOGRACE] | test_contest_lifecycle_1_4.py | PASS |
| [API-CONTEST-DELETE-BADCONFIRM] | test_contest_lifecycle_1_4.py | PASS |
| [API-CONTEST-DELETE-OK] | test_contest_lifecycle_1_4.py | PASS |
| [CANARY-PYTEST-ORACLE] | test_canary_scoring_1_4.py | PASS |
| [CANARY-PYTEST-REVERT] | test_canary_scoring_1_4.py | PASS |

\* [OP-AUTOCLOSE]: auto-close срабатывает в `ContestContext`, но персистится только при последующем committing-запросе (тест использует `calculate` round 1). Отдельный GET без commit не сохраняет CLOSED — см. рекомендации @Coder.

## Дефекты

### [OP-CLOSE] — POST `.../admin/rounds/{id}/close` после deadline не переводит раунд в CLOSED

**Файл:** `tests/api/test_operational_phase_1_4.py::test_op_close_after_deadline`

**Ожидание:** ACTIVE + `deadline <= now` → `POST .../close` → 200, status `CLOSED` в БД.

**Факт:** HTTP 400 `"Round 10 must be ACTIVE to close (got CLOSED)"`; в БД раунд остаётся `ACTIVE` (rollback сессии).

**Причина (анализ):** В `src/api/deps.py` `get_contest_context` вызывает `auto_close_expired_rounds` до handler. При прошедшем deadline auto-close переводит раунд в CLOSED **в сессии**, затем `close_round` в handler требует `ACTIVE` → `ValueError` → 400 **без `commit`**, изменения auto-close откатываются.

**Рекомендации @Coder (любой из вариантов):**
1. После `auto_close_expired_rounds` в `get_contest_context` делать `await session.commit()` если `closed_ids` не пуст.
2. Сделать `close_round` идемпотентным для уже `CLOSED` (вернуть 200).
3. На endpoint `close` не вызывать auto-close до явного close, или вызывать close до auto-close.

**Затронутые файлы:** `src/api/deps.py`, `src/services/round_service.py`, `src/api/v1/contest_ops.py`.

## Canary verification

- Manual Script 1: `verify_via_api.py --bootstrap load` → exit 0 (`OK contest_id=1`).
- Manual Script 2: `compare_db_vs_reference.py` → exit 0 (`scores=90/90 leaderboard=10/10`).
- Manual CANARY: temp copy `expected_scores.csv` с `expected_total=99999` → Script 2 exit 1 с `volchenko/round 1: total: got 28, want 99999`.

## Out of scope (зафиксировано)

Newsletters, contacts/profile, Playwright E2E, audit log — вне Stage 1 API (`tester_1.4.1.md` §7).

## Артефакты

| Путь | Назначение |
|------|------------|
| `tests/api/conftest.py` | `empty_api`, `contest_url`, `get_contest_id`, `build_contracted_contest_via_http` |
| `tests/api/reference_compare.py` | Shared CSV ↔ DB compare |
| `tests/manual/verify_via_api.py` | Script 1 |
| `tests/manual/compare_db_vs_reference.py` | Script 2 |
| `manuals/MANUAL_SCORING_VERIFICATION.md` | RU sign-off guide |

## Команды

```bash
uv run pytest tests/api/ -v          # 79 passed, 1 failed, 2 skipped
uv run pytest tests/integration/ -v  # 36 passed
```

## Следующий шаг

@Coder исправляет **[OP-CLOSE]** (и желательно commit auto-close в `get_contest_context` для read-only GET). @Tester перезапускает `tests/api/` → ожидается TEST_PASS.
