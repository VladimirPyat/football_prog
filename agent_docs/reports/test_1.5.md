# Отчёт тестирования — Этап 1.5 (Errors, Logging & Cleanup)

**Дата:** 2026-06-21  
**Вердикт:** TEST_PASS  
**Исполнитель:** @Tester

## Резюме

Реализован и пройден полный набор тестов Stage 1.5: контракт ошибок (`detail` на русском + `code`), централизованные handlers, логирование INFO/WARNING/ERROR, recoverable fallbacks, `notify_admin` на 500. Регрессия ключевых тестов 1.4 зелёная (60 passed, 1 skipped), включая **90/90** и **10/10** scoring gate.

## Таблица [TEST-ID]

| ID | Категория | Файл | Результат |
|----|-----------|------|-----------|
| [EXC-META] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-HANDLER] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-404] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-403-RULE] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-422-SCORE] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-409-TRANS] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-400-GRACE] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-403-LOCK] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-400-VAL] | Unit | `test_exceptions_1_5.py` | PASS |
| [EXC-500-UNHANDLED] | Unit | `test_exceptions_1_5.py` | PASS (`notify_admin` + ERROR log) |
| [EXC-GET-CONTEST-404] | Unit/API | `test_exceptions_1_5.py` | PASS (404, не 500) |
| [ERR-404-CONTEST] | API | `test_errors_1_5.py` | PASS |
| [ERR-404-ROUND] | API | `test_errors_1_5.py` | PASS |
| [ERR-401-NOAUTH] | API | `test_errors_1_5.py` | PASS |
| [ERR-403-RBAC] | API | `test_errors_1_5.py` | PASS (403, без `code`) |
| [ERR-403-PAUSE] | API | `test_errors_1_5.py` | PASS |
| [ERR-403-LOCK] | API | `test_errors_1_5.py` | PASS (`CONTEST_LOCKED`) |
| [ERR-400-BATCH] | API | `test_errors_1_5.py` | PASS |
| [ERR-422-PYDANTIC] | API | `test_errors_1_5.py` | PASS |
| [ERR-422-SCORE] | API | `test_errors_1_5.py` | PASS (`SCORE_OUT_OF_RANGE`) |
| [ERR-400-GRACE] | API | `test_errors_1_5.py` | PASS |
| [ERR-409-LIFECYCLE] | API | `test_errors_1_5.py` | PASS (`ILLEGAL_TRANSITION`) |
| [REC-PRED-NULL] | Unit | `test_recoverable_1_5.py` | PASS (WARNING + skip) |
| [REC-AUTOCLOSE-SKIP] | Unit | `test_recoverable_1_5.py` | PASS (без исключения; WARNING не ожидается для CLOSED) |
| [REC-TIEBREAK-DEFAULT] | Unit | `test_recoverable_1_5.py` | PASS (`0` + WARNING) |
| [REC-SMOKE] | Unit | `test_recoverable_1_5.py` | PASS |
| [LOG-INFO-PRED] | API | `test_errors_1_5.py` | PASS |
| [LOG-INFO-CALC] | API | `test_errors_1_5.py` | PASS |
| [LOG-ERROR-500] | Unit | `test_exceptions_1_5.py` | PASS (в составе [EXC-500-UNHANDLED]) |

## Статический аудит (read-only)

| Проверка | Команда | Результат |
|----------|---------|-----------|
| Нет per-router `try/except` эвристик | `rg 'except (ValueError\|PermissionError\|ContestLockedError)' src/api/v1/` | **PASS** — 0 совпадений |
| Нет substring HTTP mapping | `rg 'out of range.*in msg\|deadline.*in msg' src/api/` | **PASS** — 0 совпадений |
| Единый дом для `ContestLockedError` | `rg 'class ContestLockedError' src/` | **PASS** — только `src/core/exceptions.py` |
| `manuals/API_GUIDE.md` Error Response Format | ручная проверка §324 | **PASS** — секция присутствует |

### Выборочный обзор docstrings (ручной)

Проверены эндпоинты в `src/api/v1/contests.py`: `list_contests`, `create_contest`, `get_contest`, `update_contest`, `pause`, `resume`, `finish`, `delete_contest` — docstrings на русском, краткие, соответствуют бизнес-операциям. Handlers в `src/api/handlers/` — английские module docstrings (внутренние), публичные роуты документированы в v1.

## Выполненные команды

```bash
# Stage 1.5 suite
uv run pytest tests/unit/test_exceptions_1_5.py tests/api/test_errors_1_5.py tests/unit/test_recoverable_1_5.py -v
# → 28 passed in 41.75s

# Stage 1.5 + 1.4 regression subset
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
# → 60 passed, 1 skipped in 135.43s
```

Ключевые регрессионные кейсы 1.4: `[API-RESULTS] 90/90`, `[API-LB-GLOBAL] 10/10` — PASS.

## Изменённые тестовые файлы

- `tests/unit/test_exceptions_1_5.py` — дополнены все [EXC-*] кейсы + [LOG-ERROR-500]
- `tests/api/test_errors_1_5.py` — добавлены [ERR-403-RBAC], [ERR-403-LOCK], [ERR-422-SCORE], [ERR-409-LIFECYCLE], [LOG-INFO-*]
- `tests/unit/test_recoverable_1_5.py` — реальные [REC-*] тесты с `caplog`

## Дефекты

Не обнаружены.

## Примечания

- `[REC-AUTOCLOSE-SKIP]`: `auto_close_expired_rounds` обрабатывает только ACTIVE туры; уже CLOSED туры пропускаются без WARNING (корректное поведение). WARNING логируется при сбое `close_round`/`transition_round` внутри auto-close — отдельный сценарий не воспроизводился без моков.
- `[ERR-403-DEADLINE]` — опциональный, не реализован (требует time mock; round 10 в fixture сдвинут вперёд).

## Следующий шаг

Этап 1.5 готов к sign-off. Stage 1 sign-off или merge после полного `pytest tests/ --ignore=tests/manual` по желанию.
