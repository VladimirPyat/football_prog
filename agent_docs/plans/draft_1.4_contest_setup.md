# План Этапа 1.4: Multi-contest, Setup phase, полная contest logic

> Решения пользователя из чата (авторитетные). Фаза B — инструкции и контракты готовы.

## 1. Цели

1. **Несколько конкурсов** в одной БД — отказ от singleton `contest_settings`.
2. **Фаза SETUP** (`status=DRAFT`, `is_locked=false`): создание конкурса, CRUD команд и участников (инвайты + temp password), PATCH правил/структуры.
3. **Фаза RUNNING** (после первого activate): только пары из существующих команд; прогнозы до дедлайна; результаты **после** дедлайна; расчёт только при `round.status=CLOSED`.
4. **Явное закрытие тура** `POST .../rounds/{id}/close` + **синхронный auto-close** при API-вызовах (без BackgroundTasks).
5. **Free Tour** — `POST .../admin/rounds/free-tour` (сценарий 7, `docs/04_supervisor_scenario.md`).
6. **Contest-scoped API** — префикс `/api/v1/contests/{contest_id}/...`; legacy-пути 1.3 — thin shims для регрессии loader-тестов.
7. **Exceptional tie-break** — колонка на `contest_participants`, не на `users`; разрешена после `is_locked` (без изменения `rules_json`).

**Out of scope 1.4:** newsletters / email BackgroundTasks.

## 2. Связь с 1.3

| 1.3 (готово / в тесте) | 1.4 (расширение) |
|------------------------|------------------|
| JWT, RBAC, caching | Сохранить; contest_id в deps |
| Lifecycle pause/finish/delete | Per-contest; delete wipes one contest |
| Immutability `is_locked` | На таблице `contests` |
| Singleton endpoints | Миграция + shims |
| Unit tests API/lifecycle | Расширить multi-contest |
| Tester: auth/RBAC на loader data | Tester 1.3 — узкий scope |
| — | Tester 1.4 — **полный HTTP E2E** (90/90, 10/10) |

**Prerequisite:** 1.3 `TEST_PASS` (минимум `READY_FOR_TEST` для старта кодера).

## 3. Миграция схемы

### 3.1 Новая таблица `contests` (замена `contest_settings`)

| Колонка | Тип | Примечание |
|---------|-----|------------|
| `id` | INTEGER PK | |
| `name` | VARCHAR NOT NULL | Отображаемое имя |
| `slug` | VARCHAR UNIQUE NULL | Опционально для URL |
| `is_locked` | BOOLEAN DEFAULT FALSE | |
| `status` | VARCHAR | DRAFT/RUNNING/PAUSED/FINISHED |
| `paused_at`, `finished_at` | TIMESTAMPTZ NULL | Как в 1.3 |
| `total_teams`, `matches_per_round`, `total_rounds`, `is_round_robin` | INTEGER/BOOLEAN | Структура |
| `rules_json` | JSONB | Из `contest_defaults.json` |

### 3.2 `contest_participants`

| Колонка | Тип | Примечание |
|---------|-----|------------|
| `contest_id` | FK → contests | |
| `user_id` | FK → users | |
| `status` | VARCHAR | `PENDING`, `ACCEPTED` |
| `exceptional_tiebreak_points` | INTEGER DEFAULT 0 | CHECK >= 0 |
| PK | `(contest_id, user_id)` | |

Удалить `users.exceptional_tiebreak_points` (данные перенести в default contest participant row).

### 3.3 Contest-scoped FK

| Таблица | Изменение |
|---------|-----------|
| `teams` | + `contest_id` FK; UNIQUE `(contest_id, name)` |
| `rounds` | + `contest_id` FK; UNIQUE `(contest_id, number)` вместо global |
| `matches`, `predictions`, `scores` | Косвенно через `round_id` / contest filter |

`users`, `contacts` — глобальные (login уникален глобально).

### 3.4 Backfill (migration `1.4`)

1. Создать `contests` из единственной строки `contest_settings` (`name='Default'`, `id=1`).
2. Проставить `contest_id=1` на все `teams`, `rounds`.
3. Создать `contest_participants` для каждого user с predictions или всех users loader-а; скопировать `exceptional_tiebreak_points`.
4. DROP `contest_settings`; DROP `users.exceptional_tiebreak_points`.
5. `load_test_data.py` — загрузка в contest id=1 (или параметр `--contest-id`).

## 4. Фазы конкурса

### SETUP (`contests.status=DRAFT`, `!is_locked`)

