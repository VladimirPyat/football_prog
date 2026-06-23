# Конкурс прогнозов на футбол

Бэкенд-сервис конкурса прогнозов: участники сдают прогнозы счёта до дедлайна тура; после окончания матчей система начисляет очки и публикует таблицы.

## О конкурсе

Приложение принимает прогнозы участников и обрабатывает результаты матчей.

**Суть:** участники пытаются угадать исходы футбольных матчей до их начала. Очки начисляются в зависимости от точности прогноза. После завершения всех матчей тура система подсчитывает очки и формирует таблицу по туру и сводную по всем прошедшим турам.

**Типовая конфигурация** (настраивается для каждого конкурса):

- Формат в духе РПЛ: **30 туров**, **8 матчей** в туре, **16 команд**
- Приём прогнозов заканчивается в дедлайн, который задаёт организатор, до начала первого матча тура
- Опоздавший или не сдавший прогнозы участник получает за тур **ноль** очков
- После дедлайна таблица прогнозов становится доступна участникам
- Побеждает участник с наибольшим количеством очков по итогам всех туров

**Роли:**

| Роль | Кратко |
|------|--------|
| **Visitor** (посетитель) | Анонимный доступ: лидерборды и опубликованные результаты |
| **User** (участник) | Прогнозы, контакты в профиле |
| **Supervisor** (организатор) | Управление конкурсом: команды, туры, результаты, расчёт, публикация |
| **Admin** (администратор) | Полный доступ: пересчёт, жизненный цикл конкурса, создание организаторов |

Организатор может участвовать в конкурсе отдельным приглашённым аккаунтом. Полные бизнес-правила и сущности: [`docs/01_tech_regulations.md`](docs/01_tech_regulations.md) (неизменяемая спецификация).

---

## Обзор бэкенда

**Стек:** Python 3.12 · FastAPI · SQLAlchemy (async) · Alembic · JWT · SQLite (dev) / PostgreSQL (целевая СУБД)

**Контракт API:** OpenAPI **v1.2.0** — [`agent_docs/contracts/api_v1.yaml`](agent_docs/contracts/api_v1.yaml)  
**Контракт БД:** [`agent_docs/contracts/db_schema.md`](agent_docs/contracts/db_schema.md)

Основной префикс маршрутов: `/api/v1/contests/{contest_id}/…`. Устаревшие пути без `contest_id` — deprecated-обёртки над конкурсом по умолчанию.

### Что делает бэкенд

1. **Жизненный цикл конкурса** — создание, фаза настройки (команды, участники, логотипы), активация первого тура → конкурс блокируется и переходит в RUNNING
2. **Прогнозы** — пакетная сдача на тур; приватность до/после дедлайна; принятие приглашения при смене пароля
3. **Начисление очков** — расчёт по результатам матчей; бонусы и тай-брейки; агрегация общей таблицы
4. **Лидерборды** — таблицы тура и общая: место, бонусы, колонки счётчиков (`count_exact_high`, `count_exact`, `count_diff`, `count_outcome`)
5. **Discovery** — публичный список идущих конкурсов, «мои конкурсы», контакты профиля
6. **Статика** — логотип по умолчанию и загруженные организатором логотипы команд по `/static/`

Подробности: [API Guide](manuals/API_GUIDE.md) · [Scoring Logic](manuals/SCORING_LOGIC.md) · [DB Reference](manuals/DB_REFERENCE.md)

### Структура проекта

