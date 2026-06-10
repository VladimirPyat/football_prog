# Отчёт о тестировании — Этап 1.2

**Дата:** 2026-06-11  
**Вердикт:** ✅ TEST_PASS  
**Команда:** `uv run pytest tests/integration/ -v`  
**Результат:** 36 passed, 0 failed, 0 errors (5.27s)

---

## Итоговая таблица [TEST-ID]

| TEST-ID | Описание | Результат | Детали |
|---------|----------|-----------|--------|
| [LD-COUNT] | 16 команд, 10 пользователей, 10 раундов, 72 FINISHED + 8 SCHEDULED | ✅ PASS | 5 проверок по id-запросам |
| [LD-NULL] | Round 10: score1/score2 IS NULL, status SCHEDULED | ✅ PASS | Все 8 матчей проверены |
| [LD-ABSENCE] | serov/round4 = 0 строк, нет NULL-предсказаний, нет 0:0-плейсхолдеров | ✅ PASS | 3 проверки |
| [LD-MAP] | Уникальность short_name и login; спот-чек Дин–Балт раунд 1 → 1:1 | ✅ PASS | 3 проверки |
| [LD-IDEMPOTENT] | Повторный запуск loader --reset → те же счётчики | ✅ PASS | 5 счётчиков совпадают |
| [DL-24H-FAIL] | Дедлайн = match−24h и match−23h → ValueError | ✅ PASS | 2 подтеста |
| [DL-24H-OK] | Дедлайн = match−3 days → принят | ✅ PASS | Дедлайн сохранён в БД |
| [ST-ILLEGAL] | PUBLISHED→ACTIVE и DRAFT→CALCULATED → ValueError | ✅ PASS | 2 подтеста |
| [ST-LOCK] | DRAFT→ACTIVE устанавливает is_locked=True | ✅ PASS | |
| [BT-PARTIAL] | 7/8 предсказаний → ValueError, 0 строк в БД | ✅ PASS | |
| [BT-FULL] | 8/8 сохранены атомарно; повторная отправка заменяет батч (8, не 16) | ✅ PASS | |
| [BT-ZERO] | Предсказание 0:0 сохранено как реальные значения (не NULL) | ✅ PASS | |
| [BT-DEADLINE] | Прошедший дедлайн и не-ACTIVE раунд → PermissionError | ✅ PASS | 2 подтеста |
| [CALC-ROUND] | Score rows для раундов 1–9 совпадают с expected_scores.csv | ✅ PASS | **90/90** |
| [CALC-COUNTS] | Агрегированные count_* по пользователям совпадают с leaderboard.csv | ✅ PASS | **10/10** |
| [CALC-COUNTS-ROW] | Per-round count_* vs expected_scores.csv с safety-gate | ✅ PASS | **90/90** |
| [CALC-ATOMIC] | Исключение mid-calculate_round → 0 Score-строк в БД (rollback) | ✅ PASS | |
| [CALC-VOID] | VOID матча → recalculate_round; Score-строки внутренне согласованы | ✅ PASS | 10 строк, total=base+b1+b2+b3 |

---

## Примечания о реализации

### [CALC-ROUND] — bonus2 в БД не всегда 0
В процессе отладки обнаружено: поле `Score.bonus2` содержит ненулевые значения (например, 8)
для некоторых пользователей/раундов. Это **не дефект** — контракт (`tester_1.2.md`) явно
указывает, что `expected_bonus2 == 0` относится к фикстурному столбцу (который объединяет
bonus1+bonus2 в `expected_bonus1`), а не к требованию нулевого DB-столбца.  
Проверка: `score.bonus1 + score.bonus2 == expected_bonus1` — **90/90 PASS**.

### [BT-FULL] — replace vs IntegrityError
`tester_1.2.md` предполагал IntegrityError при повторной отправке, однако Coder реализовал
DELETE-then-INSERT (замену батча). User-task явно подтверждает семантику замены. Тест
верифицирует именно замену (count=8, не 16) — **PASS**.

### [DL-24H-OK] — SQLite и timezone
SQLite не хранит timezone в DATETIME. При чтении обратно получаем naive-datetime.
Тест нормализует оба значения к UTC-aware перед сравнением.

---

## Файлы тестов

| Файл | Назначение |
|------|-----------|
| `tests/integration/conftest.py` | Фикстуры `loaded_db` и `minimal_db` |
| `tests/integration/test_loader_1_2.py` | [LD-*] тесты целостности загрузчика |
| `tests/integration/test_deadline_batch_1_2.py` | [DL-*] [ST-*] [BT-*] тесты дедлайнов/статусов/батчей |
| `tests/integration/test_calculate_persistence_1_2.py` | [CALC-*] тесты корректности расчёта |
