# Техническая документация

Человекочитаемая документация проекта «Конкурс прогнозов на футбол».

## Запуск и настройка (`setup/`)

| Документ | Тема |
|----------|------|
| [DEV_SETUP.md](setup/DEV_SETUP.md) | **Локальная разработка:** зависимости, bootstrap-скрипт, API + frontend, тестовые логины |
| [DEPLOYMENT.md](setup/DEPLOYMENT.md) | **Деплой на сервер:** PostgreSQL, URL, CORS, разделение env, первый запуск |
| [CONFIG.md](setup/CONFIG.md) | Настройки, переменные окружения, seed, contest defaults |
| [BOOTSTRAP_USERS.md](setup/BOOTSTRAP_USERS.md) | Первичные пользователи Support / SUPERVISOR через `.env` + bootstrap-скрипт |

## Тестирование (`testing/`)

| Документ | Тема |
|----------|------|
| [SUPERVISOR_TESTING_SCENARIOS.md](testing/SUPERVISOR_TESTING_SCENARIOS.md) | **Ручное QA организатора:** чек-лист по маршрутам, фикстура, известные пробелы |
| [MANUAL_SCORING_VERIFICATION.md](testing/MANUAL_SCORING_VERIFICATION.md) | Sign-off Stage 1: ручная проверка scoring + CANARY |

## Архитектура и справочники (`dev/`)

| Документ | Тема |
|----------|------|
| [ARCHITECTURE.md](dev/ARCHITECTURE.md) | Обзор системы, слои, потоки данных, state machines |
| [API_GUIDE.md](dev/API_GUIDE.md) | FastAPI: маршруты, auth, RBAC, жизненный цикл конкурса |
| [DB_REFERENCE.md](dev/DB_REFERENCE.md) | SQLAlchemy-модели, enums, ограничения, миграции |
| [SCORING_LOGIC.md](dev/SCORING_LOGIC.md) | Очки, бонусы, tie-breakers, правила валидации |
| [FRONTEND_REFERENCE.md](dev/FRONTEND_REFERENCE.md) | **Карта фронтенда:** маршруты, компоненты, редактируемые строки UI |
| [STATUS_REFERENCE.md](dev/STATUS_REFERENCE.md) | **Статусы:** конкурс, тур, матч — смысл, переходы, где в коде; API vs подписи UI |

## Контракты (вне `manuals/`)

| Документ | Тема |
|----------|------|
| [ERROR_LOGGING.md](../agent_docs/contracts/ERROR_LOGGING.md) | Политика ошибок и логирования |
| [api_v1.yaml](../agent_docs/contracts/api_v1.yaml) | OpenAPI-контракт API |

## Терминология

| Термин | Значение |
|--------|----------|
| **Supervisor (организатор)** | `users.role=SUPERVISOR`; настройка конкурса, туры, результаты. UI на `/admin/*` (историческое имя пути). |
| **Support (техподдержка)** | `users.role=SUPPORT`; lifecycle, restore, recalculate, создание организаторов. API `/api/v1/admin/users/*`. |
| **Путь `/admin/…`** | Рабочая область организатора — **не переименовывается**; используют и SUPERVISOR, и Support. |

См. также [API_GUIDE.md — Role-Based Access Control](dev/API_GUIDE.md#role-based-access-control).

## Покрытие этапов

| Этап | Документы |
|------|-----------|
| **0** — БД и конфигурация | `DB_REFERENCE.md`, `CONFIG.md`, `SCORING_LOGIC.md` |
| **1.1** — Scoring engine | `SCORING_LOGIC.md` |
| **1.2** — Сервисы и loader | `API_GUIDE.md`, `CONFIG.md` |
| **1.3** — HTTP API | `API_GUIDE.md`, `CONFIG.md`, `SCORING_LOGIC.md` |
| **1.4** — Multi-contest + setup | `DB_REFERENCE.md`, `API_GUIDE.md` |
| **1.4** — E2E + ручной sign-off | `MANUAL_SCORING_VERIFICATION.md` |
| **1.5** — Ошибки и логирование | `ERROR_LOGGING.md` |
| **1.6** — Bootstrap и API организаторов | `BOOTSTRAP_USERS.md` |
| **1.8** — Discovery и контакты | `API_GUIDE.md` |
| **1.12** — Invite без SMTP | `DEV_SETUP.md` |
| **1.14** — Dev-фикстура | `DEV_SETUP.md`, `STATUS_REFERENCE.md` |
| **2.3.x** — Видимость туров, ACTIVE UX | `API_GUIDE.md`, `STATUS_REFERENCE.md`, `SUPERVISOR_TESTING_SCENARIOS.md` |
| **2.x** — Frontend | `DEV_SETUP.md`, `FRONTEND_REFERENCE.md` |
| **2.x** — Деплой | `DEPLOYMENT.md` |

Последняя синхронизация: реорганизация `manuals/` (setup / testing / dev), перевод на русский, `README.md` → `INDEX.md`.
