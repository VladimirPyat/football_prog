# Отчёт тестирования Stage 0

**Дата:** 2026-06-09  
**Этап:** 0 — Database & Configuration  
**Вердикт:** PASS

## 1. Проверка миграций (2.1)

| Команда | Результат | Exit code |
|---------|-----------|-----------|
| `uv run alembic upgrade head` | Успешно (SQLiteImpl, схема применена) | 0 |
| `uv run alembic downgrade base` | Успешно (`0992bb744cc8 → base`, Initial schema откат) | 0 |
| `uv run alembic upgrade head` (повторно) | Успешно (`base → 0992bb744cc8`) | 0 |

Цикл upgrade → downgrade → upgrade выполнен без ошибок. Rollback логика корректна.

## 2. Проверка ограничений и тестов (2.2)

### Unit-тесты @Coder (`tests/unit/test_db_models.py`)

| Тест | Покрытие | Результат |
|------|----------|-----------|
| `test_match_score_zero_zero_succeeds` | `0` — валидный счёт матча | PASS |
| `test_match_score_null_null_succeeds` | `NULL` — отсутствие результата матча | PASS |
| `test_match_invalid_score_raises_integrity_error` | CHECK: score < 0 и > 20 | PASS |
| `test_match_same_team_raises_integrity_error` | CHECK: team1_id != team2_id | PASS |
| `test_duplicate_prediction_raises_integrity_error` | UNIQUE (user_id, round_id, match_id) | PASS |
| `test_prediction_null_scores_succeeds` | NULL в прогнозе допустим | PASS |

### Дополнительные интеграционные тесты @Tester

Добавлены тесты для edge cases, не покрытых unit-набором:

| [TEST-ID] | Файл | Покрытие | Результат |
|-----------|------|----------|-----------|
| STAGE0-PRED-01 | `tests/integration/test_stage0_constraints.py` | Прогноз 0:0 — валидный счёт, не «отсутствие» | PASS |
| STAGE0-PRED-02 | `tests/integration/test_stage0_constraints.py` | CHECK на predictions: score < 0 и > 20 | PASS |
| STAGE0-PRED-03 | `tests/integration/test_stage0_constraints.py` | Отсутствие прогноза = нет строки в БД | PASS |
| STAGE0-SEED-01 | `tests/integration/test_stage0_seed.py` | rules_json и структурные поля = contest_defaults.json | PASS |
| STAGE0-SEED-02 | `tests/integration/test_stage0_seed.py` | rules_json без `_meta`, только контрактные секции | PASS |

### Ручная проверка на alembic-мигрированной БД (`football.db`)

- Вставка прогноза `score1=0, score2=0` — успешно.
- Вставка прогноза `score1=99` — `IntegrityError` (CHECK constraint).

### Критический invariant: 0 vs отсутствие прогноза

| Сценарий | Ожидание | Факт |
|----------|----------|------|
| Прогноз 0:0 | Строка с `score1=0, score2=0` | Подтверждено (unit + integration + migrated DB) |
| Отсутствие прогноза | Нет строки в `predictions` | Подтверждено (STAGE0-PRED-03) |
| NULL в прогнозе | Допустимо на уровне схемы | Подтверждено (unit) |

Схема поддерживает разделение: `0` — валидный счёт; отсутствие прогноза — absence of row (не sentinel `0`).

### Команда pytest

```
uv run pytest tests/ -v
```

**Результат:** 13 passed in 0.53s, exit code 0.

## 3. Проверка seed-данных (2.3)

| Команда | Результат | Exit code |
|---------|-----------|-----------|
| `uv run python src/scripts/seed.py` | contest_settings (id=1) + admin (login=admin) созданы | 0 |

### Сравнение `contest_settings` с `contest_defaults.json`

| Поле | В БД | В JSON | Совпадение |
|------|------|--------|------------|
| `total_teams` | 16 | 16 | ✓ |
| `matches_per_round` | 8 | 8 | ✓ |
| `total_rounds` | 30 | 30 | ✓ |
| `is_round_robin` | true | true | ✓ |
| `rules_json` | scoring_rules, tiebreakers, constraints, contest_structure | idem (без `_meta`) | ✓ |

`rules_json` в БД точно соответствует `build_rules_json()` из seed-скрипта и контрактным секциям `contest_defaults.json`.

## 4. Дефекты

Дефекты не обнаружены.

## 📸 Integration & DBeaver Verification

Дополнительные интеграционные тесты (`tests/db/test_integration_flow.py`), добавлены без дублирования unit-тестов @Coder.

| ID | Тест | Результат |
|----|------|-----------|
| **IF-01** | Full Round Lifecycle (seed → round → 8 matches → 3×8 predictions → 2 FINISHED → JOIN) | **PASS** |
| **IF-02** | Batch Prediction Uniqueness (volchenko, duplicate → IntegrityError) | **PASS** |
| **IF-03** | DBeaver Visual Verification Data (labeled chain + ID logging) | **PASS** |

**IF-01:** все вставки успешны; FK корректны; `JOIN users ↔ predictions ↔ matches` вернул ровно 24 строки; у 6 `SCHEDULED` матчей `score1/score2` остались `NULL`.

**IF-02:** полный набор из 8 прогнозов для `volchenko` сохранён; повторная вставка `(user_id, round_id, match_id)` → `IntegrityError`.

**IF-03:** цепочка для ручной проверки в DBeaver создана. На Stage 0 отдельной таблицы `contests` нет — метка `DBeaver_Check_Stage0` записана в `contest_settings.rules_json.dbeaver_check_name`. При запуске теста в stdout выводятся runtime-ID:

```
[IF-03] DBeaver smoke test IDs: contest_settings_id=1, team_home_id=1, team_away_id=2, round_id=1, match_id=1, user_id=1, prediction_id=1, dbeaver_check_name=DBeaver_Check_Stage0
```

Прогноз `0:0` сохранён успешно (доказывает, что `0` — валидный счёт).

```
uv run pytest tests/db/test_integration_flow.py -v
```

**Результат:** 3 passed, exit code 0.

**Вердикт по интеграционной готовности:** PASS. Базовые категории M/FK/UQ/CK не переоценивались — они остаются PASS по handoff @Coder.

## 5. Заключение

Stage 0 готов для перехода к следующему этапу. Схема БД, миграции, ограничения, seed-данные и интеграционные сценарии соответствуют контракту `agent_docs/contracts/db_schema.md` и `contest_defaults.json`.
