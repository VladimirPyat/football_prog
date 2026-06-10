# План Этапа 1: Бэкенд-ядро (Backend Core)

> Статус: **ЧЕРНОВИК (Фаза А)**. Требует утверждения пользователем (✅) перед генерацией инструкций агентам (Фаза Б).
> Источники: `docs/01_tech_regulations.md`, `docs/02_project_structure.md`, `docs/03_user_scenarios.md`, `docs/04_supervisor_scenario.md`, `docs/test_data/*`, `docs/roadmap.csv`.

---

## 1. Обзор и цель этапа

Этап 1 строит ядро бэкенда поверх готовой БД (Этап 0): аутентификация, ввод прогнозов (batch-only), машина дедлайнов, движок скоринга, лидерборды. Критерий успеха по roadmap:
> «API проходит контракт-тесты, расчёт совпадает с историческими данными, транзакции атомарны».

**Главный результат предварительного анализа данных (`docs/test_data/contracted/`) — обе проблемы сняты после уточнений пользователя (2026-06-10):**
- ✅ **Базовые очки** воспроизводятся точь-в-точь: **89/89** строк (туры 1–9, 10 игроков).
- ✅ **Бонусы 1/2/3** воспроизводятся: `expected_total` **89/89**, `expected_bonus3` 89/89. Полное правило: `agent_docs/contracts/bonus_rules.md`.
- ✅ **Лидерборд и тай-брейкеры**: полный рейтинг + итоги совпадают с `leaderboard.csv` **10/10**. Правило: `agent_docs/contracts/leaderboard_tiebreakers.md`. Колонки-счётчики = частота попаданий (тай-брейк-инпуты).

Особенности фикстур (для @Tester): бонус 2 «вшит» в колонку `expected_bonus1` (`expected_bonus2`=0); per-round `count_*` в `expected_scores.csv` !!!ТРЕБУЕТ УТОЧНЕНИЯ!!!   . 
`leaderboard.csv` Подробности: `agent_docs/reports/BLOCKED.md`.

---

## 2. Архитектура (модульный монолит)

Слои внутри `src/` (слабая связанность, перспектива выделения сервисов):

```
src/
  api/                      # FastAPI роутеры (тонкий слой, без бизнес-логики)
    v1/
      auth.py               # /auth/login, /auth/change-password
      rounds.py             # публичные: leaderboard, results, predictions (чтение)
      predictions.py        # пользовательские: submit batch
      admin_rounds.py       # supervisor: создание/редактирование туров
      admin_results.py      # supervisor: ввод результатов, VOID, calculate
      admin_misc.py         # supervisor/admin: teams, participants, override
      deps.py               # DI: сессия БД, current_user, RoleChecker
  core/
    security.py             # bcrypt, JWT (создание/верификация), get_settings
    config.py               # уже есть в config/settings.py — переиспользуем
    errors.py               # доменные исключения -> HTTP коды
  schemas/                  # Pydantic v2 (request/response DTO)
    auth.py  predictions.py  rounds.py  admin.py  leaderboard.py
  services/                 # бизнес-логика (чистая, тестируемая)
    auth_service.py
    prediction_service.py   # batch-only, NULL-семантика, deadline
    round_service.py        # статусная машина тура, правило 24ч
    match_service.py        # результаты, статусы, VOID
    scoring_service.py      # читает правила из contest_settings.rules_json
    leaderboard_service.py  # агрегация + тай-брейкеры
  repositories/             # доступ к данным (опц., если упрощает тесты)
  database/                 # есть из Этапа 0 (models, engine, base)
  scripts/
    seed.py                 # есть
    load_test_data.py       # НОВОЕ: загрузчик contracted-данных для @Tester
main.py                     # сборка FastAPI app, middleware (CORS), роутеры
```

**Ключевые принципы:**
- Роутер не содержит логики — только валидация DTO, вызов сервиса, маппинг ошибок.
- `ScoringService` читает все числовые значения/пороги/множители из `contest_settings.rules_json` (хардкодим только структуру правил, не значения).
- Атомарность: расчёт тура и пересчёт при VOID — в одной транзакции (`async with session.begin()`), полный пересчёт всех участников тура.

---

## 3. Аутентификация и авторизация (RBAC)

