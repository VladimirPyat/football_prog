# Ручная проверка подсчёта очков (Stage 1 sign-off)

Инструкция для владельца проекта / организатора: доказать, что очки считаются из данных БД, а не «зашиты» в код, и совпадают с эталонными CSV.

## 1. Цель и три уровня проверки

| Уровень | Что проверяет | Где |
|---------|---------------|-----|
| **1.1** | Чистая математика scoring engine (без БД) | `tests/scoring/` |
| **1.2** | Персистентность: loader → `calculate_round` → таблица `scores` | `tests/integration/` |
| **1.4** | Полный путь через HTTP + сравнение БД с CSV | эта инструкция + `tests/api/` + `tests/manual/` |

Ниже — сценарий **1.2 + 1.4** для финальной приёмки Stage 1.

## 2. Эталонные файлы (read-only)

Не редактируйте во время обычного прогона:

| Файл | Назначение |
|------|------------|
| `docs/test_data/contracted/predictions.csv` | Прогнозы участников |
| `docs/test_data/contracted/matches.csv` | Результаты матчей |
| `docs/test_data/contracted/expected_scores.csv` | Ожидаемые очки (**90 строк**, раунды 1–9) |
| `docs/test_data/contracted/leaderboard.csv` | Итоговый рейтинг (**10 игроков**) |
| `docs/test_data/config/contest_defaults.json` | Правила scoring |

## 3. Быстрая автоматическая проверка (рекомендуется)

```bash
uv run pytest tests/integration/test_calculate_persistence_1_2.py -v
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
uv run pytest tests/integration/ tests/api/ -v
```

- Первая команда — **[CALC-ROUND] 90/90** через сервисный слой (loader).
- Вторая — **[API-RESULTS] 90/90** через HTTP `POST .../contests/1/admin/rounds/{id}/calculate`.
- Третья — полный регресс Stage 1 (integration + API).

## 4. Ручной двухфазный прогон

### Подготовка

```bash
uv run alembic upgrade head
```

**Вариант A — loader + HTTP calculate (быстрее):**

```bash
uv run python tests/manual/verify_via_api.py --bootstrap load --database-url sqlite+aiosqlite:///./football_verify.db
```

**Вариант B — полная HTTP-настройка (медленнее, без loader):**

```bash
uv run python tests/manual/verify_via_api.py --bootstrap empty --database-url sqlite+aiosqlite:///./football_e2e.db
```

Переменные окружения: `DATABASE_URL`, `CONTEST_ID`, `API_BASE_URL`, `VERIFY_BOOTSTRAP` — см. [tests/manual/README.md](../tests/manual/README.md).

### Фаза 1 — Script 1 (`verify_via_api.py`)

1. Создаёт/загружает конкурс (contest-scoped API).
2. Считает раунды 1–9 через HTTP (или полный цикл setup→predict→close→result→calculate в режиме `empty`).
3. Smoke: `GET .../leaderboard`, `GET .../rounds`.

**Ожидание:** exit code `0`, в stdout `OK contest_id=...`.

### STOP — DBeaver (только чтение)

Файл SQLite из `DATABASE_URL` (по умолчанию `./football_verify.db`).

Примеры запросов:

```sql
SELECT COUNT(*) FROM predictions;
SELECT round_id, status, score1, score2 FROM matches LIMIT 20;
SELECT user_id, round_id, total_with_bonus3 FROM scores LIMIT 20;
SELECT number, status FROM rounds WHERE number <= 9;
```

После полного dev bootstrap (`dev_setup.py` + `finalize_dev_fixture`) в `scores` ожидается **100 строк** (90 за туры 1–9 + 10 за тур 10 `CALCULATED`); тур 11 — без очков до ручного calculate.

Проверьте: после `finalize_dev_fixture` раунды 1–9 в статусе **`PUBLISHED`**; в `scores` ~90 строк; **отсутствие прогноза = нет строки** в `predictions`, не `NULL` и не `0:0`-sentinel. Без finalize (только loader) раунды 1–9 остаются `CLOSED`.

### Фаза 2 — Script 2 (`compare_db_vs_reference.py`)

```bash
uv run python tests/manual/compare_db_vs_reference.py --contest-id 1 --database-url sqlite+aiosqlite:///./football_verify.db
```

Сравниваются: `base`, `bonus1+bonus2`, `bonus3`, `total_with_bonus3`, агрегаты `count_*` vs `leaderboard.csv`.

**Ожидание:** exit code `0`, `scores=90/90 leaderboard=10/10`.

## 5. CANARY — доказательство, что ответы не зашиты

1. Скопируйте `expected_scores.csv` во временный файл.
2. Измените одну ячейку `expected_total` (+999).
3. Запустите Script 2 с `--expected-scores /path/to/copy.csv` **без изменения кода приложения**.
4. **Должен FAIL** с сообщением вида `login/round N: total: got X, want Y`.
5. Верните эталон → **PASS**.

Автоматический аналог: `tests/api/test_canary_scoring_1_4.py` (`[CANARY-PYTEST-ORACLE]`, `[CANARY-PYTEST-REVERT]`).

**Не коммитьте** canary-правки в `docs/test_data/contracted/`.

## 6. Что менять для проверки разных слоёв

| Если изменить… | Перезапустить | Ожидание |
|----------------|---------------|----------|
| `predictions.csv` → reload / re-submit | integration или Script 1+2 | FAIL на затронутых строках |
| `matches.csv` → reload / PUT result | то же | FAIL |
| только `expected_scores.csv` (canary) | Script 2 / pytest | FAIL (oracle изменился) |
| `scores` напрямую в DBeaver | Script 2 без recalculate | может PASS до следующего calculate |
| `src/scoring/*` | `tests/scoring/` | FAIL если математика сломана |

## 7. Типичные проблемы

- Раунд не `CLOSED` → calculate возвращает 400/403.
- Result до deadline → 403.
- Partial predictions → 400 (batch rejected).
- Неверный `contest_id` или путь к SQLite в multi-contest setup.

## 8. Критерий приёмки Stage 1

- [ ] `tests/integration/` green — 90/90 persistence
- [ ] `tests/api/` green — 90/90 via HTTP
- [ ] Script 1 exit 0
- [ ] Script 2 exit 0 (90/90 + 10/10)
- [ ] CANARY fail → revert → pass
- [ ] DBeaver inspection (рекомендуется)

## Связанные документы

- [SCORING_LOGIC.md](SCORING_LOGIC.md)
- [DB_REFERENCE.md](DB_REFERENCE.md)
- [API_GUIDE.md](API_GUIDE.md)
- [tests/manual/README.md](../tests/manual/README.md)
