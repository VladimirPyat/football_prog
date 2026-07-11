# Архитектура системы

Высокоуровневое описание бэкенда платформы конкурсов футбольных прогнозов (Football Predictions Contest). Списки эндпоинтов, столбцы таблиц и формулы начисления очков — по ссылкам в конце документа; этот документ не дублирует эти спецификации.

## Содержание

- [Назначение](#назначение)
- [Контекст системы](#контекст-системы)
- [Слоистая архитектура](#слоистая-архитектура)
- [Структура кода](#структура-кода)
- [Модель данных](#модель-данных)
- [Модель мультиконкурса](#модель-мультиконкурса)
- [Конечные автоматы жизненного цикла](#конечные-автоматы-жизненного-цикла)
- [Потоки запросов и данных](#потоки-запросов-и-данных)
- [Конвейер начисления очков](#конвейер-начисления-очков)
- [Безопасность и доступ](#безопасность-и-доступ)
- [Сквозные аспекты](#сквозные-аспекты)
- [Дополнительные материалы](#дополнительные-материалы)

## Назначение

Бэкенд поддерживает платформу футбольных прогнозов с поддержкой **нескольких конкурсов** (multi-contest):

- Организаторы настраивают конкурсы (команды, участники, правила), проводят туры, вводят результаты, рассчитывают и публикуют таблицы результатов.
- Участники отправляют пакет прогнозов до дедлайна тура.
- Посетители читают публичные таблицы лидеров и опубликованные результаты.
- Правила начисления очков хранятся в `contests.rules_json`; **чистый (pure)** движок начисления очков вычисляет баллы без обращения к базе данных.

**Поверхность API:** OpenAPI v1.2.0 — [`agent_docs/contracts/api_v1.yaml`](../../agent_docs/contracts/api_v1.yaml)  
**Основной префикс:** `/api/v1/contests/{contest_id}/…`

## Контекст системы

```mermaid
flowchart LR
    subgraph clients [Clients]
        WEB[Web UI / Frontend]
        CLI[Scripts & tests]
    end

    subgraph backend [Backend — this repo]
        API[FastAPI / Uvicorn]
        SVC[Services]
        ENG[Scoring engine]
        DB[(SQLite / PostgreSQL)]
        FS[Static files]
    end

    WEB -->|JWT REST| API
    CLI -->|httpx / scripts| API
    API --> SVC
    SVC --> ENG
    SVC --> DB
    API --> FS
```

| Граница | Технология |
|----------|------------|
| HTTP | FastAPI, валидация Pydantic, OpenAPI |
| Хранение данных | SQLAlchemy 2 async, миграции Alembic |
| Аутентификация | JWT (HS256), пароли bcrypt |
| Правила и конфигурация | `contests.rules_json`, `config/settings.py`, `.env` |
| Статические ресурсы | `/static/assets/*` (встроенные), `/static/teams/*` (загрузки) |

## Слоистая архитектура

```mermaid
flowchart TB
    subgraph http [HTTP layer]
        R[src/api/v1/* routers]
        H[src/api/handlers]
        D[src/api/deps.py]
    end

    subgraph domain [Domain layer]
        SV[src/services/*]
        SC[src/scoring/*]
    end

    subgraph infra [Infrastructure]
        ORM[src/database]
        CFG[config/settings.py]
        CORE[src/core — security, exceptions, logging]
    end

    R --> D
    R --> H
    R --> SV
    H --> SV
    SV --> SC
    SV --> ORM
    D --> CORE
    SV --> CORE
    R -->|AppError| EH[error_handlers]
```

**Принципы:**

| Правило | Где |
|------|--------|
| Роутеры остаются «тонкими» | Делегируют логику в `services/` или общие `handlers/` |
| Бизнес-правила в сервисах | Конечные автоматы состояний, guard-проверки, транзакции |
| Чистое начисление очков | `src/scoring/` — без обращений к БД; вызывается из `scoring_persistence` |
| Типизированные ошибки домена | `AppError` → JSON `{detail, code}`; без `HTTPException` в сервисах |
| Побочные эффекты в рамках конкурса | Автозакрытие истёкших туров через зависимость на маршрутах конкурса |

Подробнее: [API Guide — Архитектура](API_GUIDE.md#architecture)

## Структура кода

```
main.py              → app factory, CORS, routers, static mounts
config/settings.py   → env-backed Settings singleton
src/
  api/v1/            → REST endpoints (auth, contests, setup, predictions, admin)
  api/handlers/      → shared leaderboard / predictions response builders
  api/deps.py        → DB session, JWT user, RoleChecker, ContestContext, auto-close
  core/              → security, exceptions, logging
  database/          → models, async engine
  schemas/           → Pydantic DTOs (mirror OpenAPI components)
  scoring/           → engine, rules accessor, standings builder
  services/          → all mutable business logic
  scripts/           → seed, bootstrap_users, load_test_data
alembic/             → schema migrations
static/assets/       → default team logo (committed)
uploads/teams/       → supervisor uploads (gitignored)
```

## Модель данных

Десять таблиц. Конкурс (Contest) — это **корневой агрегат** для команд, туров и участия.

```mermaid
erDiagram
    users ||--o| contacts : has
    users ||--o{ contest_participants : enrolls
    contests ||--o{ contest_participants : has
    contests ||--o{ teams : contains
    contests ||--o{ rounds : contains
    rounds ||--o{ matches : contains
    teams ||--o{ matches : team1
    teams ||--o{ matches : team2
    users ||--o{ predictions : submits
    rounds ||--o{ predictions : for
    matches ||--o{ predictions : on
    users ||--o{ scores : earns
    rounds ||--o{ scores : per

    contests {
        int id PK
        string status
        bool is_locked
        json rules_json
    }
    contest_participants {
        int contest_id PK
        int user_id PK
        string status
        int exceptional_tiebreak_points
    }
    rounds {
        int id PK
        string status
        timestamptz deadline
    }
    scores {
        int user_id
        int round_id
        int total_with_bonus3
        int count_exact_high
    }
```

**Глобальное и в рамках конкурса:**

| Понятие | Хранение |
|---------|----------|
| Логин, пароль, глобальная роль | `users.role` — одно из `USER`, `SUPERVISOR`, `SUPPORT` |
| Участие в конкурсе | `contest_participants` — `PENDING` / `ACCEPTED` |
| Правила начисления очков | `contests.rules_json` (фиксируются при `is_locked`) |
| Ручное переопределение тай-брейка | `contest_participants.exceptional_tiebreak_points` (не входит в `rules_json`) |

Полный список столбцов: [`agent_docs/contracts/db_schema.md`](../../agent_docs/contracts/db_schema.md) · [Справочник БД](DB_REFERENCE.md)

## Модель мультиконкурса

Начиная с этапа 1.4 поддерживается **несколько конкурсов** в одной базе данных. Каждый конкурс владеет своими командами, турами и записями участников.

```mermaid
flowchart LR
    U[users — global identity]
    C1[contest A]
    C2[contest B]
    U -->|contest_participants| C1
    U -->|contest_participants| C2
    SUP[SUPERVISOR] -->|GET /contests| C1
    SUP --> C2
    PL[USER] -->|GET /me/contests| C1
```

Устаревшие маршруты без `{contest_id}` разрешаются в конкурс по умолчанию (`id=1`) для обратной совместимости тестов.

<a id="lifecycle-state-machines"></a>

## Конечные автоматы жизненного цикла

### Конкурс

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> RUNNING : first round activate\n(is_locked=true)
    RUNNING --> PAUSED : Support pause
    PAUSED --> RUNNING : Support resume
    RUNNING --> FINISHED : Support finish
    PAUSED --> FINISHED : Support finish
```

| Фаза | `status` | `is_locked` | Типичные операции |
|-------|----------|-------------|-------------------|
| Настройка | `DRAFT` | `false` | Команды, приглашения, логотипы, PATCH правил |
| Рабочая | `RUNNING` | `true` | Прогнозы, результаты, расчёт |
| Заморожена | `PAUSED` | `true` | Изменения только для чтения; безопасное удаление после grace-периода |
| Финальная | `FINISHED` | `true` | Только чтение; Поддержке (SUPPORT) разрешён пересчёт |

Матрица разрешённых операций: [`agent_docs/contracts/contest_lifecycle_flow.md`](../../agent_docs/contracts/contest_lifecycle_flow.md)

### Тур

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> ACTIVE : activate
    ACTIVE --> CLOSED : deadline / auto-close
    CLOSED --> CALCULATED : calculate
    CALCULATED --> PUBLISHED : publish
    CALCULATED --> CALCULATED : VOID match → recalculate
```

**Автозакрытие:** при каждом вызове API в рамках конкурса `auto_close_expired_rounds` переводит тур `ACTIVE → CLOSED`, когда `now >= deadline` (синхронно, по возможности в той же транзакции).

## Потоки запросов и данных

### Отправка прогноза (участник)

```mermaid
sequenceDiagram
    participant C as Client
    participant R as contest_ops router
    participant D as deps
    participant P as prediction_service
    participant DB as Database

    C->>R: POST .../rounds/{id}/predictions
    R->>D: JWT + ContestContext + auto-close
    D->>DB: close expired rounds if any
    R->>P: submit_batch(user, round, items)
    P->>DB: load round, participant, matches
    P->>P: guards: ACTIVE, deadline, ACCEPTED
    P->>DB: upsert all predictions (atomic)
    R-->>C: 200 saved_count
```

Отсутствующий прогноз = **отсутствие строки** (никогда не используйте `0` как признак «пусто»). Пакет должен покрывать все матчи тура.

### Расчёт и публикация (организатор)

```mermaid
sequenceDiagram
    participant S as Supervisor
    participant R as admin router
    participant SP as scoring_persistence
    participant E as scoring engine
    participant DB as Database

    S->>R: POST .../calculate
    R->>SP: calculate_round(round_id)
    SP->>DB: load matches, predictions, rules_json
    SP->>E: score_round(...)
    E-->>SP: UserRoundScore per user
    SP->>DB: write scores, transition CALCULATED
    S->>R: POST .../publish
    R->>DB: transition PUBLISHED
```

После публикации публичные GET-запросы лидерборда/результатов включают кэширование по ETag.

## Конвейер начисления очков

Правила **управляются данными** из `contests.rules_json`. Движок применяет фиксированный алгоритм, описанный в контракте начисления очков.

```mermaid
flowchart LR
    subgraph inputs [Inputs per round]
        M[Match results]
        PR[Predictions]
        RU[rules_json]
    end

    subgraph engine [src/scoring]
        SR[ScoringRules accessor]
        ER[engine.score_round]
        ST[standings.build_standings]
    end

    subgraph outputs [Outputs]
        SC[scores table]
        LB[Leaderboard JSON]
    end

    M --> ER
    PR --> ER
    RU --> SR --> ER
    ER -->|UserRoundScore| SP[scoring_persistence]
    SP --> SC
    SC --> ST
    ST --> LB
```

| Этап | Что происходит |
|-------|----------------|
| **Базовые очки** | На матч: одна категория — exact high, exact, diff+outcome, outcome или miss |
| **Бонус 1** | Множитель за уникальный точный прогноз |
| **Бонус 2** | Порог по количеству верных исходов в туре |
| **Бонус 3** | Место в туре по базовой сумме (+ опциональный дополнительный порог) |
| **Тай-брейк** | Сумма → количество точных → база без бонусов → количество диффов → ручное переопределение |
| **VOID** | Очки за матч обнуляются; бонусы пересчитываются для оставшихся матчей |

Сводка контракта: [`agent_docs/contracts/scoring_flow.md`](../../agent_docs/contracts/scoring_flow.md)  
Реализация и сохранение: [SCORING_LOGIC.md](SCORING_LOGIC.md)

## Безопасность и доступ

```mermaid
flowchart TB
    REQ[HTTP request]
    REQ --> AUTH{Bearer JWT?}
    AUTH -->|public GET| PUB[leaderboard, results, /contests/public]
    AUTH -->|valid| RBAC[RoleChecker + contest guards]
    RBAC --> USER[USER — own predictions]
    RBAC --> SUP[SUPERVISOR — admin ops]
    RBAC --> ADM[Support — recalc, lifecycle, all predictions pre-deadline]
```

| Механизм | Примечания |
|-----------|--------|
| Payload JWT | `{sub: user_id, role, exp}` |
| Процесс приглашения | Временный пароль → участник `PENDING` → смена пароля → `ACCEPTED` |
| Приватность прогнозов | До дедлайна: USER/SUPERVISOR видят только свои очки; Поддержка (SUPPORT) видит все |
| Защитные проверки конкурса | `PAUSED` / `FINISHED` блокируют изменяющие операции; `is_locked` блокирует CRUD настройки |

Таблицы RBAC: [API Guide — RBAC](API_GUIDE.md#role-based-access-control)

## Сквозные аспекты

| Аспект | Реализация |
|---------|------------------|
| Ошибки | `src/core/exceptions.py` + `error_handlers.py` → `{detail, code}` |
| Логирование | `LOG_LEVEL`, структурированный формат при запуске |
| HTTP-кэш | Публичный лидерборд/результаты: `Cache-Control` + ETag на основе состояния очков |
| Миграции | Alembic async; URL из `DATABASE_URL` |
| Начальная загрузка | `seed.py` + `bootstrap_users.py` — см. [BOOTSTRAP_USERS.md](../setup/BOOTSTRAP_USERS.md) |
| Тестовые данные | `load_test_data.py` + CSV по контракту — см. [CONFIG.md](../setup/CONFIG.md) |

## Дополнительные материалы

| Тема | Документ |
|-------|----------|
| Индекс справочников | [INDEX.md](../INDEX.md) |
| HTTP API, сервисы, эндпоинты | [API_GUIDE.md](API_GUIDE.md) |
| Таблицы, перечисления, миграции | [DB_REFERENCE.md](DB_REFERENCE.md) |
| Очки, бонусы, код движка | [SCORING_LOGIC.md](SCORING_LOGIC.md) |
| Переменные окружения, seed, загрузчик | [CONFIG.md](../setup/CONFIG.md) |
| OpenAPI (эталонные маршруты) | [`api_v1.yaml`](../../agent_docs/contracts/api_v1.yaml) |
| Контракт БД | [`db_schema.md`](../../agent_docs/contracts/db_schema.md) |
| Контракт начисления очков | [`scoring_flow.md`](../../agent_docs/contracts/scoring_flow.md) |
| Матрица жизненного цикла | [`contest_lifecycle_flow.md`](../../agent_docs/contracts/contest_lifecycle_flow.md) |
| Бизнес-правила (неизменяемые) | [`docs/01_tech_regulations.md`](../../docs/01_tech_regulations.md) |
| README проекта | [`README.md`](../../README.md) |
