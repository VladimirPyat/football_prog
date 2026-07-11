# Руководство по API

Приложение FastAPI, аутентификация, RBAC, HTTP-эндпоинты и интеграция со слоем сервисов.

## Содержание

- [Статус реализации](#implementation-status)
- [Запуск приложения](#running-the-application)
- [Архитектура](#architecture)
- [Аутентификация](#authentication)
- [Установка пароля и invite-ссылки (Stage 1.12)](#password-setup--invite-links-stage-112)
- [Контроль доступа на основе ролей](#role-based-access-control)
- [Multi-Contest API](#multi-contest-api)
- [Обнаружение конкурсов и контакты пользователя](#contest-discovery--user-contacts)
- [Управление пользователями (техподдержка)](#admin-user-management)
- [Жизненный цикл конкурса и неизменяемость](#contest-lifecycle--immutability)
- [Слой сервисов](#service-layer)
- [Справочник эндпоинтов](#endpoints-reference)
- [HTTP-кэширование](#http-caching)
- [Формат ответа об ошибке](#error-response-format)
- [Логирование](#logging)
- [Связанная документация](#related-documentation)

## Статус реализации [UPDATED] {#implementation-status}

| Компонент | Статус | Путь |
|-----------|--------|------|
| Round service (машина статусов + правило 24 ч) | ✅ Stage 1.2 | `src/services/round_service.py` |
| Match service (результаты + VOID) | ✅ Stage 1.2 | `src/services/match_service.py` |
| Prediction service (пакетная отправка + видимость) | ✅ Stage 1.2 | `src/services/prediction_service.py` |
| Scoring persistence (calculate/recalculate) | ✅ Stage 1.2 | `src/services/scoring_persistence.py` |
| Contest lifecycle (пауза/завершение/защита удаления) | ✅ Stage 1.3 | `src/services/contest_lifecycle_service.py` |
| Агрегация leaderboard + ETag | ✅ Stage 1.3 | `src/services/leaderboard_service.py` |
| Публичные LB/результаты только для PUBLISHED + предпросмотр CALCULATED для staff | ✅ Stage 2.3.1 | `leaderboard_service`, `contest_ops.py`, `admin_misc.py` [UPDATED] |
| Размещение дедлайна тура + блокировка изменений за 24 ч | ✅ Stage 2.3.1 | `round_service.py`, `contest_ops.py`, `admin_rounds.py` [UPDATED] |
| Редактирование результата на CALCULATED + авто-пересчёт | ✅ Stage 2.3.2 | `match_service.py` → `set_result`, `recalculate_round` [NEW] |
| Multi-contest API + фаза setup | ✅ Stage 1.4 | `src/api/v1/contests.py`, `contest_ops.py`, … |
| Приложение FastAPI | ✅ Stage 1.3 | `main.py` |
| JWT-аутентификация (bcrypt + python-jose) | ✅ Stage 1.3 | `src/core/security.py`, `src/api/v1/auth.py` |
| Pydantic-схемы запросов/ответов | ✅ Stage 1.3 | `src/schemas/` |
| Контроль доступа на основе ролей | ✅ Stage 1.3 | `src/api/deps.py` — `RoleChecker` |
| Типизированные ошибки + централизованные обработчики | ✅ Stage 1.5 | `src/core/exceptions.py`, `src/api/error_handlers.py` |
| Структурированное логирование | ✅ Stage 1.5 | `src/core/logging_config.py`, `LOG_LEVEL` |
| Заглушка алерта администратора | ✅ Stage 1.5 | `src/services/notification_service.py` |
| Общие HTTP-обработчики (DRY) | ✅ Stage 1.5 | `src/api/handlers/` |
| API создания организатора | ✅ Stage 1.6 | `src/api/v1/admin_users.py`, `src/services/user_admin_service.py` |
| CLI bootstrap пользователей | ✅ Stage 1.6 | `src/scripts/bootstrap_users.py`, `.env.example` |
| Обнаружение конкурсов и контакты пользователя | ✅ Stage 1.8 | `src/api/v1/me.py`, `contest_discovery_service`, `contact_service` |
| Столбцы count в leaderboard + принятие invite | ✅ Stage 1.7 | `leaderboard_service`, `participant_service`, `prediction_service` |
| Загрузка логотипов команд и статические ресурсы | ✅ Stage 1.9 | `team_logo_service`, `contest_teams.py`, static routes в `main.py` |
| Auth setup links + принятие invite по токену | ✅ Stage 1.12 | `setup_tokens.py`, `auth_setup_service.py`, `auth.py` |
| Очистка неподтверждённых участников при старте конкурса | ✅ Stage 1.12 | `contest_setup_service.purge_unconfirmed_participants`, `purge_before_first_activation` |
| Режим обучения организатора + восстановление конкурса | ✅ Stage 1.12 | `contest_restore_service.py`, restore route в `contests.py` |
| OpenAPI-контракт | 📋 Авторитетная спецификация | `agent_docs/contracts/api_v1.yaml` (v1.2.1) |
| HTTP integration tests | ✅ Stage 1.6 | `tests/api/` — loader DB + httpx ASGI |

**До → После (Stage 1.6):** Техподдержка может создавать глобальные аккаунты `SUPERVISOR` (организатор) через `POST /admin/users/supervisor`. Начальные учётные записи техподдержки/организатора на пустой БД — через `bootstrap_users.py` + переменные окружения `SEED_*` (см. [BOOTSTRAP_USERS.md](../setup/BOOTSTRAP_USERS.md)).

## Запуск приложения [NEW] {#running-the-application}

```bash
uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Проверка здоровья: `GET /health` → `{"status": "ok"}`  
Интерактивная документация: `http://localhost:8000/docs`

## Архитектура [UPDATED] {#architecture}

```
Client → FastAPI (Uvicorn) → CORS → logging
       → RoleChecker / auth deps → Pydantic validation
       → Router (thin) → Services → SQLAlchemy async
       → AppError → error_handlers → JSON {detail, code}
```

| Слой | Путь | Назначение |
|------|------|------------|
| Точка входа | `main.py` | Фабрика приложения, CORS, `setup_logging()`, `register_error_handlers()`, роутеры под `/api/v1`, mount статических ресурсов [UPDATED] |
| Маппинг ошибок | `src/api/error_handlers.py` | `AppError` → HTTP JSON; необработанные → 500 + `notify_admin()` |
| Исключения | `src/core/exceptions.py` | Иерархия `AppError` (`NotFoundError`, `ValidationError`, `ContestRuleError`, …) |
| Логирование | `src/core/logging_config.py` | Формат root logger; уровень из `LOG_LEVEL` |
| Зависимости | `src/api/deps.py` | Сессия БД, разрешение JWT-пользователя, RBAC, контекст конкурса, **batch auto-close hook** [UPDATED 1.16] |
| Роутеры | `src/api/v1/*.py` | Только HTTP-маппинг — делегирует сервисам или `src/api/handlers/` |
| Admin users | `src/api/v1/admin_users.py` | `POST /admin/users/supervisor` (только техподдержка) [NEW] |
| Общие обработчики | `src/api/handlers/` | DRY-сборщики для predictions view и leaderboard/results |
| Схемы | `src/schemas/*.py` | Pydantic-модели запросов/ответов |
| Безопасность | `src/core/security.py` | bcrypt hash/verify пароля, JWT encode/decode |
| Сервисы | `src/services/` | Бизнес-логика; выбрасывает `AppError`, никогда `HTTPException` |
| Алерты | `src/services/notification_service.py` | Заглушка `notify_admin()` для критических сбоев [NEW] |

## Аутентификация [UPDATED] {#authentication}

JWT bearer-токены. Тело токена: `{sub: user_id, role, exp}`.

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `POST` | `/api/v1/auth/login` | None | Проверка учётных данных → `{access_token, token_type, is_temp_password}` |
| `POST` | `/api/v1/auth/change-password` | Bearer | Смена пароля; сбрасывает `is_temp_password`; принимает все ожидающие invite конкурса (`PENDING` → `ACCEPTED`) |
| `GET` | `/api/v1/auth/me` | Bearer | Профиль текущего пользователя |
| `GET` | `/api/v1/auth/me/contacts` | Bearer | Контакты профиля (email, VK, TG, переключатель уведомлений) |
| `PATCH` | `/api/v1/auth/me/contacts` | Bearer | Частичное обновление / upsert контактов |

**До → После (Stage 1.12):** При `enforce_password_setup=true` (по умолчанию) вход с временным паролем возвращает **403** `{detail, code: "PASSWORD_SETUP_REQUIRED"}` — пользователь должен завершить `/auth/setup` по подписанной ссылке (см. [Установка пароля и invite-ссылки](#password-setup--invite-links-stage-112)). При `enforce_password_setup=false` сохраняется legacy-путь: вход с временным паролем + `/auth/change-password`.

**Поток с временным паролем (legacy / `enforce_password_setup=false`):** Пока `is_temp_password=true`, разрешены без ограничений `/auth/change-password`, `/auth/me` и `/auth/me/contacts` (GET/PATCH). `POST .../predictions` возвращает `403` с `code=PARTICIPANT_NOT_ACCEPTED`, пока пользователь не сменит временный пароль (что также переводит `contest_participants.status` в `ACCEPTED`).

Неверные учётные данные → `401` (`Неверный логин или пароль`). Недействительный/просроченный токен → `401`. Ответы auth/RBAC из `deps.py` содержат только русский `detail` (без поля `code`); доменные ошибки из сервисов включают `code`.

Конфигурация: [CONFIG.md — значения по умолчанию приложения](../setup/CONFIG.md#application-defaults-configsettingspy) (не корневой `.env`).

## Установка пароля и invite-ссылки (Stage 1.12) [NEW] {#password-setup--invite-links-stage-112}

Подписанные JWT-токены (`purpose: setup_password`) обеспечивают принятие invite и сброс пароля без SMTP.

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/api/v1/auth/setup-preview?token=…` | None | Предпросмотр ссылки: `{login, mode, already_completed}` |
| `POST` | `/api/v1/auth/complete-setup` | None | Идемпотентное принятие + опциональная установка пароля `{token, new_password?}` |
| `POST` | `/api/v1/auth/request-password-reset` | None | Всегда **200**; перевыпускает временный пароль, если email известен |

**Значения `mode`** (из `setup-preview`, управляются `ENFORCE_PASSWORD_SETUP`):

| `enforce_password_setup` | `mode` | Поведение UI |
|--------------------------|--------|--------------|
| `true` | `password_form` | Пользователь должен передать `new_password` в `complete-setup` |
| `false` | `confirm_only` | Только подтверждение участия; вход с временным паролем из письма |

**Ответ invite** (`POST /contests/{id}/participants`):

```json
{
  "user_id": 42,
  "login": "ivanov",
  "temp_password": "…",
  "status": "PENDING",
  "setup_url": "http://127.0.0.1:3000/auth/setup?token=…"
}
```

Базовый URL ссылки и TTL токена берутся из **`config/settings.py`** (`frontend_base_url`, `setup_token_expire_hours`). Имена env `FRONTEND_BASE_URL` / `SETUP_TOKEN_EXPIRE_HOURS` — для переопределения при деплое (Kubernetes, CI shell) — **не** для корневого `.env` (только секреты). Значения по умолчанию: `http://127.0.0.1:3000`, 72 ч. Реализация: `src/core/setup_tokens.py`, `src/services/auth_setup_service.py`.

**Путь принятия:** `complete-setup` с `contest_id` в токене устанавливает `contest_participants.status` в `ACCEPTED`. Успех **не** выдаёт JWT автоматически — frontend перенаправляет на login.

Dev workflow без SMTP: [DEV_SETUP.md — Новый конкурс: подтверждение участников](../setup/DEV_SETUP.md#new-contest-confirm-participants-without-email-stage-112).

## Контроль доступа на основе ролей [NEW] {#role-based-access-control}

Зависимость `RoleChecker(*roles)` в `src/api/deps.py`.

| Роль | Возможности |
|------|-------------|
| **Visitor** (без токена) | Публичные GET: список туров; leaderboard и результаты тура/глобальные **только для туров `PUBLISHED`** [UPDATED]; **`GET /contests/public`** (конкурсы RUNNING) |
| **USER** | Чтение/запись собственных прогнозов; **`GET /me/contests`** (только зачисленные конкурсы); LB/результаты тура с той же видимостью, что у Visitor (только `PUBLISHED`) |
| **SUPERVISOR** (организатор) | Round/match/result/VOID, calculate, publish, чтение настроек конкурса; **та же приватность прогнозов до дедлайна, что у USER** (только свои очки); предпросмотр LB/результатов тура для туров **`CALCULATED`** при аутентификации [UPDATED] |
| **ADMIN** | **Техподдержка (технический персонал)** — все действия организатора + recalculate, жизненный цикл конкурса, исключительный tie-break, безопасное удаление, **создание организаторов** (`POST /admin/users/supervisor`); **единственная роль, которая может видеть все прогнозы до дедлайна** (диагностика) |

**Защита по статусу конкурса:** Когда `contests.status ∈ {PAUSED, FINISHED}` для целевого конкурса, все мутирующие операции round/match/prediction возвращают `403`. Публичные GET остаются разрешёнными.

### Организатор и участник (один человек) [NEW] {#organizer-vs-participant-same-person}

Система разделяет два понятия:

| Понятие | Хранение | Смысл |
|---------|----------|-------|
| **Глобальная роль** | `users.role` | Одно значение на логин: `USER`, `SUPERVISOR` или `ADMIN` (техподдержка) |
| **Членство в конкурсе** | `contest_participants` | Участвует ли этот логин в данном конкурсе (`PENDING` / `ACCEPTED`) |

Организатор (`SUPERVISOR`) **может** также отправлять прогнозы и появляться в leaderboard. В бизнес-терминах **нет** правила, запрещающего это, но продуктовая модель предполагает **отдельные логины** для двух «шляп»:

| Потребность | Рекомендуемый подход |
|-------------|----------------------|
| Вести конкурс (команды, туры, результаты, calculate) | Аккаунт `SUPERVISOR` (организатор) — `bootstrap_users.py`, `POST /admin/users/supervisor` или UI организатора (`/admin/*`) |
| Играть как участник | **Аккаунт `USER`** — invite через `POST /contests/{id}/participants`, как у любого другого игрока |

**Почему не один логин для обоих?**

1. **Единая глобальная роль** — `users.role` не может быть одновременно `USER` и `SUPERVISOR`. Invite flow всегда создаёт нового `USER`; bootstrap и API организатора создают `SUPERVISOR` без зачисления в `contest_participants`.
2. **Приватность прогнозов** — до дедлайна тура `USER` и `SUPERVISOR` видят только свои очки прогнозов; остальные отображаются как «отправлено без деталей». Только **техподдержка** обходит этот фильтр (`prediction_service.visible_predictions`). У организатора нет «god mode» для прогнозов до дедлайна.
3. **Маршрутизация UI/API** — организаторы выбирают конкурсы через `GET /contests`; игроки — через `GET /me/contests`. Два аккаунта сохраняют потоки понятными.

**Что организатор может без участия в игре:** управлять setup и scoring, публиковать результаты, и (только техподдержка) устанавливать `exceptional_tiebreak_points` при равенстве в таблице — для этого **не** нужна строка участника.

**Операционный паттерн:** один человек, два логина (например, `ivan_org` / `ivan_player`). Пригласите email игрока через обычный participant flow; логин организатора используйте только для back-office.

> **Не поддерживается:** назначение «роли организатора» на уровне конкурса или dual-role на одном аккаунте. Ручная вставка в `contest_participants` для пользователя `SUPERVISOR` возможна на уровне БД, но не рекомендуется (запутанный UX; для игры используйте отдельный invite `USER`).

## Multi-Contest API [NEW] {#multi-contest-api}

Stage 1.4 вводит маршруты с областью конкурса под `/api/v1/contests/{contest_id}/…`. Legacy-пути 1.3 (без `contest_id`) остаются как **deprecated shims**, разрешающие конкурс по умолчанию (`resolve_default_contest_id`).

### Управление конкурсом (SUPERVISOR+ / техподдержка)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| `GET` | `/contests` | SUPERVISOR+ | Список активных конкурсов (`deleted_at IS NULL`) |
| `GET` | `/contests/deleted` | Техподдержка | Мягко удалённые конкурсы с флагом `restore_available` |
| `POST` | `/contests` | SUPERVISOR+ | Создание конкурса (фаза setup) |
| `GET` | `/contests/{id}` | SUPERVISOR+ | Детали конкурса |
| `PATCH` | `/contests/{id}` | SUPERVISOR+ | Обновление настроек (заблокировано при `is_locked`) |
| `POST` | `/contests/{id}/start` | SUPERVISOR+ | DRAFT → RUNNING, `is_locked=true`; очищает неподтверждённых участников PENDING [UPDATED Stage 1.15] |
| `POST` | `/contests/{id}/pause` | SUPERVISOR+ | RUNNING → PAUSED |
| `POST` | `/contests/{id}/resume` | SUPERVISOR+ | PAUSED → RUNNING |
| `POST` | `/contests/{id}/finish` | Техподдержка; SUPERVISOR при `supervisor_training_mode=true` | RUNNING\|PAUSED → FINISHED |
| `DELETE` | `/contests/{id}` | SUPERVISOR+ | Мягкое удаление: снимок + очистка данных + установка `deleted_at`; DRAFT мгновенно, PAUSED после grace; body `{confirm: "DELETE"}` → `{status: "DELETED"}` |
| `POST` | `/contests/{id}/restore` | Техподдержка | Replay snapshot в окне восстановления; сбрасывает `deleted_at` |

### Фаза setup (SUPERVISOR+)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET/POST/PATCH/DELETE` | `/contests/{id}/teams` | Team CRUD |
| `POST` | `/contests/{id}/teams/{team_id}/logo` | Multipart загрузка логотипа (PNG/JPEG/GIF, max 2 MiB; только SETUP) |
| `GET/POST/DELETE` | `/contests/{id}/participants` | Invite/список/удаление участников |
| `PUT` | `/contests/{id}/participants/{user_id}/exceptional-tiebreak` | Tie-break на уровне конкурса (техподдержка) |

### Операции конкурса

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/contests/{id}/rounds` | Public | Список туров |
| `GET/POST` | `/contests/{id}/rounds/{rid}/predictions` | USER+ | Predictions view / пакетное сохранение |
| `GET` | `/contests/{id}/rounds/{rid}/leaderboard` | Public (optional Bearer) | Таблица тура; видимость по статусу тура + роли зрителя [UPDATED] |
| `GET` | `/contests/{id}/rounds/{rid}/results` | Public (optional Bearer) | Результаты + очки; те же правила видимости, что у leaderboard тура [UPDATED] |
| `GET` | `/contests/{id}/leaderboard` | Public | Глобальная таблица — агрегирует **только туры `PUBLISHED`** [UPDATED] |
| `POST/PATCH/…` | `/contests/{id}/admin/rounds`, `/admin/matches/…` | SUPERVISOR+ | Round/match admin (та же семантика, что у legacy) |
| `POST` | `/contests/{id}/admin/recalculate` | Техподдержка | Пересчёт всех туров CALCULATED |

**Поля строки leaderboard (Stage 1.7) [UPDATED]:** Каждая запись включает столбцы count tie-break из сохранённых scores / агрегатов `StandingRow`:

| Поле | Смысл |
|------|-------|
| `count_exact_high` | Точный счёт с высоким весом tie-break |
| `count_exact` | Точный счёт (стандартный) |
| `count_diff` | Верная разница мячей |
| `count_outcome` | Только верный исход |

Таблица тура читает столбцы `scores` тура; глобальная таблица использует суммы `StandingRow` по турам (тот же источник, что и tie-breakers ранга).

**Видимость leaderboard/результатов тура (Stage 2.3.1) [UPDATED]:** Эндпоинты принимают опциональный Bearer token (`get_optional_user`). `viewer_role` управляет `_allowed_round_statuses` в `leaderboard_service.py`:

| Зритель | Возвращаемые статусы тура | HTTP при блокировке |
|---------|---------------------------|---------------------|
| Без токена / `USER` | Только `PUBLISHED` | `403` `RESULTS_NOT_AVAILABLE` |
| `SUPERVISOR` / техподдержка | `CALCULATED`, `PUBLISHED` | `403` `RESULTS_NOT_AVAILABLE` |

Глобальная таблица (`GET …/leaderboard`) суммирует очки **только из туров `PUBLISHED`** — туры предпросмотра `CALCULATED` исключены даже для staff. Frontend должен проверять [STATUS_REFERENCE.md](STATUS_REFERENCE.md) §2.3 перед вызовом публичных LB/results для туров не-`PUBLISHED`.

**Матрица результатов тура (Stage 1.17) [UPDATED]:** `GET …/rounds/{rid}/results` возвращает строки `results[]` с базовыми очками за матч для публичной матрицы:

| Поле | Смысл |
|------|-------|
| `results[].points[]` | Один `{ match_id, base_points }` на элемент в top-level `matches[]`, **в том же порядке** |
| `base_points` | Целое `0`–`16` из scoring engine; `null`, если пользователь не прогнозировал или матч не scorable (`VOID`, `CANCELED`, не завершён) |
| `total_without_bonus3` | Сохранённый агрегат (base + bonus1 + bonus2) — столбец «Итого без бон.» |
| `total` | Сохранённый `total_with_bonus3` (включает bonus3) |

Ячейки за матч используют **только базовые очки матча** — не `bonus1_points` на ячейку. Бонусы тура `bonus1` / `bonus2` / `bonus3` остаются на строке. Значения пересчитываются при чтении через `compute_round_user_scores()`; итоги строк — из сохранённых `scores`.

**Логотипы команд (Stage 1.9) [UPDATED]:** `TeamOut.logo_url` никогда не `null` в JSON — когда `teams.logo_url` не задан, API возвращает `DEFAULT_TEAM_LOGO_URL` (по умолчанию `/static/assets/default-team-logo.jpg`). Загруженные файлы хранятся в `uploads/teams/{contest_id}/{team_id}.jpg` и отдаются по `{STATIC_URL_PREFIX}/teams/{contest_id}/{team_id}.jpg`. Изображения обрезаются по центру и масштабируются до `TEAM_LOGO_TARGET_PX` (по умолчанию 64×64). Сброс кастомного логотипа: `PATCH .../teams/{id}` с `"logo_url": null`.

| Статический путь | Механизм отдачи | Содержимое |
|------------------|-----------------|------------|
| `/static/assets/*` | `StaticFiles` mount на `static/assets/` | Встроенные ресурсы только для чтения (логотип команды по умолчанию) |
| `/static/teams/*` | Динамический `FileResponse` route в `main.py` (защита от path traversal) | Загруженные организатором логотипы из `uploads/teams/` |

Зависимость `ContestContext` проверяет существование `contest_id` (404, если нет).

## Обнаружение конкурсов и контакты пользователя [NEW] {#contest-discovery--user-contacts}

Stage 1.8 закрывает frontend blockers B1–B3 для Stage 2.1 (главная Visitor + выбор конкурса User + контакты профиля).

### Список конкурсов пользователя (B1)

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/me/contests` | Bearer (любая роль) | Конкурсы, где у пользователя есть строка `contest_participants` |

Элементы ответа включают `participant_status` (`PENDING` \| `ACCEPTED`), глобальную `role` (из `users.role`), `status` конкурса и опциональный `slug`. Сортировка по имени конкурса. Организаторы без зачисления используют `GET /contests` (SUPERVISOR+), а не этот эндпоинт.

### Публичное обнаружение (B2)

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/contests/public` | None | Только конкурсы RUNNING (id, name, status, slug) |

Маршрут регистрируется **до** `/contests/{contest_id}`, чтобы избежать захвата пути. Возвращает `Cache-Control` (тот же паттерн, что у других публичных GET). PAUSED и FINISHED конкурсы исключены по замыслу.

### Контакты пользователя (B3)

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/auth/me/contacts` | Bearer | Чтение контактов; значения по умолчанию, если строки нет |
| `PATCH` | `/auth/me/contacts` | Bearer | Частичное обновление (upsert); пустая строка очищает email |

Разрешено при `is_temp_password=true`. Invite flow (`POST /contests/{id}/participants`) предзаполняет `email` в строке `contacts` нового пользователя.

## Управление пользователями (техподдержка) [UPDATED] {#admin-user-management}

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| `POST` | `/admin/users/supervisor` | Техподдержка | Создание глобального организатора конкурса (`users.role = SUPERVISOR`) |

**Запрос** (`CreateSupervisorRequest`):

```json
{
  "login": "org1",
  "password": "initial-password",
  "first_name": "Ivan",
  "last_name": "Organizer",
  "is_temp_password": false
}
```

**Ответ:** `{ "user": { "id", "login", "role": "SUPERVISOR", "first_name", "last_name", "is_temp_password" } }`

| Условие | HTTP | `code` |
|---------|------|--------|
| Успех | 200 | — |
| Дубликат login | 400 | `VALIDATION_ERROR` |
| Не техподдержка | 403 | (RBAC, без `code`) |
| Невалидное body | 422 | (Pydantic) |

**Не** зачисляет нового пользователя автоматически в `contest_participants` — организатор это глобальная роль, а не игрок.

**Первый деплой:** используйте CLI один раз на пустую БД — [BOOTSTRAP_USERS.md](../setup/BOOTSTRAP_USERS.md). Пользователи сохраняются в БД; bootstrap не запускается при каждом рестарте API.

### `user_admin_service.py` [NEW]

```python
async def create_supervisor(session, *, login, password, first_name, last_name, is_temp_password=False) -> User
```

Хеширует `password` через bcrypt; выбрасывает `ValidationError`, если login занят.

## Жизненный цикл конкурса и неизменяемость [UPDATED] {#contest-lifecycle--immutability}

Машина статусов на `contests.status` (управляется `contest_lifecycle_service.py`):

```
DRAFT ──(first activate)──► RUNNING ──(POST /pause)──► PAUSED
                                │                         │
                                │                    (POST /resume)
                                │                         │
                                └──(POST /finish)──► FINISHED ◄──┘
```

| Правило | Применение |
|---------|------------|
| Первая активация тура | **До lock:** `purge_before_first_activation` удаляет всех участников USER со статусом PENDING; затем `transition_round` устанавливает `is_locked=true`; lifecycle устанавливает `status=RUNNING` |
| Очистка неподтверждённых | При первой активации `contest_setup_service.purge_unconfirmed_participants` удаляет строки `contest_participants` со `status=PENDING` и `users.role=USER`; orphan users удаляются, если не зачислены в другой конкурс |
| PATCH настроек при lock | `403 ContestLocked` — структурные поля и `rules_json` заморожены |
| GET настроек при lock | Всегда разрешён (SUPERVISOR+) — снимок только для чтения |
| Обновление exceptional tie-break | Разрешено техподдержке даже при lock — не часть правил конкурса |
| Безопасное удаление | Мягкое удаление SUPERVISOR+ (DRAFT мгновенно; PAUSED после grace); скрыто из списков (`deleted_at`); восстановление техподдержкой в окне snapshot |
| Hard purge | Ops-скрипт `purge_deleted_contests.py`; retention `contest_purge_retention_seconds` в settings (по умолчанию 30 дней) |

**До → После (Stage 1.15+):** Pause/resume: SUPERVISOR+. Finish: техподдержка (SUPERVISOR только при `supervisor_training_mode`). Delete: SUPERVISOR+ без training flag; restore: **только техподдержка**. Delete создаёт snapshot, затем soft-delete.

**Очистка при безопасном удалении** (`contest_teardown.wipe_contest_data`): удаляет операционные данные конкурса и сбрасывает конкурс в пустой DRAFT (строка конкурса сохраняется). При включённом training mode сначала записывается restore snapshot — см. `contest_restore_service.py`.

**Маппинг доменных ошибок** (определены в `src/core/exceptions.py`, маппятся в `src/api/error_handlers.py`):

| Исключение | HTTP | `code` (типичный) |
|------------|------|-------------------|
| `NotFoundError` | 404 | `NOT_FOUND` |
| `ValidationError` | 400 | `VALIDATION_ERROR` |
| `ScoreOutOfRangeError` | 422 | `SCORE_OUT_OF_RANGE` |
| `ContestRuleError` | 403 | `CONTEST_RULE_VIOLATION` / `DEADLINE_PASSED` / `DEADLINE_CHANGE_CLOSED` [UPDATED] / `RESULTS_NOT_AVAILABLE` [UPDATED] / `PARTICIPANT_NOT_ENROLLED` / `PARTICIPANT_NOT_ACCEPTED` / … |
| `ContestLockedError` | 403 | `CONTEST_LOCKED` |
| `GracePeriodError` | 400 | `GRACE_PERIOD_ACTIVE` |
| `IllegalTransitionError` | 409 | `ILLEGAL_TRANSITION` |
| `ContestNotPausedError` | 403 | `CONTEST_NOT_PAUSED` |
| `ContestDeleteDisabledError` | 403 | `CONTEST_DELETE_DISABLED` |
| `PasswordSetupRequiredError` | 403 | `PASSWORD_SETUP_REQUIRED` [NEW] |
| `SnapshotNotFoundError` | 404 | `SNAPSHOT_NOT_FOUND` [NEW] |
| `SnapshotExpiredError` | 410 | `SNAPSHOT_EXPIRED` [NEW] |
| Unhandled / `CriticalError` | 500 | `INTERNAL_ERROR` |

Тело ответа: `{"detail": "<Russian message>", "code": "<CODE>"}`. См. [Формат ответа об ошибке](#error-response-format) и [ERROR_LOGGING.md](../../agent_docs/contracts/ERROR_LOGGING.md).

**Body DELETE `/contests/{id}`:** `{ "confirm": "DELETE" }` (Pydantic `Literal`). Неверное значение confirm → **422** (валидация схемы). Валидный confirm, но grace не истёк → **400** (`GracePeriodError`). Ответ `{ "deleted": true, "status": "DELETED" }`. Строка конкурса остаётся в БД с установленным `deleted_at` и **скрыта** из `GET /contests` и публичных списков до restore или hard purge.

**Hard purge (ops):** `uv run python src/scripts/purge_deleted_contests.py` удаляет мягко удалённые строки старше `CONTEST_PURGE_RETENTION_SECONDS` (по умолчанию 30 дней). Опции: `--dry-run`, `--before ISO-DATE`, `--all-deleted`.

Legacy shim: `DELETE /admin/contest` (только конкурс по умолчанию, техподдержка, устарело).

> **Заметка по SQLite:** `paused_at` может round-trip как naive datetime. Сравнение grace period в `assert_deletable` ожидает timezone-aware значения; нормализуйте к UTC в production code или используйте PostgreSQL для production.

## Слой сервисов [UPDATED] {#service-layer}

Все сервисы — `async` функции с `AsyncSession`. Роутеры оборачивают вызовы в транзакции через `get_db`.

### `round_service.py` [UPDATED] {#round_servicepy-updated}

```python
def validate_round_deadline_placement(deadline, earliest_match, *, now=None) -> None
def assert_deadline_change_allowed(current_deadline, deadline_rule_hours, *, now=None) -> None
async def transition_round(session, round_id, target_status: RoundStatus) -> Round
async def set_deadline(session, round_id, new_deadline: datetime) -> Round
async def close_round(session, contest_id, round_id) -> Round
```

**Auto-close (lazy, без scheduler) [NEW Stage 1.16]:**

Фоновой job нет. Просроченные туры ACTIVE (`now >= deadline`) переходят в `CLOSED` синхронно во время API-запросов.

| Слой | Триггер | Реализация |
|------|---------|------------|
| **Batch** | `ContestContext` на `/api/v1/contests/{contest_id}/…` | `auto_close_expired_rounds(session, contest_id)` в `deps.get_contest_context`; `commit`, если какой-то тур закрыт |
| **Per-round** | Любой сервис, затрагивающий конкретный тур | `ensure_round_closed_if_expired(session, round_id)` в `round_auto_close_service.py` — вызывается перед guards prediction/result/calculate/LB |

**Гарантии после дедлайна:**

| Операция | Поведение |
|----------|-----------|
| `POST …/predictions` | Отклонено — `403` `DEADLINE_PASSED` и/или `ROUND_NOT_ACTIVE` |
| `GET …/predictions` | Полная таблица при `now >= deadline` (любой caller, включая без Bearer). До дедлайна: правила приватности для аутентифицированных; anonymous → **403** `PREDICTIONS_NOT_PUBLIC` |
| `PUT …/results`, `POST …/calculate` | Разрешено, когда тур `CLOSED` (auto-closed inline, если в БД ещё `ACTIVE`) |
| `GET …/rounds` | Возвращает `status=CLOSED` для просроченных туров (batch hook и/или prior per-round ensures) |

Legacy shims (`GET/POST /api/v1/rounds/…` без `contest_id`) **не** используют `ContestContext`; полагаются на **per-round** ensure внутри services/handlers.

Явное закрытие: `POST /api/v1/contests/{contest_id}/admin/rounds/{id}/close` — то же конечное состояние; требует `now >= deadline` (идемпотентно, если уже `CLOSED`).

См. `agent_docs/contracts/contest_lifecycle_flow.md` §3.2 и `manuals/dev/STATUS_REFERENCE.md` §2.

**Машина статусов** (только один шаг; нелегальные переходы → `IllegalTransitionError`):
```
DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED
```

**Старт конкурса (Stage 1.15):** `POST /contests/{id}/start` устанавливает `is_locked=true`, `status=RUNNING` и очищает неподтверждённых участников PENDING — **без** активации тура. Идемпотентно, если уже RUNNING + locked.

**Побочный эффект активации (legacy / после start):** `contests.is_locked = True` при переходе в `ACTIVE`, если ещё не locked. API вызывает `purge_before_first_activation` **до** lock (no-op, если не DRAFT), затем `transition_round`, затем `ensure_running_on_first_activation` → `status=RUNNING`.

**Политика дедлайна (2026-06-27) [UPDATED]:**

| Правило | Когда | Ограничение |
|---------|-------|-------------|
| **Placement** | Создание тура, `set_deadline`, PATCH deadline | `now < deadline < earliest_match_kickoff` (`validate_round_deadline_placement`) |
| **24h change lockout** | `set_deadline` только на туре **ACTIVE** | Организатор может менять deadline только пока `now <= current_deadline - deadline_rule_hours` (`assert_deadline_change_allowed` → `DEADLINE_CHANGE_CLOSED`) |
| **Прошедшие даты матчей** | Создание тура | Каждый матч `date_time >= now`; иначе `400` `VALIDATION_ERROR` |

**До → После:** `deadline_rule_hours` (по умолчанию 24 из `rules_json.contest_structure`) больше **не** требует, чтобы deadline был за N часов до первого kickoff. Он ограничивает **редактирование** deadline на активном туре. См. [SCORING_LOGIC.md — Validation Constraints](SCORING_LOGIC.md#validation-constraints).

**Round PATCH** (`PATCH …/admin/rounds/{id}`): редактируем в `DRAFT` или `ACTIVE` (не `CLOSED`+). На **ACTIVE** после прошедшего deadline: смена `team1_id` / `team2_id` → `400` «После дедлайна нельзя менять состав матчей»; deadline и поля расписания матчей могут обновляться с учётом placement/24h rules.

**Политика frontend (Stage 2.3.2) [UPDATED]:** UI организатора на `/admin/rounds` блокирует редактирование состава команд, когда тур `ACTIVE` (`canEditRoundStructure` только в `DRAFT`). Изменения расписания — через status dropdown + kickoff-based reschedule (`matchScheduleEdit.ts`). Backend PATCH может ещё принимать swap команд до prediction deadline, пока не ужесточено — см. `agent_docs/reports/todo.md`.

### `match_service.py`

```python
async def set_result(session, match_id, score1: int, score2: int) -> Match
async def change_status(session, match_id, new_status: MatchStatus) -> Match
```

- `set_result`: проверяет `0 ≤ score ≤ max_score_value`; устанавливает `FINISHED`. Разрешено, когда `round.status` — `CLOSED` или `CALCULATED` и `now >= deadline`. Сначала выполняется **`ensure_round_closed_if_expired`**, чтобы `ACTIVE` строка после deadline закрылась inline [NEW 1.16]. На `CALCULATED` после обновления счёта запускает `recalculate_round`, чтобы `scores` и staff LB preview оставались синхронизированы. [UPDATED] Ошибка `ROUND_NOT_CLOSED`, когда тур не `CLOSED`/`CALCULATED`: сообщение «Результат можно внести только на закрытом или рассчитанном туре».
- `change_status(VOID)`: если тур `CALCULATED`, атомарно запускает `recalculate_round`.

### `prediction_service.py` [UPDATED]

```python
async def submit_batch(session, user_id, round_id, items: list[tuple[int,int,int]]) -> int
async def visible_predictions(session, round_id, viewer_role, viewer_id) -> list[dict]
```

До дедлайна: только свои очки для `USER` и `SUPERVISOR`; `ADMIN` видит все. После дедлайна: полная таблица (`visible_predictions` использует `now >= deadline`; **`ensure_round_closed_if_expired`** на GET/POST [NEW 1.16]).

API добавляет `assert_contest_running` перед submit. Неполный batch → `400`; deadline / не ACTIVE / contest не RUNNING → `403`.

**До → После (Stage 1.7):** Отправка прогнозов больше не использует router-level `require_not_temp_password`. `submit_batch` проверяет зачисление и статус accept:

| Условие | HTTP | `code` |
|---------|------|--------|
| `users.is_temp_password=true` | 403 | `PARTICIPANT_NOT_ACCEPTED` |
| Нет строки `contest_participants` | 403 | `PARTICIPANT_NOT_ENROLLED` |
| `participant.status != ACCEPTED` | 403 | `PARTICIPANT_NOT_ACCEPTED` |

Смена пароля (`POST /auth/change-password`) переводит все участия `PENDING` в `ACCEPTED` через `participant_service.accept_pending_participations`.

### `scoring_persistence.py`

См. [SCORING_LOGIC.md — Scoring Persistence](SCORING_LOGIC.md#scoring-persistence).

### `contest_lifecycle_service.py` [UPDATED]

```python
async def purge_before_first_activation(session, contest_id: int) -> int
async def require_unlocked(session, contest_id: int) -> Contest
async def assert_contest_running(session, contest_id: int) -> Contest
async def ensure_running_on_first_activation(session, contest_id: int) -> Contest
async def pause_contest(session, contest_id: int) / resume_contest(session, contest_id: int) / finish_contest(session, contest_id: int)
async def assert_deletable(session, contest_id: int, *, instant: bool) -> Contest
async def delete_contest_data(session, contest_id: int, *, deleted_by_user_id: int | None) -> None
async def update_exceptional_tiebreak(session, contest_id: int, user_id, points) -> int
```

### `auth_setup_service.py` [NEW]

Stage 1.12 — preview по подписанной ссылке, complete-setup, password reset.

```python
async def preview_setup(session, token: str) -> dict
async def complete_setup(session, token: str, new_password: str | None) -> dict
async def request_password_reset(session, email: str) -> dict
```

### `contest_restore_service.py` [NEW]

Stage 1.12 — snapshot в training mode при delete и replay через `POST /contests/{id}/restore`.

```python
async def restore_contest_from_snapshot(session, contest_id: int) -> None
```

Содержимое snapshot (минимальное): скаляры конкурса + `rules_json`, teams, rounds, matches, список `user_id` участников.

### `contest_setup_service.py` [UPDATED]

```python
async def purge_unconfirmed_participants(session, contest_id: int) -> int
```

Удаляет всех участников USER со статусом PENDING перед первой активацией (вызывается, пока конкурс ещё unlocked).

### `leaderboard_service.py` [UPDATED]

Агрегирует строки `Score`, читает `contest_participants.exceptional_tiebreak_points`, вызывает `build_standings(manual_overrides=…)`, сериализует `count_exact_high`, `count_exact`, `count_diff`, `count_outcome` на каждой строке leaderboard и строит ETag hashes для cache headers.

**Видимость (Stage 2.3.1):** `get_round_leaderboard` / `get_round_results` принимают опциональный `viewer_role`. `_assert_round_visible` разрешает `PUBLISHED` для public/USER; добавляет `CALCULATED` для `SUPERVISOR`/`ADMIN`. `get_global_leaderboard` join'ит scores только из туров со `status == PUBLISHED`.

### `team_logo_service.py` [NEW]

Stage 1.9 — validate, resize (64×64 center-crop), сохранение логотипов команд; resolve default URL для ответов API.

```python
async def save_team_logo(session, *, contest_id, team_id, file_bytes, content_type, settings) -> str
def resolve_team_logo_url(logo_url: str | None, settings) -> str
def delete_uploaded_logo_if_custom(logo_url: str | None, settings) -> None
```

### `participant_service.py` [NEW]

Stage 1.7 — перевод pending invites в accepted при смене пароля.

```python
async def accept_pending_participations(session, user_id: int) -> int
```

### `contest_discovery_service.py` [NEW]

Stage 1.8 — списки конкурсов для зачисленных пользователей и анонимных visitors.

```python
async def list_user_contests(session, *, user_id: int, role: str) -> list[UserContestOut]
async def list_public_contests(session) -> list[PublicContestOut]
```

- `list_user_contests`: JOIN `contests` + `contest_participants` для `user_id`; сортировка по `contests.name`; echo глобальной `users.role`.
- `list_public_contests`: только `contests.status = RUNNING`; сортировка по name.

### `contact_service.py` [NEW]

Stage 1.8 — read/upsert строки `contacts` для эндпоинтов профиля.

```python
async def get_contacts(session, user_id: int) -> ContactOut
async def upsert_contacts(session, user_id: int, patch: dict) -> ContactOut
```

- Отсутствующая строка → defaults (`email/vk_id/tg_id` null, `notify_enabled=false`).
- Частичный PATCH через `model_dump(exclude_unset=True)` в router; пустая строка очищает `email`.
- Невалидный email → `ValidationError` (`400`, `VALIDATION_ERROR`).

## Справочник эндпоинтов [UPDATED] {#endpoints-reference}

Базовый путь: `/api/v1`. **Предпочтительно:** contest-scoped paths из [Multi-Contest API](#multi-contest-api). Legacy paths ниже — deprecated shims (конкурс по умолчанию).

### Публичные (без auth)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/contests/public` | Конкурсы RUNNING для Visitor discovery |
| `GET` | `/rounds` | Список туров (конкурс по умолчанию) ⚠️ deprecated |
| `GET` | `/leaderboard` | Глобальная таблица ⚠️ deprecated |
| `GET` | `/rounds/{id}/leaderboard` | Таблица тура ⚠️ deprecated |
| `GET` | `/rounds/{id}/results` | Результаты матчей + очки пользователей ⚠️ deprecated |

### Пользователь (Bearer, USER+)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/me/contests` | Зачисленные конкурсы с `participant_status` |
| `GET` | `/auth/me/contacts` | Контакты профиля |
| `PATCH` | `/auth/me/contacts` | Частичное обновление контактов |
| `GET` | `/rounds/{id}/predictions` | Predictions с фильтром видимости ⚠️ deprecated |
| `POST` | `/rounds/{id}/predictions` | Пакетное сохранение прогнозов ⚠️ deprecated |

### Организатор (Bearer, SUPERVISOR или ADMIN) — legacy shims

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/admin/contest-settings` | Чтение конфигурации конкурса ⚠️ deprecated |
| `PATCH` | `/admin/contest-settings` | Обновление настроек ⚠️ deprecated |
| `POST` | `/admin/rounds` | Создание тура с матчами ⚠️ deprecated |
| `PATCH` | `/admin/rounds/{id}` | Обновление deadline тура ⚠️ deprecated |
| `POST` | `/admin/rounds/{id}/activate` | DRAFT → ACTIVE ⚠️ deprecated |
| `POST` | `/admin/rounds/{id}/calculate` | CLOSED → CALCULATED ⚠️ deprecated |
| `POST` | `/admin/rounds/{id}/publish` | CALCULATED → PUBLISHED ⚠️ deprecated |
| `PUT` | `/admin/matches/{id}/result` | Ввод финального счёта ⚠️ deprecated |
| `PATCH` | `/admin/matches/{id}/status` | VOID / POSTPONED / CANCELED ⚠️ deprecated |

### Только техподдержка (Bearer, ADMIN)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/admin/users/supervisor` | Создание аккаунта организатора (SUPERVISOR) |

### Только техподдержка (Bearer, ADMIN) — legacy shims

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/admin/contest/pause` | RUNNING → PAUSED ⚠️ deprecated |
| `POST` | `/admin/contest/resume` | PAUSED → RUNNING ⚠️ deprecated |
| `POST` | `/admin/contest/finish` | RUNNING\|PAUSED → FINISHED ⚠️ deprecated |
| `DELETE` | `/admin/contest` | FK-safe очистка ⚠️ deprecated |
| `PUT` | `/admin/users/{user_id}/exceptional-tiebreak` | Tie-break (конкурс по умолчанию) ⚠️ deprecated |
| `POST` | `/admin/recalculate` | Re-run scoring ⚠️ deprecated |

### `POST /rounds/{id}/predictions`

**Запрос:**

```json
{
  "predictions": [
    { "match_id": 1, "score1": 0, "score2": 0 }
  ]
}
```

**Правила:** Требуются все матчи тура (атомарное сохранение). Счёт `0..20`; `0` — валидное значение. Отсутствующие поля → `422`; неполный batch → `400`; после deadline / не ACTIVE / contest PAUSED|FINISHED → `403`.

**Ответ GET (Stage 2.3.1) [UPDATED]:** Каждый матч в представлении прогнозов включает `team1_id` и `team2_id` (FK к `teams.id`) вместе с отображаемыми именами — используется admin UI для выбора команд.

**Ответ:** `{ "success": true, "saved_count": 8 }`

## HTTP-кэширование [NEW] {#http-caching}

Публичные GET leaderboard и results возвращают:

```
Cache-Control: public, max-age=300, stale-while-revalidate=60
ETag: <16-char sha256 hash of score state>
```

ETag выводится из `max(Score.id)` и статуса тура — меняется после calculate/VOID/recalculate.

**Не кэшируются:** predictions GET/POST, все admin routes, contest PATCH.

TTL настраивается через [CONFIG.md](../setup/CONFIG.md#environment-variables).

## Формат ответа об ошибке [NEW] {#error-response-format}

Доменные ошибки (подклассы `AppError` из `src/core/exceptions.py`) возвращают:

```json
{ "detail": "Дедлайн тура истёк", "code": "DEADLINE_PASSED" }
```

| `code` | Типичный HTTP |
|--------|---------------|
| `NOT_FOUND` | 404 |
| `VALIDATION_ERROR` | 400 |
| `SCORE_OUT_OF_RANGE` | 422 |
| `CONTEST_RULE_VIOLATION` / `DEADLINE_PASSED` / `DEADLINE_CHANGE_CLOSED` / `RESULTS_NOT_AVAILABLE` / `CONTEST_NOT_RUNNING` | 403 [UPDATED] |
| `PARTICIPANT_NOT_ENROLLED` / `PARTICIPANT_NOT_ACCEPTED` | 403 |
| `CONTEST_LOCKED` | 403 |
| `PASSWORD_SETUP_REQUIRED` | 403 [NEW] |
| `SNAPSHOT_NOT_FOUND` | 404 [NEW] |
| `SNAPSHOT_EXPIRED` | 410 [NEW] |
| `GRACE_PERIOD_ACTIVE` | 400 |
| `ILLEGAL_TRANSITION` | 409 |
| `INTERNAL_ERROR` | 500 |

- Pydantic validation: **422**, body FastAPI по умолчанию (без `code`).
- Auth/RBAC (`deps.py`): только `detail`, русский текст, без `code`.
- Полная политика (RU): [ERROR_LOGGING.md](../../agent_docs/contracts/ERROR_LOGGING.md).

## Логирование [NEW] {#logging}

Настраивается при старте в `main.py` через `setup_logging(settings.log_level)`.

| Уровень | Типичное использование |
|---------|------------------------|
| `ERROR` | Необработанные исключения, алерты `notify_admin` |
| `WARNING` | Восстанавливаемые fallbacks, 4xx `AppError` на HTTP boundary |
| `INFO` | Сохранение прогнозов, расчёт тура, pause/resume/finish конкурса |
| `DEBUG` | Счётчики scoring data, детали auto-close |

Формат лога: `%(asctime)s %(levelname)s [%(name)s] %(message)s`

Уровень задаётся env var `LOG_LEVEL` (по умолчанию `INFO`). См. [CONFIG.md](../setup/CONFIG.md#environment-variables).

Восстанавливаемые внутренние проблемы (например, пропущенные NULL prediction rows) логируются как `WARNING` и применяют defaults без падения запроса — см. [ERROR_LOGGING.md](../../agent_docs/contracts/ERROR_LOGGING.md#категории-ошибок).

## Связанная документация {#related-documentation}

| Тема | Документ |
|------|----------|
| Таблицы и ограничения БД | [DB_REFERENCE.md](DB_REFERENCE.md) |
| Env vars и seed | [CONFIG.md](../setup/CONFIG.md) |
| Очки, бонусы и tie-breakers | [SCORING_LOGIC.md](SCORING_LOGIC.md) |
| Начальный bootstrap ADMIN/SUPERVISOR | [BOOTSTRAP_USERS.md](../setup/BOOTSTRAP_USERS.md) |
| Политика ошибок и логирования (RU) | [ERROR_LOGGING.md](../../agent_docs/contracts/ERROR_LOGGING.md) |
