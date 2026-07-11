# Конкурс прогнозов на футбол

Full-stack приложение: участники сдают прогнозы до дедлайна тура; организатор вводит результаты, система начисляет очки и публикует таблицы.

**Стек:** Python 3.12 · FastAPI · SQLAlchemy · Next.js · TypeScript · SQLite (dev) / PostgreSQL (prod)

## О конкурсе

**Суть:** участники угадывают исходы матчей до их начала. Очки — по точности прогноза. После тура — таблица тура и сводная по опубликованным турам.

**Типовая конфигурация** (на конкурс): ~30 туров, 8 матчей, 16 команд. Дедлайн прогнозов — до первого матча тура (настраивается в `rules_json`).

**Роли:**

| Роль | Кратко |
|------|--------|
| **Visitor** | Публичные лидерборды и результаты опубликованных туров |
| **User** | Прогнозы, профиль, контакты |
| **Supervisor** | Команды, туры, дедлайны, результаты, расчёт, публикация |
| **Support** | + пересчёт, жизненный цикл конкурса, создание организаторов |

Бизнес-спека (read-only): [`docs/01_tech_regulations.md`](docs/01_tech_regulations.md)

---

## Текущее состояние (2026-06)

| Слой | Статус | Прогресс |
|------|--------|----------|
| **Backend** (Stage 1) | API, scoring, lifecycle, multi-contest, auto-close дедлайна | [`agent_docs/progress/stage_1.md`](agent_docs/progress/stage_1.md) — до **1.16** |
| **Frontend** (Stage 2) | Auth, профиль, админка организатора (`/admin/*`) | [`agent_docs/progress/stage_2.md`](agent_docs/progress/stage_2.md) — до **2.3.5** |
| **Ручное QA** | Чек-лист супервайзера, dev-фикстура туров 1–11 | [SUPERVISOR_TESTING_SCENARIOS.md](manuals/testing/SUPERVISOR_TESTING_SCENARIOS.md) |

Актуальные темы последних итераций: старт конкурса и soft-delete, ДопТур, lazy auto-close тура по дедлайну, синхронизация UI «Дедлайн» / ввод результатов, UTC + display timezone для datetime-local.

---

## Быстрый старт

Подробно: **[manuals/setup/DEV_SETUP.md](manuals/setup/DEV_SETUP.md)**

```bash
uv sync
cp .env.example .env                    # SEED_SUPPORT_PASSWORD (support), SEED_SUPERVISOR_PASSWORD
cp frontend/.env.local.example frontend/.env.local   # API URL, Europe/Moscow display TZ
uv run python src/scripts/dev_setup.py --run   # БД + API (:8000) + UI (:3000)
```

- UI: `http://127.0.0.1:3000/` · API: `http://127.0.0.1:8000/docs` · health: `/health`
- Только серверы (без сброса БД): `uv run python src/scripts/dev_setup.py --run-only`
- Логины bootstrap: [BOOTSTRAP_USERS.md](manuals/setup/BOOTSTRAP_USERS.md)

### Тесты

```bash
uv run pytest tests/ --ignore=tests/manual -q
cd frontend && npm run test:unit && npm run lint && npm run type-check
```

---

## Архитектура (кратко)

```
Browser → Next.js (frontend/) → FastAPI (src/api/) → services/ → DB
                                              ↘ scoring/ (pure functions)
```

- API prefix: `/api/v1/contests/{contest_id}/…` (legacy shims без `contest_id` — deprecated)
- OpenAPI **v1.2.1**: [`agent_docs/contracts/api_v1.yaml`](agent_docs/contracts/api_v1.yaml)
- Жизненный цикл и guards: [`agent_docs/contracts/contest_lifecycle_flow.md`](agent_docs/contracts/contest_lifecycle_flow.md)
- UI статусы и связи страниц «Туры» / «Результаты»: [`agent_docs/contracts/admin_ui_status_matrix.md`](agent_docs/contracts/admin_ui_status_matrix.md)

Подробнее: [ARCHITECTURE.md](manuals/dev/ARCHITECTURE.md) · [API_GUIDE.md](manuals/dev/API_GUIDE.md) · [FRONTEND_REFERENCE.md](manuals/dev/FRONTEND_REFERENCE.md)

### Структура репозитория

```
football_prog/
├── main.py, config/settings.py
├── src/                    # Backend: api, services, scoring, scripts
├── frontend/               # Next.js UI (participant + /admin)
├── alembic/, tests/
├── manuals/                # Техдоки (INDEX.md): user/, setup/, testing/, dev/
├── agent_docs/contracts/   # Контракты API, БД, scoring, UI matrix
└── docs/                   # Продуктовые спеки (read-only)
```

---

## Документация

**Оглавление:** [manuals/INDEX.md](manuals/INDEX.md) — разделы `user/`, `setup/`, `testing/`, `dev/`

| Тема | Документ |
|------|----------|
| Инструкция участника | [USER_GUIDE.md](manuals/user/USER_GUIDE.md) |
| Инструкция организатора | [SUPERVISOR_GUIDE.md](manuals/user/SUPERVISOR_GUIDE.md) |
| Локальная разработка | [DEV_SETUP.md](manuals/setup/DEV_SETUP.md) |
| Настройки, env, datetime UTC/display | [CONFIG.md](manuals/setup/CONFIG.md) |
| HTTP API, RBAC, auto-close | [API_GUIDE.md](manuals/dev/API_GUIDE.md) |
| Статусы (API ↔ UI) | [STATUS_REFERENCE.md](manuals/dev/STATUS_REFERENCE.md) |
| Очки и бонусы | [SCORING_LOGIC.md](manuals/dev/SCORING_LOGIC.md) |
| БД и миграции | [DB_REFERENCE.md](manuals/dev/DB_REFERENCE.md) |
| Ручной QA организатора | [SUPERVISOR_TESTING_SCENARIOS.md](manuals/testing/SUPERVISOR_TESTING_SCENARIOS.md) |
| Frontend: маршруты, компоненты | [FRONTEND_REFERENCE.md](manuals/dev/FRONTEND_REFERENCE.md) |

**Контракты** (`agent_docs/contracts/`):

| Файл | Содержание |
|------|------------|
| [api_v1.yaml](agent_docs/contracts/api_v1.yaml) | OpenAPI |
| [db_schema.md](agent_docs/contracts/db_schema.md) | Схема БД |
| [contest_lifecycle_flow.md](agent_docs/contracts/contest_lifecycle_flow.md) | SETUP/RUNNING, туры, прогнозы, результаты |
| [frontend_api_integration.md](agent_docs/contracts/frontend_api_integration.md) | Auth, ошибки, timestamps |
| [admin_ui_status_matrix.md](agent_docs/contracts/admin_ui_status_matrix.md) | Туры ↔ Результаты ↔ очки ↔ видимость |
| [scoring_flow.md](agent_docs/contracts/scoring_flow.md) · [bonus_rules.md](agent_docs/contracts/bonus_rules.md) | Расчёт очков |

**Прогресс агентов:** [`agent_docs/progress/stage_1.md`](agent_docs/progress/stage_1.md) · [`agent_docs/progress/stage_2.md`](agent_docs/progress/stage_2.md)

**Продуктовые спеки** (не правятся из задач на код): [`docs/`](docs/)