| Действие | Кто | API |
|----------|-----|-----|
| Создать конкурс | SUPERVISOR+ | `POST /contests` |
| PATCH структура/rules | SUPERVISOR+ | `PATCH /contests/{id}` |
| CRUD teams | SUPERVISOR+ | `.../teams` |
| CRUD participants + invite | SUPERVISOR+ | `.../participants` |
| Создать round DRAFT | SUPERVISOR+ | `.../admin/rounds` |

### RUNNING (после первого activate → `is_locked=true`, `status=RUNNING`)

| Действие | Условие |
|----------|---------|
| PATCH contest / teams / participants | **403** (ContestLocked) |
| Create/edit rounds | Только пары из teams конкурса; 24h rule |
| Predictions POST | `round=ACTIVE`, `now < deadline`, contest RUNNING |
| Auto-close / close | `ACTIVE → CLOSED` when `now >= deadline` |
| PUT match result | `now >= deadline`, contest RUNNING, round CLOSED (или ACTIVE→auto-close first) |
| Calculate | `round=CLOSED`, all matches FINISHED or terminal |
| Exceptional tie-break | ADMIN, **разрешено** при locked |

Подробная матрица: `contracts/contest_lifecycle_flow.md`.

## 5. Auto-close (без BackgroundTasks)

**Механизм:** dependency / middleware hook `auto_close_expired_rounds(session, contest_id)`:

- Вызывается в начале каждого contest-scoped handler (или централизованно в `get_contest_or_404`).
- Для всех `rounds` конкурса со `status=ACTIVE` и `deadline <= now(UTC)` → `transition_round(..., CLOSED)`.
- Идемпотентно; в одной транзакции с основным запросом.

**Явное закрытие:** `POST .../rounds/{id}/close` — SUPERVISOR; только `ACTIVE`; опционально до дедлайна (early close для тестов — разрешить если `now >= deadline` OR explicit admin close? **Решение:** explicit close разрешён только когда `now >= deadline`; иначе 400. Auto-close покрывает deadline case.)

## 6. Free Tour

По `docs/04_supervisor_scenario.md` §7:

- Input: список `{match_id, new_date_time}` только для матчей `POSTPONED`; deadline нового тура.
- Создаёт новый round (`number = max+1`, часто 31); матчи **переносятся** (UPDATE round_id) из исходных туров.
- Исходные туры: уменьшить `matches_count`; если матч был единственным — валидация на уровне сервиса.
- Активация free tour — отдельный activate как обычный round.
- Contest must be RUNNING; teams readonly (берутся из match).

## 7. API surface (summary)

Полный контракт: `contracts/api_v1.yaml`.

**Primary:** `/api/v1/contests/{contest_id}/...`

- Contest CRUD + lifecycle (pause/resume/finish/delete)
- Teams, participants, exceptional-tiebreak on participant
- Rounds, matches, predictions, leaderboard, results
- `POST .../rounds/{id}/close`, `POST .../admin/rounds/free-tour`

**Legacy shims (deprecated):** `/api/v1/rounds`, `/api/v1/admin/...` без prefix → resolve **default contest** (единственный RUNNING или единственный в БД). Нужны для 1.3 tester на loader data.

## 8. Тестирование (стратегия)

| Stage | Scope |
|-------|-------|
| 1.3 Tester | HTTP на **loader data**: auth, RBAC, predictions, lifecycle, cache, tie-break, VOID; calculate **smoke** (не 90/90) |
| 1.4 Tester | **Full E2E** через HTTP only: empty DB → setup → 9 rounds → activate → predict → close → results → calculate → **90/90** + **10/10**; manual scripts |
| 1.2 integration | Без изменений (persistence canary) |

## 9. Порядок выполнения (@Coder)

1. Alembic migration 1.4 + models
2. `contest_setup_service.py` (create contest, teams, participants, invites)
3. Refactor lifecycle/teardown/leaderboard для `contest_id`
4. Auto-close hook + `close_round` endpoint
5. Result deadline guard в `match_service`
6. Free tour service
7. Contest-scoped routers + legacy shims
8. Update `load_test_data.py` for multi-contest backfill compat
9. Unit tests `test_contest_setup_1_4.py`, `test_multi_contest_1_4.py`, extend lifecycle tests

## 10. Риски и решения

| Риск | Решение |
|------|---------|
| Breaking 1.2 integration tests | Loader всегда seed contest_id=1; shims для legacy paths |
| Round number uniqueness | Per-contest `(contest_id, number)` |
| Leaderboard tie-break source | Read from `contest_participants` join |
| Два конкурса — один user | OK; participant row per contest |
