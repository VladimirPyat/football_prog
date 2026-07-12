# Руководство по развёртыванию сервера

Как развернуть стек Football Predictions Contest: API (FastAPI) + фронтенд (Next.js).

**Связанные документы:** [CONFIG.md](CONFIG.md) (полная таблица настроек), [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md) (первые Support/SUPERVISOR), [API_GUIDE.md](../dev/API_GUIDE.md) (`setup_url` для приглашений), [DEV_SETUP.md](DEV_SETUP.md) (только локальная разработка).

## Содержание

- [Режимы развёртывания (`APP_MODE`)](#режимы-развёртывания-app_mode)
- [Что менять и где](#что-менять-и-где)
- [Развёртывание в Docker (рекомендуется)](#развёртывание-в-docker-рекомендуется)
- [Чек-лист первого развёртывания (Docker)](#чек-лист-первого-развёртывания-docker)
- [Обновление развёртывания (git pull)](#обновление-развёртывания-git-pull)
- [Архитектура](#архитектура)
- [Локальная разработка (без Docker)](#локальная-разработка-без-docker)
- [Ручное развёртывание / systemd](#ручное-развёртывание--systemd)
- [Обратный прокси nginx (HTTP)](#обратный-прокси-nginx-http)
- [TLS / HTTPS (позже)](#tls--https-позже)
- [Постоянные данные](#постоянные-данные)
- [Ссылки-приглашения и SMTP](#ссылки-приглашения-и-smtp)
- [Чек-лист продакшена](#чек-лист-продакшена)
- [Решение проблем](#решение-проблем)

---

## Режимы развёртывания (`APP_MODE`)

Сервер хранит собственный **игнорируемый git** файл `.env`. Обновления кода через `git pull` **не должны** перезаписывать продакшн-URL, CORS или секреты.

Установите один режим в `.env`:

| `APP_MODE` | Когда | База данных | URL / CORS |
|------------|------|----------|-------------|
| `local` | Ноутбук (`uv run`, `npm run dev`) | SQLite (`./football.db`) | `127.0.0.1`, CORS `*` |
| `web_dev` | Сервер/докер-стейджинг | SQLite (`./data/football.db`) | `PUBLIC_*` или значения по умолчанию `localhost` |
| `web_prod` | Продакшн | PostgreSQL (compose `--profile prod`) | **`PUBLIC_FRONTEND_URL` обязателен** |

Пресеты заданы в ``resolve_app_mode_preset()`` (`config/settings.py`) — один читаемый блок на режим. Секреты и URL сервера остаются в игнорируемом git файле ``.env``.

**Правило:** на сервере редактируйте **только** `.env` (и тома `data/`). Не коммитьте URL сервера в репозиторий.

---

## Что менять и где

| Что | Файл / расположение | `local` | `web_dev` / `web_prod` |
|------|-----------------|---------|------------------------|
| Режим | корневой `.env` → `APP_MODE` | `local` | `web_dev` или `web_prod` |
| Публичный URL интерфейса (приглашения, CORS) | корневой `.env` → `PUBLIC_FRONTEND_URL` | — | `https://app.example.com` |
| Публичный URL API (браузер) | корневой `.env` → `PUBLIC_API_URL` | — | `https://api.example.com` |
| Пароль БД (Docker) | корневой `.env` → `POSTGRES_PASSWORD` | — | только `web_prod` |
| Пароли JWT / seed | корневой `.env` | плейсхолдеры для разработки | продакшн-секреты |
| Кастомный URL БД | корневой `.env` → `DATABASE_URL` | опционально | переопределяет значение режима по умолчанию |
| Файл SQLite (`web_dev`) | хост `./data/football.db` | `./football.db` | том Docker `./data` |
| URL API фронтенда при сборке | Docker build-аргумент из `PUBLIC_API_URL` | `frontend/.env.local` | `.env` → пересборка фронтенда |
| Загрузки и логи | хост `./data/uploads`, `./data/logs` | `./uploads`, `./logs` | тома Docker |
| Файлы PostgreSQL | том Docker `pgdata` | — | автоматически |

**Критично:** `PUBLIC_API_URL` встраивается на этапе **`docker compose build`** (Next.js). Изменение требует **пересборки** сервиса `frontend`.

**Критично:** `setup_url` в приглашении использует `PUBLIC_FRONTEND_URL` (через пресет `FRONTEND_BASE_URL`) на **API** в момент отправки приглашения.

---

## Развёртывание в Docker (рекомендуется)

Файлы стека (закоммитены):

| Файл | Роль |
|------|------|
| [`docker-compose.yml`](../../docker-compose.yml) | `db` + `api` + `frontend` |
| [`Dockerfile`](../../Dockerfile) | Образ API (`uv`, Alembic при старте) |
| [`frontend/Dockerfile`](../../frontend/Dockerfile) | Многоэтапная сборка Next.js |
| [`.env.example`](../../.env.example) | Шаблон для серверного `.env` |
| [`deploy/`](../../deploy/) | nginx (HTTP) + Docker entrypoint |

### Предварительные требования (сервер)

| Инструмент | Версия |
|------|---------|
| Docker Engine | 24+ |
| Docker Compose | v2 (`docker compose`) |
| Git | клонирование/pull репозитория |
| Обратный прокси (прод) | nginx / Caddy / Traefik + TLS |

### 1. Клонирование и создание постоянной структуры

```bash
sudo mkdir -p /opt/football_prog
sudo chown "$USER":"$USER" /opt/football_prog
git clone <repo-url> /opt/football_prog
cd /opt/football_prog

mkdir -p data/uploads data/logs
cp .env.example .env
chmod 600 .env
```

### 2. Настройка серверного `.env`

Пример для **продакшена**:

```env
APP_MODE=web_prod

PUBLIC_FRONTEND_URL=https://app.example.com
PUBLIC_API_URL=https://api.example.com

POSTGRES_PASSWORD=replace-with-strong-db-password
JWT_SECRET_KEY=replace-with-64-plus-char-random-string

SEED_SUPPORT_PASSWORD=your-support-password
SEED_SUPERVISOR_PASSWORD=your-supervisor-password

# Опциональный маппинг портов хоста (по умолчанию 8000 / 3000)
# API_PORT=8000
# FRONTEND_PORT=3000
```

Пример для **стейджинга на VDS с nginx** (`web_dev`, один IP, HTTP без TLS):

```env
APP_MODE=web_dev
PUBLIC_FRONTEND_URL=http://10.0.0.1
PUBLIC_API_URL=http://10.0.0.1
JWT_SECRET_KEY=staging-jwt-secret
SEED_SUPPORT_PASSWORD=your-support-password
SEED_SUPERVISOR_PASSWORD=your-supervisor-password
```

Оба `PUBLIC_*` **без порта** — снаружи слушает nginx на `:80`. После правки `.env` пересоберите фронтенд: `docker compose build frontend`.

Пример **без nginx** (прямой доступ к портам Docker):

```env
APP_MODE=web_dev
PUBLIC_FRONTEND_URL=http://localhost:3000
PUBLIC_API_URL=http://localhost:8000
POSTGRES_PASSWORD=staging-db-password
JWT_SECRET_KEY=staging-jwt-secret
```

Compose читает `.env` для подстановки переменных **и** передаёт его в контейнер API (`env_file`). Этот файл **никогда** не попадает в git — безопасен при каждом `git pull`.

### 3. Сборка и запуск

```bash
cd /opt/football_prog
docker compose build

# web_dev (SQLite, без контейнера PostgreSQL):
docker compose up -d

# web_prod (добавляет PostgreSQL):
docker compose --profile prod up -d
```

При первом старте контейнер API автоматически выполняет `alembic upgrade head` (`deploy/docker/entrypoint-api.sh`).

### 4. Начальная загрузка пользователей (один раз для пустой БД)

```bash
docker compose exec api uv run python src/scripts/seed.py
docker compose exec api uv run python src/scripts/bootstrap_users.py
```

См. [BOOTSTRAP_USERS.md](BOOTSTRAP_USERS.md). **Не** запускайте повторно при каждом развёртывании.

### 5. Дымовой тест (smoke test)

```bash
curl -s http://127.0.0.1:8000/health
# → {"status":"ok"}

curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/
# → 200
```

Затем настройте nginx ([§ ниже](#обратный-прокси-nginx-http)) и проверьте вход + флоу приглашения в браузере.

### 6. Кратко: что дальше

Docker слушает **только на localhost**: `127.0.0.1:3000` (UI) и `127.0.0.1:8000` (API). Пользователи заходят через nginx на порту 80 (позже 443). Подробные конфиги — в следующем разделе.

---

## Чек-лист первого развёртывания (Docker)

1. Установить Docker + Compose на сервере
2. Клонировать репозиторий в `/opt/football_prog`
3. `mkdir -p data/uploads data/logs`
4. Скопировать `.env.example` → `.env`; задать `APP_MODE=web_prod`, `PUBLIC_*`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, пароли seed
5. `docker compose build && docker compose up -d`
6. `docker compose exec api uv run python src/scripts/seed.py`
7. `docker compose exec api uv run python src/scripts/bootstrap_users.py`
8. Установить nginx по [§ HTTP](#обратный-прокси-nginx-http) (TLS — позже)
9. Дымовой тест: `/health`, вход в интерфейсе, приглашение → `setup_url` → настройка пользователя

---

## Обновление развёртывания (git pull)

Серверный `.env` и тома `data/` находятся **вне git** — они переживают обновления.

```bash
cd /opt/football_prog
git pull

# Пересборка при изменении кода или PUBLIC_API_URL фронтенда
docker compose build

docker compose up -d
```

| Что изменилось | Действие |
|---------|--------|
| Код API / Python | `docker compose build api && docker compose up -d api` |
| Код фронтенда | `docker compose build frontend && docker compose up -d frontend` |
| `PUBLIC_API_URL` в `.env` | **Обязательна** пересборка фронтенда |
| Только `PUBLIC_FRONTEND_URL` | Перезапуск API: `docker compose up -d api` |
| Миграции Alembic в репозитории | Автоматически при старте контейнера API |
| Только секреты `.env` | `docker compose up -d` (пересоздать при необходимости) |

Миграции выполняются перед uvicorn при каждом старте API. Для нулевого времени простоя на масштабе запускайте миграции отдельной разовой задачей — для однохостового развёртывания это не требуется.

Полезные команды:

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f frontend
docker compose down          # остановить (тома сохраняются)
docker compose down -v       # ⚠ удаляет том PostgreSQL
```

---

## Архитектура

Три контейнера в продакшн-Docker:

| Сервис | Образ / сборка | Порт по умолчанию | Роль |
|---------|---------------|--------------|------|
| **db** | `postgres:16-alpine` | внутренний `5432` | PostgreSQL (том `pgdata`); **только `--profile prod`** |
| **api** | `Dockerfile` | `8000` | FastAPI, JWT, статические логотипы |
| **frontend** | `frontend/Dockerfile` | `3000` | UI на Next.js |

**Node.js и Python на хосте не нужны** при развёртывании через Docker — они внутри образов (`node:20-alpine`, `python:3.12-slim`). Playwright, Vitest и `e2e/` в продакшн-образ не попадают (см. `frontend/.dockerignore`).

Проверить версию Node **в контейнере**:

```bash
docker compose exec frontend node -v
# → v20.x
```

Браузер обращается к **обоим** публичным origin:

- UI → `PUBLIC_FRONTEND_URL`
- Вызовы API → `PUBLIC_API_URL`

---

## Локальная разработка (без Docker)

```bash
cp .env.example .env
# APP_MODE=local (по умолчанию)

uv sync
uv run alembic upgrade head
uv run python src/scripts/seed.py
uv run python src/scripts/bootstrap_users.py
uv run uvicorn main:app --reload --port 8000

cd frontend
cp .env.local.example .env.local
npm ci && npm run dev
```

См. [DEV_SETUP.md](DEV_SETUP.md).

Опционально: запустите стек Docker локально с `APP_MODE=web_dev` в `.env`, чтобы повторить структуру серверной БД.

---

## Ручное развёртывание / systemd

Если вы предпочитаете bare-metal (без Docker):

```bash
uv sync --no-dev
uv run alembic upgrade head
# задайте APP_MODE=web_prod + PUBLIC_* в .env
cd frontend && npm ci && npm run build && npm prune --omit=dev
```

Запускайте API и фронтенд через systemd — пример unit-файла API:

```ini
# /etc/systemd/system/football-api.service
[Service]
WorkingDirectory=/opt/football_prog
EnvironmentFile=/opt/football_prog/.env
ExecStart=/opt/football_prog/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
```

При `APP_MODE=web_prod` задайте `PUBLIC_FRONTEND_URL` в `.env` вместо отдельных `FRONTEND_BASE_URL` / `CORS_ORIGINS`.

PostgreSQL: создайте БД/пользователя вручную ([CONFIG.md — Database URL](CONFIG.md#database-url)).

---

## Обратный прокси nginx (HTTP)

Готовые файлы в [`deploy/nginx/`](../../deploy/nginx/):

| Файл | Когда использовать |
|------|-------------------|
| [`football-single-host.http.conf`](../../deploy/nginx/football-single-host.http.conf) | **Один IP или домен** — UI на `/`, API на `/api/` (рекомендуется для VDS) |
| [`football-two-hosts.http.conf`](../../deploy/nginx/football-two-hosts.http.conf) | **Два поддомена** — `app.*` и `api.*` |
| [`install-http.sh`](../../deploy/nginx/install-http.sh) | Скрипт: подставить хост и включить сайт |
| [`SSL-TODO.md`](../../deploy/nginx/SSL-TODO.md) | Заметки для HTTPS (certbot) — позже |

### Вариант A — один хост (IP VDS, без TLS)

Подходит для `APP_MODE=web_dev` на сервере. Пользователь открывает `http://10.0.0.1/` — без порта в URL.

**1. `.env`** (замените IP):

```env
APP_MODE=web_dev
PUBLIC_FRONTEND_URL=http://10.0.0.1
PUBLIC_API_URL=http://10.0.0.1
```

**2. Пересборка фронтенда** (обязательно после смены `PUBLIC_API_URL`):

```bash
cd /opt/football_prog
docker compose build frontend
docker compose up -d
```

**3. Установка nginx** (Ubuntu/Debian):

```bash
sudo apt update && sudo apt install -y nginx
cd /opt/football_prog
sudo bash deploy/nginx/install-http.sh single 10.0.0.1
```

Скрипт копирует конфиг в `/etc/nginx/sites-available/football`, включает symlink, делает `nginx -t` и `reload`.

**Ручная установка** (без скрипта):

```bash
sudo cp deploy/nginx/football-single-host.http.conf /etc/nginx/sites-available/football
sudo sed -i 's/YOUR_PUBLIC_HOST/10.0.0.1/g' /etc/nginx/sites-available/football
sudo ln -sf /etc/nginx/sites-available/football /etc/nginx/sites-enabled/football
sudo rm -f /etc/nginx/sites-enabled/default   # опционально, если мешает дефолтный сайт
sudo nginx -t && sudo systemctl reload nginx
```

**4. Проверка:**

```bash
curl -s http://10.0.0.1/health
# → {"status":"ok"}

curl -s -o /dev/null -w "%{http_code}" http://10.0.0.1/
# → 200
```

Откройте `http://10.0.0.1/` в браузере.

### Вариант B — два поддомена (HTTP)

**`.env`:**

```env
PUBLIC_FRONTEND_URL=http://app.football.local
PUBLIC_API_URL=http://api.football.local
```

На **своём ноутбуке** (если нет DNS) добавьте в `/etc/hosts`:

```
10.0.0.1 app.football.local api.football.local
```

**Установка:**

```bash
sudo bash deploy/nginx/install-http.sh two app.football.local api.football.local
```

| Публичный URL | Upstream |
|---------------|----------|
| `http://app.…` | `http://127.0.0.1:3000` |
| `http://api.…` | `http://127.0.0.1:8000` |

### Что проксирует nginx

| Путь | Сервис |
|------|--------|
| `/` | Next.js |
| `/api/` | FastAPI (`/api/v1/…`) |
| `/static/` | логотипы команд (FastAPI) |
| `/health` | health-check API |

nginx пересылает:

- заголовок `Authorization` (JWT)
- `client_max_body_size` 4 МиБ (загрузка логотипов, лимит API — 2 МиБ)

### Безопасность (рекомендуется)

С nginx закройте прямой доступ к портам Docker с интернета — оставьте только `80`/`443`:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 3000/tcp
sudo ufw deny 8000/tcp
```

Контейнеры по-прежнему слушают `0.0.0.0:3000` и `:8000` на хосте; ufw ограничивает доступ снаружи.

---

## TLS / HTTPS (позже)

Сейчас конфиги — **только HTTP** (`listen 80`). Для продакшена:

1. Настроить DNS на VDS.
2. Установить certbot: `sudo apt install certbot python3-certbot-nginx`
3. Выполнить (пример для двух поддоменов):
   ```bash
   sudo certbot --nginx -d app.example.com -d api.example.com
   ```
4. Обновить `.env` на `https://…`, пересобрать frontend, перезапустить API.
5. Подробности: [`deploy/nginx/SSL-TODO.md`](../../deploy/nginx/SSL-TODO.md).

Certbot добавит блоки `listen 443 ssl` и редирект с HTTP.

---

## Постоянные данные

| Путь / том | Git | Переживает `compose up` | Резервное копирование |
|---------------|-----|------------------------|--------|
| `.env` | игнорируется | да (файл хоста) | защищённая копия |
| `data/uploads/` | игнорируется | да (bind mount) | копирование тома |
| `data/logs/` | игнорируется | да (bind mount) | опционально: отправка логов |
| Том Docker `pgdata` | — | да | `pg_dump` |
| `data/football.db` | игнорируется | да (SQLite в `web_dev`) | копирование файла |

Создайте директории на хосте перед первым запуском: `mkdir -p data/uploads data/logs`.

---

## Ссылки-приглашения и SMTP

- **SMTP не настроен** в v1. `setup_url` приглашения показывается в интерфейсе организатора после `POST …/participants`.
- Ссылки используют `PUBLIC_FRONTEND_URL` (через пресет режима) в момент отправки приглашения.
- Когда SMTP будет добавлен, он будет использовать `build_setup_url()` — следите, чтобы `PUBLIC_FRONTEND_URL` был корректен на сервере.

---

## Чек-лист продакшена

| Пункт | Действие |
|------|--------|
| `APP_MODE` | `web_prod` на сервере |
| `PUBLIC_FRONTEND_URL` | Публичный HTTPS-URL интерфейса |
| `PUBLIC_API_URL` | Публичный HTTPS-URL API; пересобрать фронтенд после изменения |
| `POSTGRES_PASSWORD` | Надёжный; только в серверном `.env` |
| `JWT_SECRET_KEY` | Длинный случайный; стабилен между перезапусками |
| `DATABASE_URL` | PostgreSQL (compose задаёт автоматически, если не переопределён) |
| CORS | Выводится из `PUBLIC_FRONTEND_URL` — без `*` в проде |
| `ENFORCE_PASSWORD_SETUP` | `true` (принудительно в `web_prod`) |
| Пароли начальной загрузки | Запустить один раз; при желании удалить из `.env` позже |
| TLS | HTTPS на приложении + API (или прокси того же origin) |
| Тома | `data/uploads`, `data/logs`, `pgdata` |
| `.dockerignore` | Документы/тесты исключены из образов |

---

## Решение проблем

| Симптом | Вероятная причина |
|---------|----------------|
| Ошибка CORS | Неверный `PUBLIC_FRONTEND_URL`; перезапустите API |
| Ссылка-приглашение → `127.0.0.1:3000` | `APP_MODE=local` или отсутствует `PUBLIC_FRONTEND_URL` на API |
| UI загружается, вызовы API падают | Неверный `PUBLIC_API_URL` на этапе **сборки** — `docker compose build frontend` |
| 502 Bad Gateway от nginx | Docker не запущен или неверные порты — `docker compose ps`, `curl 127.0.0.1:3000` |
| nginx: duplicate server name | Удалите конфликтующий сайт в `sites-enabled/` |
| Конфигурация сбрасывается после `git pull` | Редактировались закоммиченные файлы вместо `.env` |
| Логотипы пропали после повторного развёртывания | `data/uploads` не примонтирован |
| БД пуста после повторного развёртывания | Выполнен `docker compose down -v` (удаляет `pgdata`) |
| `PUBLIC_FRONTEND_URL is required` | Задайте его для `APP_MODE=web_prod` |
| Ошибки Alembic / подключения к БД | Проверьте `POSTGRES_PASSWORD`, `docker compose ps`, здоровье БД |

---

*Последнее обновление: 2026-07-12 — готовые конфиги nginx (HTTP), install-http.sh, TLS-TODO.*
