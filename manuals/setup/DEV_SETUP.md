# Локальная настройка разработки (Backend + Frontend)

Однократный и повседневный workflow для запуска стека **Football Predictions Contest** локально.

**Связанные документы:** [CONFIG.md](CONFIG.md) · [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) · [API_GUIDE.md](../dev/API_GUIDE.md) · Frontend Stage 2: `agent_docs/instructions/coder_2.1.md`

> **Docker Compose:** пока не предоставлен (Stage 3). Используйте bootstrap-скрипт ниже или запускайте команды вручную.

---

## Требования

| Инструмент | Версия | Проверка |
|------|---------|--------|
| **Python** | ≥ 3.12 | `python3 --version` |
| **[uv](https://docs.astral.sh/uv/)** | latest | `uv --version` |
| **Node.js** | ≥ 20 LTS (18+ может работать) | `node --version` |
| **npm** | ≥ 10 | `npm --version` |

Опционально для E2E (тестировщик Stage 2.1+): браузеры Playwright — **однократно**:

```bash
cd frontend && npm run playwright:install
```

Браузеры хранятся в `frontend/.playwright-browsers/` (вне git, переиспользуются агентами).
`playwright.config.ts` сам задаёт `PLAYWRIGHT_BROWSERS_PATH` — **не** используйте голый `npx playwright install` (sandbox может скачать в эфемерный `/tmp/cursor-sandbox-cache/`).

---

## Быстрый старт (рекомендуется)

Из корня репозитория:

```bash
# 1. Окружение (один раз)
cp .env.example .env
# Отредактируйте .env: задайте SEED_SUPPORT_PASSWORD и SEED_SUPERVISOR_PASSWORD (см. .env.example)

# 2. Bootstrap БД + запуск API и UI (одна команда)
uv run python src/scripts/dev_setup.py --run
# → http://127.0.0.1:3000/  (UI)
# → http://127.0.0.1:8000/health  (API)
# Ctrl+C для остановки обоих серверов
```

При первом `--run` скрипт также создаёт `frontend/.env.local` из `.env.local.example` и запускает `npm install`, если `node_modules/` отсутствует.

### Ручной запуск (два терминала)

Используйте, если предпочитаете отдельные процессы или БД уже настроена:

```bash
# Только bootstrap (без серверов)
uv run python src/scripts/dev_setup.py

# Терминал 1 — API
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Терминал 2 — UI
cd frontend
cp .env.local.example .env.local   # один раз
npm install                        # один раз
npm run dev                        # http://127.0.0.1:3000
```

**Перезапуск серверов без сброса БД:**

```bash
uv run python src/scripts/dev_setup.py --run-only
```

**Проверка API:** `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`

**Проверка публичного списка конкурсов (B2):** после полной настройки конкурс id `1` в статусе **RUNNING** → `curl -s http://127.0.0.1:8000/api/v1/contests/public`

---

## Bootstrap-скрипт — `src/scripts/dev_setup.py`

Автоматизирует миграции, тестовые данные, пользователей admin и dev-состояние конкурса.

```bash
uv run python src/scripts/dev_setup.py              # полная dev БД для frontend (по умолчанию)
uv run python src/scripts/dev_setup.py --run        # полная настройка + запуск API (:8000) и UI (:3000)
uv run python src/scripts/dev_setup.py --run-only     # только запуск серверов (без настройки БД)
uv run python src/scripts/dev_setup.py --minimal    # пустой конкурс + только admin (без CSV loader'а)
uv run python src/scripts/dev_setup.py --no-reset   # полная настройка без предварительной очистки таблиц loader'а
uv run python src/scripts/dev_setup.py --check      # только проверка требований, без изменений БД
uv run python src/scripts/dev_setup.py --check-ports  # проверить, что :8000 и :3000 свободны [UPDATED]
uv run python src/scripts/dev_setup.py --ensure-running-only          # ручная фикстура после loader'а
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e    # E2E: только тур 10 ACTIVE
uv run python src/scripts/dev_setup.py --finalize-fixture-only      # восстановить фикстуру на существующей БД
uv run python src/scripts/dev_setup.py --help
```

### Что делают `--run` / `--run-only` [UPDATED]

1. **`assert_dev_ports_free`** — прервать, если API `:8000` или UI `:3000` уже занят (см. `--check-ports`)
2. Убедиться, что `frontend/.env.local` существует (скопировать из `.env.local.example`, если отсутствует)
3. Запустить `npm install` в `frontend/`, если `node_modules/` отсутствует
4. Запустить **API**: `uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000`
5. Запустить **UI**: `npm run dev` в `frontend/` → `http://127.0.0.1:3000`
6. Опрашивать `/health` и корень UI до готовности (или таймаут ~90с)
7. При **Ctrl+C** или SIGTERM — остановить оба дочерних процесса

`--run` = полная настройка по умолчанию, затем шаги 1–7. `--run-only` = шаги 1–7 без изменения БД.

**Только проверка портов:**

```bash
uv run python src/scripts/dev_setup.py --check-ports
# ✅ API: 127.0.0.1:8000 is free
# ❌ UI: 127.0.0.1:3000 is in use  → exit 1
```

### Что делает `--full` (по умолчанию)

1. `uv sync` (установка Python-зависимостей из `pyproject.toml`)
2. Предупреждение, если `.env` отсутствует (скопировать из `.env.example` вручную)
3. `alembic upgrade head`
4. `load_test_data.py --reset` — конкурс **id=1**, 16 команд, 10 пользователей (`user`/`user`, …), туры 1–10 из CSV
5. `bootstrap_users.py` — **после loader'а** (loader с `--reset` удаляет всех `users`; bootstrap восстанавливает `support` / `supervisor` из `.env`)
6. **Dev-состояние конкурса** — конкурс `1` → `RUNNING` + `is_locked=true`
7. **`finalize_dev_fixture`** (manual-профиль, по умолчанию) — туры **1–9** `PUBLISHED` со `scores` (90 строк ≡ `expected_scores.csv`), тур **10** `CALCULATED` (10 очков, не опубликован), тур **11** `CLOSED` (ожидает ввода результатов)

| Тур | Статус после finalize | Строк `scores` |
|-------|----------------------|---------------|
| 1–9 | `PUBLISHED` | по 10 (всего 90) |
| 10 | `CALCULATED` | 10 |
| 11 | `CLOSED` | 0 |

**E2E-профиль** (`--e2e`): пропускает finalize; тур **10** остаётся `ACTIVE` с дедлайном в будущем (тесты прогнозов / правила 24 часов). Использование:

```bash
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
```

**Восстановление существующей БД** без полного сброса:

```bash
uv run python src/scripts/dev_setup.py --finalize-fixture-only
```

### Что делает `--minimal`

Шаги 1–3 как выше, затем `seed.py` + `bootstrap_users.py` (без CSV loader'а, без тестового логина `user/user`).

Используйте `--minimal` для пустого конкурса на этапе SETUP; используйте **`--full`** для Stage 2 frontend / E2E.

### Dev-фикстура — `finalize_dev_fixture` (Stage 1.14)

Скрипт: `src/scripts/finalize_dev_fixture.py`. Вызывается автоматически в конце **полной настройки по умолчанию** и `--ensure-running-only` (кроме `--e2e`).

**Назначение:** после CSV loader'а конкурс `id=1` показывает все значимые фазы туров для ручного QA организатора — не только `CLOSED` (1–9) + `ACTIVE` (10).

| Шаг | Что происходит |
|------|----------------|
| Туры 1–9 | `calculate_round` → `PUBLISHED`; строки `scores` ≡ `expected_scores.csv` (всего 90) |
| Тур 10 | Синтетические результаты матчей → `CALCULATED` (10 очков); **не** опубликован |
| Тур 11 | Новый тур `CLOSED`, дедлайн прошёл (референс **2026-06-27**), 8 матчей `SCHEDULED`, 0 очков |
| Конкурс | `RUNNING` + `is_locked=true` |
| Участники | Пользователи только из bootstrap (`admin`, демо `user`) переведены в `PENDING`, чтобы подсчёт очков оставался 10 пользователей/тур |

**Профили:**

| Профиль | Команда | Тур 10 | Туры 1–9 | Тур 11 |
|---------|---------|----------|------------|----------|
| Manual (по умолчанию) | `dev_setup.py` или `--ensure-running-only` | `CALCULATED` | `PUBLISHED` + очки | `CLOSED` |
| E2E | `--ensure-running-only --e2e` | `ACTIVE`, дедлайн в будущем | `CLOSED`, без finalize | не создан |
| Только восстановление | `--finalize-fixture-only` | (повторно применяет manual-таблицу) | | |

**Проверка фикстуры (SQLite):**

```sql
SELECT r.number, r.status,
       (SELECT COUNT(*) FROM scores s WHERE s.round_id = r.id) AS score_rows
FROM rounds r
WHERE r.contest_id = 1
ORDER BY r.number;
-- Ожидается: 1–9 PUBLISHED (по 10), 10 CALCULATED (10), 11 CLOSED (0); всего scores = 100
```

Значения статусов и обзор UI: [STATUS_REFERENCE.md](../dev/STATUS_REFERENCE.md) §2.3 (таблица dev-фикстуры).

**Изоляция pytest:** `load_test_data.py` сам по себе оставляет туры 1–9 в `CLOSED`, а тур 10 в `ACTIVE` — finalize запускается только из `dev_setup`, а не из loader'а.

**Ручное QA Stage 2.3.2:** после прохождения организатором `/admin/rounds` или `/admin/results`, перед передачей повторно запустите `--finalize-fixture-only`, чтобы восстановить туры 9=`PUBLISHED`, 10=`CALCULATED`, 11=`CLOSED` (см. [STATUS_REFERENCE.md](../dev/STATUS_REFERENCE.md) §2.3).

---

## Шаги вручную (без скрипта)

```bash
uv sync
cp .env.example .env   # отредактируйте пароли

uv run alembic upgrade head

# Полные dev-данные (порядок важен — bootstrap ПОСЛЕ loader'а):
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only   # RUNNING + finalize fixture (manual-профиль)

# То же, что три строки выше, одной командой:
# uv run python src/scripts/dev_setup.py

# Минимальный вариант:
# uv run python src/scripts/seed.py
# uv run python src/scripts/bootstrap_users.py
```

---

## Окружение frontend

Создайте `frontend/.env.local` (см. `frontend/.env.local.example` после scaffold):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Используйте `127.0.0.1` везде (совпадает с `baseURL` Playwright в инструкциях тестировщика). `localhost` тоже работает, если CORS разрешает (по умолчанию `CORS_ORIGINS=["*"]`).

---

## Тестовые логины (после настройки `--full`)

| Роль | Логин | Пароль | Источник |
|------|-------|----------|--------|
| USER (контрактный) | `shutov` (или любой логин из CSV) | `user` | `load_test_data.py` — у всех контрактных пользователей общий dev-пароль `user` |
| SUPERVISOR | `supervisor` | значение из `.env` `SEED_SUPERVISOR_PASSWORD` | `bootstrap_users.py` |
| Support | `support` | значение из `.env` `SEED_SUPPORT_PASSWORD` | `bootstrap_users.py` |

> **Примечание:** для новых участников используйте UI приглашений организатора (`/admin/settings/participants`) или `dev_invite_setup.py confirm-all`. Playwright E2E создаёт отдельного пользователя через `playwright.global-setup.ts`.

**Не** коммитьте `.env` или реальные пароли.

---

## Запуск тестов

### Backend

```bash
uv run pytest tests/ --ignore=tests/manual -q
```

Регрессия Stage 1.12 (auth setup, purge, training restore):

```bash
ENFORCE_PASSWORD_SETUP=true SUPERVISOR_TRAINING_MODE=true \
  CONTEST_DELETE_GRACE_SECONDS=0 CONTEST_RESTORE_WINDOW_SECONDS=3600 \
  uv run pytest tests/api/test_auth_setup.py tests/api/test_participant_purge.py \
    tests/api/test_contest_restore.py tests/api/test_dev_invite_setup.py \
    tests/api/test_participant_accept.py -v
```

### Frontend (после scaffold Stage 2.1)

```bash
cd frontend
npm run test:unit
npm run lint && npm run type-check && npm run format:check
npm run test:e2e          # требует API на :8000 и UI на :3000
npm run build
```

ID линтеров для отчётов тестировщика: `[LINT-ESLINT]`, `[LINT-TSC]`, `[LINT-PRETTIER]` — см. `agent_docs/instructions/tester_2.1.md` §6.

---

## Troubleshooting

| Симптом | Решение |
|---------|-----|
| `bootstrap_users` пропускает / нет пользователя support | Задайте `SEED_SUPPORT_PASSWORD` в `.env` |
| `GET /contests/public` возвращает `[]` | Перезапустите `dev_setup.py` (конкурс должен быть **RUNNING**) |
| Ошибки CORS с `:3000` | Убедитесь, что `CORS_ORIGINS` включает origin frontend или `["*"]` |
| Нарушение unique constraint в `load_test_data` | Используйте `--reset` или полный `dev_setup.py` |
| Admin отсутствует после loader'а | Запустите `bootstrap_users.py` **после** `load_test_data --reset` |
| Вход `user/user` не работает (401) | Перезапустите `dev_setup.py --full` — используйте контрактный логин `shutov` / `user` |
| Playwright E2E не находит браузер | `cd frontend && npm run playwright:install` (кэш: `.playwright-browsers/`) |
| Порт занят | `uv run python src/scripts/dev_setup.py --check-ports`; остановите процесс на :8000/:3000 или используйте стек другого терминала |
| `--run` завершается сразу | Проверьте логи — отсутствует `frontend/`, `node` или `npm`; запустите `--check` |
| UI не готов после `--run` | Дождитесь до 90с при первом `npm install`; перезапустите `cd frontend && npm run dev` |

---

<a id="new-contest-confirm-participants-without-email-stage-112"></a>

## Новый конкурс: подтверждение участников без email (Stage 1.12+)

SMTP **не** подключён в dev. Приглашённые игроки начинают со статуса `PENDING` в `contest_participants`, пока не завершат настройку пароля (`ACCEPTED`). До этого они не могут отправлять прогнозы.

> **Критично:** при **активации первого тура** API **удаляет** всех участников USER со статусом `PENDING`. Подтвердите всех **до** активации тура 1. См. [API_GUIDE.md](../dev/API_GUIDE.md#password-setup--invite-links-stage-112).

### Локальное тестирование invite (дефолты)

Дополнительные флаги в корневом `.env` не нужны. Дефолты в `config/settings.py`:

- `enforce_password_setup=true` — flow invite, приближённый к production
- `frontend_base_url=http://127.0.0.1:3000` — корректный host для `setup_url`

Устаревший автоматизированный вход только в тестах: `ENFORCE_PASSWORD_SETUP=false` через **префикс shell** или pytest `monkeypatch` — см. [CONFIG.md — Настройки local / CI](CONFIG.md#local--ci-tuning-not-in-env).

### Workflow A — invite через UI + ссылка настройки (один участник)

1. Запустите стек: `uv run python src/scripts/dev_setup.py --run-only` (или `--run` на свежей БД).
2. Войдите как **supervisor** → **Настройки** → **Участники** (`/admin/settings/participants`).
3. Выберите нужный конкурс (мультиконкурс: переключите конкурс в шелле организатора).
4. Заполните форму приглашения (email, имя) → **Пригласить**.
5. В модальном окне показываются **логин**, **временный пароль** и **`setup_url`** — скопируйте все три (кнопка «Скопировать»).
6. **Подтвердите участника** (выберите один способ):
   - **Браузер:** откройте `setup_url` в новой вкладке (или инкогнито), задайте постоянный пароль → редирект на login → войдите как новый пользователь.
   - **Передать вручную:** отправьте логин + `setup_url` игроку (почтовый сервер не нужен).
7. В разделе **Участники** статус должен измениться с «Ожидает» (`PENDING`) на «Принят» (`ACCEPTED`).
8. Пользователь может открыть конкурс и отправлять прогнозы, когда тур станет `ACTIVE`.

Формат `setup_url`: `http://127.0.0.1:3000/auth/setup?token=…` (host frontend из `FRONTEND_BASE_URL` / настроек).

### Workflow B — массовое подтверждение через `dev_invite_setup.py` (dev / QA)

Используйте, когда пригласили много пользователей и не хотите открывать каждую ссылку вручную.

```bash
# 1. Список PENDING-приглашённых для конкурса id=2; опционально: записать ссылки настройки
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id 2 \
  --out src/scripts/dev_unconfirmed.tsv \
  --links-out src/scripts/.tokens

# 2a. Открыть ссылки из .tokens (JSON-строки с setup_url) — то же, что шаг 6 в Workflow A
# 2b. Или подтвердить всех на сервере (задаёт пароль + ACCEPTED за один шаг):
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id 2 \
  --password 'DevPass123!'

# Частичный список из TSV:
uv run python src/scripts/dev_invite_setup.py confirm-list \
  --file src/scripts/dev_unconfirmed.tsv \
  --password 'DevPass123!'
```

`src/scripts/.tokens` — вне git. Столбцы TSV: `user_id`, `contest_id`, `email`, `login`.

### Workflow C — создание пустого конкурса (`--minimal`)

Для **нового** конкурса (не CSV-конкурса `id=1`):

```bash
uv run python src/scripts/dev_setup.py --minimal
# → пустой конкурс DRAFT + admin/supervisor; без демо-пользователей
```

Затем в UI: создать/настроить конкурс → пригласить участников (Workflow A или B) → добавить команды/туры → активировать первый тур только после того, как все нужные пользователи в статусе `ACCEPTED`.

### Проверка в БД (опционально)

```sql
SELECT u.login, cp.status
FROM contest_participants cp
JOIN users u ON u.id = cp.user_id
WHERE cp.contest_id = 2
ORDER BY u.login;
-- Нужен статус ACCEPTED до POST .../rounds/{id}/activate
```

### Troubleshooting

| Симптом | Решение |
|---------|-----|
| В модальном окне invite нет `setup_url` | Проверьте логи API; убедитесь, что `FRONTEND_BASE_URL` / frontend на `:3000` |
| Вход с временным паролем → 403 `PASSWORD_SETUP_REQUIRED` | Ожидаемо при `ENFORCE_PASSWORD_SETUP=true` — используйте `setup_url`, а не вход с временным паролем |
| Участник пропал после активации тура | Был всё ещё `PENDING` — пригласите повторно или подтвердите до активации |
| `confirm-all` находит 0 строк | Неверный `--contest-id`; или пользователь уже `ACCEPTED` / не temp-password |

Детали API: [API_GUIDE.md — Настройка пароля и invite-ссылки](../dev/API_GUIDE.md#password-setup--invite-links-stage-112).

---

## Подтверждение invite без SMTP — `dev_invite_setup.py` (краткая справка)

Когда SMTP не настроен, используйте dev-скрипт для экспорта неподтверждённых приглашённых и подтверждения через `complete-setup`:

```bash
# Экспорт неподтверждённых участников (опционально: регенерировать ссылки настройки)
uv run python src/scripts/dev_invite_setup.py list-pending
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id 2 \
  --out src/scripts/dev_unconfirmed.tsv \
  --links-out src/scripts/.tokens

# Подтвердить строки из TSV (строки с # пропускаются)
uv run python src/scripts/dev_invite_setup.py confirm-list \
  --file src/scripts/dev_unconfirmed.tsv \
  --password 'DevPass123!'

# Экспорт + подтверждение всех за один шаг (пароль из SEED_SUPERVISOR_PASSWORD в .env)
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id 2
```

`src/scripts/.tokens` — вне git (один JSON-объект на строку с `setup_url`).
Для переключателей E2E/training используйте переменные shell или pytest `monkeypatch` — см. [CONFIG.md — Настройки local / CI](CONFIG.md#local--ci-tuning-not-in-env).

---

## Повседневный workflow

| Задача | Команда |
|------|---------|
| Bootstrap + запуск стека | `uv run python src/scripts/dev_setup.py --run` |
| Запуск стека (БД уже в порядке) | `uv run python src/scripts/dev_setup.py --run-only` |
| Запуск только API | `uv run uvicorn main:app --reload --port 8000` |
| Запуск только UI | `cd frontend && npm run dev` |
| Сброс БД к demo-состоянию | `uv run python src/scripts/dev_setup.py` |
| Восстановить только фикстуру (без loader'а) | `uv run python src/scripts/dev_setup.py --finalize-fixture-only` |
| E2E БД (тур 10 ACTIVE) | `uv run python src/scripts/dev_setup.py --ensure-running-only --e2e` |
| Архивировать лог приложения | `uv run python src/scripts/archive_logs.py` |
| Перезапустить миграции | `uv run alembic upgrade head` |

Вы **не** перезапускаете `bootstrap_users.py` при каждом рестарте API — пользователи сохраняются в `football.db`. Перезапускайте после очистки БД или свежего клона.

---

## Ссылки для агентов Stage 2

| Роль | Документ |
|------|----------|
| Coder 2.1 | `agent_docs/instructions/coder_2.1.md` §2 |
| Tester 2.1 | `agent_docs/instructions/tester_2.1.md` §2 |
| Интеграция API | `agent_docs/contracts/frontend_api_integration.md` |
| Блокеры | `agent_docs/reports/BLOCKED.md` (B1–B6 решены) |

---

*Последнее обновление: Stage 2.3.1 — `--check-ports`; Stage 1.14 fixture + invite workflow.*

---

<a id="manual-qa-cheatsheet"></a>

## Шпаргалка для ручного QA

Быстрые команды для ручного тестирования организатором (также печатаются в конце `dev_setup.py` при запуске стека).

### Сброс базы данных к demo-фикстуре

Возвращает конкурс **id=1** (RUNNING, заблокирован), 16 команд, демо-пользователей. Очищает таблицы loader'а.

```bash
# Полный сброс (рекомендуется)
uv run python src/scripts/dev_setup.py

# То же самое, плюс запуск API + UI
uv run python src/scripts/dev_setup.py --run

# Только шаг loader'а (затем восстановить staff + состояние фикстуры)
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
```

### Принять все ожидающие приглашения (без SMTP)

Список конкурсов, у которых остались приглашённые со статусом **«Ожидает»**:

```bash
uv run python src/scripts/dev_invite_setup.py list-pending
```

Пример вывода:

```text
contest_id	pending	name
10	2	E2E Setup 1719580000
```

Подтверждает каждого участника с временным паролем в статусе `PENDING` для указанного конкурса через `complete-setup`:

```bash
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id <ID>
```

**Пароль:** не логин организатора — это **новый пароль**, назначаемый каждому приглашённому пользователю.
По умолчанию скрипт читает `SEED_SUPERVISOR_PASSWORD` из `.env` (то же значение, что вы используете для входа `supervisor` в dev).
Переопределите через `--password '…'` при необходимости.

```bash
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id <ID> --password 'OtherPass1!'
```

Опционально: сначала экспортировать список + ссылки настройки:

```bash
uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id <ID> \
  --out src/scripts/dev_unconfirmed.tsv --links-out src/scripts/.tokens
```

<a id="remove-extra--deleted-contests"></a>

### Удаление лишних / удалённых конкурсов

E2E (`admin_setup`, `supervisor_create_round`, …) создаёт много конкурсов в статусах **DRAFT** и **RUNNING** с именами вида `E2E Setup …`. Они засоряют список конкурсов, пока их не удалить.

#### Поштучно (UI)

| Статус конкурса | Шаги |
|----------------|-------|
| **DRAFT** | Выбрать конкурс → `/admin/settings/parameters` → **Удалить конкурс** (мгновенное soft-delete) |
| **RUNNING** | Та же страница → **Остановить конкурс** → подождать **10 с** (`contest_delete_grace_seconds`, по умолчанию 10) → **Удалить конкурс** |
| **PAUSED** | **Удалить конкурс** (после задержки, если кнопка удаления была отключена) |
| **FINISHED** | В UI организатора удаление недоступно — пропустить или полный сброс БД ниже |

Soft-deleted конкурсы пропадают из `GET /contests`, но остаются в БД до окончательного удаления. Support может **восстановить** их в течение training-окна на `/admin/lifecycle`.

**Массового скрипта** для удаления множества активных строк DRAFT/RUNNING нет — используйте цикл в UI или сброс БД.

#### Окончательное удаление soft-deleted строк из БД

```bash
uv run python src/scripts/purge_deleted_contests.py --all-deleted --dry-run
uv run python src/scripts/purge_deleted_contests.py --all-deleted
```

Очистка только по TTL хранения (по умолчанию 30 дней): `uv run python src/scripts/purge_deleted_contests.py` — см. `contest_purge_retention_seconds` в [CONFIG.md](CONFIG.md).

#### Полный сброс (назад к единственному фикстурному конкурсу `id=1`)

Очищает таблицы loader'а и все дополнительные конкурсы; восстанавливает демо-пользователей и завершённые туры конкурса 1:

```bash
uv run python src/scripts/dev_setup.py
```

Используйте, когда в списке десятки остатков от E2E и не нужно сохранять кастомные конкурсы. Серверы продолжают работать, если уже запущены; меняется только БД. Чтобы перезапустить стек: `dev_setup.py --run-only`.

| Цель | Действие |
|------|--------|
| Скрыть draft из списков (soft delete) | UI: «Удалить конкурс» на странице параметров (DRAFT/PAUSED) |
| Восстановить в течение окна | Support: `/admin/lifecycle` → «Восстановить» |
| **Окончательное удаление** soft-deleted строк из БД | `purge_deleted_contests.py --all-deleted` (см. выше) |
| Очистка только по TTL хранения | `uv run python src/scripts/purge_deleted_contests.py` |
| Сбросить всё к dev-фикстуре | `uv run python src/scripts/dev_setup.py` |

### Типичный flow создания конкурса (S1.x)

1. «+ Новый конкурс» → задать параметры → добавить все команды → пригласить участников.
2. `confirm-all --contest-id <ID>` (или вручную `setup_url` для каждого приглашения).
3. Страница параметров: панель готовности зелёная → «Запустить конкурс».

См. [SUPERVISOR_TESTING_SCENARIOS.md](../testing/SUPERVISOR_TESTING_SCENARIOS.md) для полного чек-листа.