- **JWT** (`python-jose`), пароли — **bcrypt**. Зависимости уже в стеке (`docs/02`); добавляем через `uv add`, если их нет в `pyproject.toml`.
- `POST /auth/login` → `{access_token, token_type}`; токен содержит `sub=user_id`, `role`, `exp`.
- `is_temp_password=True` → логин успешен, но клиент обязан вызвать `POST /auth/change-password` (UC-4). До смены — ограниченный доступ (только смена пароля).
- `RoleChecker` (зависимость FastAPI) защищает все эндпоинты. Матрица ролей:
  - `VISITOR` (без токена): публичные `GET` лидерборд/результаты прошедших туров.
  - `USER`: + свои прогнозы (чтение/запись до дедлайна), свои контакты.
  - `SUPERVISOR`: + управление турами/матчами/результатами/VOID/calculate.
  - `ADMIN`: + override, пересчёт всего конкурса, назначение supervisor.
- **Seed-данные тестов**: `users.csv` → роль `USER`; для e2e нужен пользователь `user/user` (см. `docs/03`) и `supervisor` — учитываем в `load_test_data.py`.

---

## 4. Прогнозы: batch-only и NULL-семантика (критично)

- `POST /api/v1/rounds/{id}/predictions` принимает **ровно `matches_per_round` прогнозов** (all-or-nothing). Частичное → `400`.
- Запись атомарна (одна транзакция): либо все строки сохранены, либо ни одной.
- После `deadline` (или статус тура `CLOSED`+) → `403`, поля readonly.
- **Правило NULL ≠ 0**: отсутствие прогноза = отсутствие строки в `predictions`. `0` — значащий счёт. Pydantic-поля счёта — целые `0..max_score_value`; в скоринге сравнение строго `IS NOT NULL`, запрещено `.get('score', 0)` или `!= 0`.
- Приватность: до дедлайна прогноз виден только автору и Supervisor; после — всем (UC-8/UC-9).

---

## 5. Статусные машины

**Round**: `DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED`.
- `DRAFT→ACTIVE`: активация приёма прогнозов (первый ACTIVE = старт конкурса → `contest_settings.is_locked=TRUE`).
- `ACTIVE→CLOSED`: дедлайн прошёл (приём закрыт).
- `CLOSED→CALCULATED`: вызван расчёт (`POST /admin/rounds/{id}/calculate`).
- `CALCULATED→PUBLISHED`: публикация итогов (immutable).
- **Правило 24ч**: нельзя менять `deadline`, если до первого матча тура < `deadline_rule_hours` (24); `deadline` должен быть `< first_match_date - 24h`. Нарушение → `400`.

**Match**: `SCHEDULED → FINISHED → (VOID)`; также `POSTPONED`, `CANCELED`.
- Ввод результата: `score 0..max_score_value`, переводит в `FINISHED`.
- `VOID`: очки за матч = 0, атомарный пересчёт тура.
- `POSTPONED` → кандидат во Free Tour (вне MVP Этапа 1, зарезервировано).

---

## 6. Движок скоринга (ScoringService)

### 6.1 Базовые очки — ✅ ВЕРИФИЦИРОВАНО (полная спецификация в `agent_docs/dataflow/scoring_flow.md`)
Приоритет Exact > Diff > Outcome, ровно одна категория за матч. Алгоритм воспроизводит `expected_base_pts` на 89/89 строках. Это «золотой» инвариант для тестов Этапа 1.

### 6.2 Бонусы — ✅ ВЕРИФИЦИРОВАНО (`agent_docs/contracts/bonus_rules.md`)
- Бонус 1 — уникальность **исхода** (П1/Х/П2), `база×множитель%` (×2 при 200%), суммируется по туру.
- Бонус 2 — по числу угаданных исходов (база ≥ 4): 6→8, 7→12, 8→16.
- Бонус 3 — базис `база+бонус1+бонус2`; ранги 12/8/4 (равные очки → все получают балл места) + 4 за базис ≥ 50; ничего при базе = 0.
Бонус-слой — отдельная функция поверх базовых очков; значения из `rules_json`.

### 6.3 Тай-брейкеры (итоговый лидерборд) — ✅ ВЕРИФИЦИРОВАНО (`agent_docs/contracts/leaderboard_tiebreakers.md`)
Порядок: `total_points DESC → exact_scores_count (eh+ex) DESC → total_without_bonuses DESC → correct_diffs_count DESC → manual_tiebreak (из конфига)`. Реализуется в `LeaderboardService`; 5-й ручной критерий и эндпоинт override обязательны. Счётчики (частоты) — входы критериев 2 и 4.