```
football_prog/
├── main.py                 # Точка входа FastAPI, роутеры, статика
├── config/
│   └── settings.py         # Настройки из env (БД, JWT, загрузки, …)
├── alembic/                # Миграции БД
├── src/
│   ├── api/v1/             # HTTP-роутеры (auth, contests, predictions, admin, …)
│   ├── api/handlers/       # Общие сборщики ответов (leaderboard, predictions)
│   ├── core/               # Безопасность, исключения, логирование
│   ├── database/           # Модели SQLAlchemy и async-движок
│   ├── schemas/            # Pydantic-схемы запросов/ответов
│   ├── scoring/            # Чистый движок начисления очков и standings
│   ├── services/           # Слой бизнес-логики
│   └── scripts/            # seed, bootstrap_users, load_test_data
├── static/assets/          # Логотип команды по умолчанию
├── uploads/teams/          # Загруженные логотипы (gitignored)
├── tests/                  # unit, integration, api, scoring
├── manuals/                # Техническая документация для разработчиков
├── agent_docs/contracts/   # Авторитетные контракты API и БД (read-only)
└── docs/                   # Неизменяемые продуктовые и бизнес-спеки (read-only)
```

### Архитектура (крупными мазками)

```
Client → FastAPI → JWT / RBAC → Router → Service → SQLAlchemy → DB
                              ↘ Scoring engine (чистые функции)
```

Роутеры тонкие; правила — в `src/services/`. Доменные ошибки → JSON `{detail, code}`. См. [API Guide — Architecture](manuals/API_GUIDE.md#architecture-updated).

---

## Быстрый старт

Полная инструкция (бэкенд + фронт, тестовые логины, troubleshooting): **[manuals/DEV_SETUP.md](manuals/DEV_SETUP.md)**

```bash
uv sync
cp .env.example .env          # задать SEED_ADMIN_PASSWORD, SEED_SUPERVISOR_PASSWORD
uv run python src/scripts/dev_setup.py --run   # БД + API (:8000) + UI (:3000)
```

- UI: `http://127.0.0.1:3000/` · API health: `http://127.0.0.1:8000/health` · Swagger: `http://127.0.0.1:8000/docs`
- Только перезапуск серверов (без сброса БД): `uv run python src/scripts/dev_setup.py --run-only`
- Минимальный ручной путь (без loader): см. `dev_setup.py --minimal` в [DEV_SETUP.md](manuals/DEV_SETUP.md)

Bootstrap и переменные окружения: [BOOTSTRAP_USERS.md](manuals/BOOTSTRAP_USERS.md) · [CONFIG.md](manuals/CONFIG.md)

### Тесты

```bash
uv run pytest tests/ --ignore=tests/manual -q
```

---

## Документация

| Тема | Документ |
|------|----------|
| **Оглавление** | [manuals/README.md](manuals/README.md) |
| **Локальная разработка (API + UI)** | [manuals/DEV_SETUP.md](manuals/DEV_SETUP.md) |
| Общая архитектура, dataflow | [manuals/ARCHITECTURE.md](manuals/ARCHITECTURE.md) |
| HTTP API, auth, RBAC, lifecycle | [manuals/API_GUIDE.md](manuals/API_GUIDE.md) |
| Модели БД и миграции | [manuals/DB_REFERENCE.md](manuals/DB_REFERENCE.md) |
| Очки, бонусы, тай-брейки | [manuals/SCORING_LOGIC.md](manuals/SCORING_LOGIC.md) |
| Настройки, env, seed и loader | [manuals/CONFIG.md](manuals/CONFIG.md) |
| Первичный ADMIN/SUPERVISOR | [manuals/BOOTSTRAP_USERS.md](manuals/BOOTSTRAP_USERS.md) |
| Политика ошибок и логирования | [manuals/ERROR_LOGGING.md](manuals/ERROR_LOGGING.md) |

**Контракты** (авторитетный источник формы API/БД):

- [api_v1.yaml](agent_docs/contracts/api_v1.yaml) — OpenAPI v1.2.0
- [db_schema.md](agent_docs/contracts/db_schema.md) — описание таблиц
- [contest_lifecycle_flow.md](agent_docs/contracts/contest_lifecycle_flow.md) — машины состояний

**Продуктовые спеки** (неизменяемые, не правятся из задач на код): [`docs/`](docs/)
