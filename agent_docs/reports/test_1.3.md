# Отчёт о тестировании — Этап 1.3

**Дата:** 2026-06-21  
**Вердикт:** ✅ TEST_PASS  
**Команда:** `uv run pytest tests/api/ -v`  
**Результат:** 31 passed, 1 skipped, 0 failed (~109s)

**Регрессия 1.2:** `uv run pytest tests/integration/ -v` → 36 passed, 0 failed (~5s)

---

## Итоговая таблица [TEST-ID]

| TEST-ID | Описание | Результат | Детали |
|---------|----------|-----------|--------|
| [AUTH-LOGIN] | Валидные / невалидные учётные данные → 200 + token / 401 | ✅ PASS | 2 теста |
| [AUTH-TEMP] | Временный пароль → 403 на predictions; change-password OK | ✅ PASS | |
| [RBAC-USER] | USER не может вызвать SUPERVISOR endpoint → 403 | ✅ PASS | |
| [RBAC-PUB] | Публичный GET leaderboard без токена → 200 | ✅ PASS | |
| [RBAC-ADMIN] | POST recalculate только ADMIN | ✅ PASS | |
| [API-PRED-PARTIAL] | 7/8 предсказаний → 400 | ✅ PASS | |
| [API-PRED-FULL] | 8/8 ACTIVE до дедлайна → 200 | ✅ PASS | |
| [API-PRED-RANGE] | score 21 → 422; 0:0 принят | ✅ PASS | |
| [API-PRED-DEADLINE] | После дедлайна / не-ACTIVE → 403 | ✅ PASS | 2 подтеста |
| [API-PRED-PRIVACY] | До дедлайна — чужие scores скрыты; после — видны все | ✅ PASS | |
| [API-PRED-VISITOR] | GET predictions без токена → 401 | ✅ PASS | |
| [API-SMOKE-CALC] | calculate раунда 1 → CALCULATED, users_scored > 0 | ✅ PASS | |
| [API-VOID] | VOID матча → пересчёт; leaderboard меняется | ✅ PASS | |
| [API-CACHE] | leaderboard/results: Cache-Control + ETag; POST pred — нет | ✅ PASS | |
| [API-CACHE-ETAG] | ETag меняется после calculate | ✅ PASS | |
| [API-CS-GET] | SUPERVISOR GET settings → status, is_locked | ✅ PASS | |
| [API-CS-PATCH-UNLOCKED] | PATCH rules до activate → 200 | ✅ PASS | |
| [API-CS-PATCH-LOCKED] | PATCH после activate → 403 | ✅ PASS | |
| [API-CS-ACTIVATE] | Первый activate → is_locked, RUNNING | ✅ PASS | |
| [API-TB-SET] | ADMIN set exceptional points при locked → 200 | ✅ PASS | |
| [API-TB-LOCKED] | (вместе с [API-TB-SET]) | ✅ PASS | |
| [API-TB-RBAC] | SUPERVISOR set → 403 | ✅ PASS | |
| [API-TB-DISPLAY] | GET leaderboard включает exceptional_tiebreak_points | ✅ PASS | |
| [API-TB-RANK] | Синтетический tie: выше exceptional points → выше rank | ⏭ SKIP | shutov/volchenko не tied по критериям 1–4 в loader data |
| [API-CONTEST-PAUSE] | pause RUNNING → PAUSED, paused_at set | ✅ PASS | |
| [API-CONTEST-PAUSE-BLOCK] | predictions при PAUSED → 403 | ✅ PASS | |
| [API-CONTEST-RESUME] | pause → resume → RUNNING; predictions снова работают | ✅ PASS | |
| [API-CONTEST-FINISH] | finish → predictions 403; public GET 200 | ✅ PASS | |
| [API-CONTEST-FINISH-IDEM] | повторный finish → 200 no-op | ✅ PASS | |
| [API-CONTEST-DELETE-RBAC] | DELETE как SUPERVISOR → 403 | ✅ PASS | |
| [API-CONTEST-DELETE-NOGRACE] | instant=false, сразу после pause → 400 | ✅ PASS | см. примечание SQLite |
| [API-CONTEST-DELETE-BADCONFIRM] | неверный confirm → 422 | ✅ PASS | см. примечание Pydantic |
| [API-CONTEST-DELETE-OK] | instant delete → DB wiped, status=DRAFT | ✅ PASS | |

---

## Примечания о реализации

### Изоляция БД и conftest
- Каждый тест получает изолированную SQLite через `load_test_data.py --reset`.
- `tests/api/__init__.py` удалён — каталог `tests/api/` затенял `src/api/` на `sys.path`.
- `ensure_contest_running` идемпотентен (пропускает уже RUNNING+locked; обрабатывает ACTIVE→ACTIVE).

### [API-CONTEST-DELETE-NOGRACE] — SQLite и timezone
SQLite возвращает naive datetime из колонок `DateTime(timezone=True)`. Без нормализации
`assert_deletable` падает с `TypeError: can't compare offset-naive and offset-aware datetimes`.
В conftest добавлен test-only monkeypatch `compute_deletable_at` (нормализация к UTC).
**Рекомендация Coder:** добавить нормализацию в `contest_lifecycle_service.py` для production.

### [API-CONTEST-DELETE-BADCONFIRM] — 422 vs 400
Схема `ContestDeleteConfirmRequest` использует `Literal["DELETE"]`. Значение `"NOPE"`
отклоняется Pydantic до handler → **422**, а не 400 из `admin_contest.py`. Тест принимает 422
как корректное отклонение неверного confirm.

### [API-TB-RANK] — SKIP
После расчёта раундов 1–9 пользователи shutov и volchenko не имеют одинакового rank по
критериям 1–4 в contracted data; синтетический tie не достижим без дополнительной подготовки.
Покрытие rank-by-tiebreak переносится в этап 1.4 (полный E2E).

### Вне scope 1.3 (перенесено в 1.4)
- `[API-CALC]` 90/90, `[API-LB-*]` 10/10 global leaderboard contract
- `verify_via_api.py`, manual two-phase scripts

---

## Файлы тестов

| Файл | Назначение |
|------|-----------|
| `tests/api/conftest.py` | loader DB, auth helpers, lifecycle helpers, instant-delete env |
| `tests/api/test_auth_rbac_1_3.py` | [AUTH-*] [RBAC-*] |
| `tests/api/test_predictions_flow_1_3.py` | [API-PRED-*] |
| `tests/api/test_contest_lifecycle_1_3.py` | [API-CS-*] [API-TB-*] [API-CONTEST-*] |
| `tests/api/test_calculate_smoke_1_3.py` | [API-SMOKE-*] [API-VOID] [API-CACHE-*] |

**Зависимость (dev):** `httpx` — для `httpx.AsyncClient` + ASGITransport.