---

## 7. Загрузчик тестовых данных (`load_test_data.py`)

`TESTING_1.md` ссылается на `test_data/scripts/load_test_data.py` — **скрипт отсутствует**, его нужно создать в Этапе 1. Особенности маппинга, которые надо учесть:
- `teams.csv` — разделитель **запятая**, без `id`, колонки `short_name,full_name,logo_url`.
- `users.csv` — разделитель `;`, колонка `full_name` (одно поле) → модель требует `first_name/last_name` (нужна стратегия разбиения/маппинга; предложение — `last_name=full_name`, `first_name=""`, либо расширить контракт).
- `matches.csv` — команды по `short_name`, дата формата `ДД.ММ.ГГГГ|ЧЧ:ММ` → парсинг в `TIMESTAMPTZ`; тур 10 = `SCHEDULED`, счета пустые (`NULL`).
- `predictions.csv` — отсутствие строки = нет прогноза (НЕ `0:0`); у `serov` нет тура 4.
- Все CSV-импорты — разделитель `;` по правилу проекта, **кроме** `teams.csv` (запятая) — расхождение фиксируем в инструкции загрузчику.

---

## 8. Разбивка на 3 изолированных под-этапа (для Фазы Б)

| № | Под-этап | Содержание | Зависит от | Инструкции |
|---|----------|-----------|-----------|-----------|
| **1.1** | **Scoring Engine** | Чистая математика без БД/API: база, бонусы 1/2/3, тай-брейкеры, плотный ранг. Вход — структуры данных, выход — dataclass. Юнит-тесты построчной сверки с `expected_scores.csv`/`leaderboard.csv` | Этап 0 (модели — только для типов) | `coder_1.1.md`, `tester_1.1.md` |
| **1.2** | **Setup, Deadlines & Data Loader** | CSV-загрузчик (маппинг по id, конфиг маппинга), статусные машины Round/Match, правило 24ч, batch-прогнозы (all-or-nothing, NULL≠0), VOID-пересчёт. Сервисный слой + юнит/интеграция на БД | 1.1, Этап 0 | `coder_1.2.md`, `tester_1.2.md` |
| **1.3** | **API Integration & Triggers** | FastAPI app, auth/JWT/bcrypt, RoleChecker (RBAC), все роуты `api_v1.yaml`, `calculate`-триггер (атомарно), публичные лидерборд/результаты + HTTP-кэш. Интеграционные тесты API | 1.1, 1.2 | `coder_1.3.md`, `tester_1.3.md` |

**Контракты-источники для всех под-этапов:** `contracts/bonus_rules.md`, `contracts/leaderboard_tiebreakers.md`, `dataflow/scoring_flow.md`, `contracts/api_v1.yaml`, `contracts/db_schema.md`.

**Все под-этапы разблокированы** (по очкам — 0 расхождений на контрактных данных). Реализуем строго 1.1 → 1.2 → 1.3.

---

## 9. Зависимости (через `uv add`, требуют подтверждения пользователя)
Проверить наличие в `pyproject.toml`; добавить недостающее:
- `fastapi`, `uvicorn[standard]`, `python-jose[cryptography]`, `passlib[bcrypt]` (или `bcrypt`), `python-multipart` (формы login), `httpx` (тесты), `pytest-asyncio`.
> По правилу проекта новые пакеты — только с явного одобрения пользователя.

---

## 10. Блокеры (см. `agent_docs/reports/BLOCKED.md`)
1. ✅ РЕШЁН — бонусы 1/2/3 верифицированы (`contracts/bonus_rules.md`), `expected_total` 89/89.
2. ✅ РЕШЁН — счётчики = частота попаданий; эталон из `leaderboard.csv` (10/10); per-round `count_*` не используются (`contracts/leaderboard_tiebreakers.md`).
3. ⚠️ ОТКРЫТО (не критично) — `users.csv` (`full_name`) vs модель (`first_name/last_name`); `teams.csv` с запятой; отсутствует `load_test_data.py`. Предлагаемый дефолт маппинга: `last_name=full_name`, `first_name=""`. Требует подтверждения в Фазе Б.

## 11. Следующий шаг
Блокеры 1 и 2 сняты. Жду общего ✅ для перехода к Фазе Б (генерация `instructions/coder_1.md`, `instructions/tester_1.md`) и подтверждения дефолта маппинга тестовых данных (п.3).
