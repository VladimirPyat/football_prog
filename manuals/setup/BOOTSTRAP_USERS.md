# Первичные пользователи (bootstrap)

Однократная настройка **Support** и **SUPERVISOR** на **новой базе данных** (локально или на сервере).  
После bootstrap пользователи живут в `football.db` (или в вашем `DATABASE_URL`) — **не запускайте скрипт** при каждом старте приложения, только когда БД снова пустая (новый деплой, новый сервер, сброс БД).

## Когда запускать

| Ситуация | Запускать `bootstrap_users.py`? |
|----------|----------------------------------|
| Первый деплой / пустая таблица `users` | **Да** |
| Ежедневная разработка, рестарт API, тесты | **Нет** — пользователи уже в БД |
| Сменили только пароль в `.env` | **Нет** — скрипт пропускает существующие логины; меняйте пароль через API или БД |
| Новый сервер / `alembic upgrade` на пустой БД | **Да** |

## 1. Настройка `.env`

Скопируйте шаблон: `cp .env.example .env`

Минимум (только пароли — логины `support` / `supervisor` заданы в `config/settings.py`):

```env
SEED_SUPPORT_PASSWORD=your-support-password
SEED_SUPERVISOR_PASSWORD=your-supervisor-password
JWT_SECRET_KEY=change-me-to-a-long-random-string
```

Используйте **пароли в открытом виде** — скрипт хеширует их bcrypt перед сохранением.  
Альтернатива: `SEED_SUPPORT_PASSWORD_HASH` / `SEED_SUPERVISOR_PASSWORD_HASH` (см. [CONFIG.md](CONFIG.md#env--secrets--deployment)).

Для не-SQLite деплоев также задайте `DATABASE_URL`.

## 2. Однократная настройка

```bash
uv run alembic upgrade head
uv run python src/scripts/seed.py              # строка конкурса (если отсутствует)
uv run python src/scripts/bootstrap_users.py   # Support + SUPERVISOR
```

**Идемпотентность:** если `support` / `supervisor` уже существуют, скрипт пишет «skipping» и ничего не меняет.

## 3. Проверка в DBeaver

До bootstrap (свежая БД): `users` пуста (или нет Support/SUPERVISOR).

После bootstrap:

```sql
SELECT id, login, role, is_temp_password FROM users;
```

Ожидайте строки вида `support` → `SUPPORT`, `supervisor` → `SUPERVISOR`.  
Колонка `password_hash` — bcrypt (`$2b$12$...`), не ваш открытый пароль.

## 4. Проверка входа и API организаторов

Запустите API: `uv run uvicorn main:app --reload`

### Вход как support

Логин bootstrap — `support` (переопределяется через `SEED_SUPPORT_LOGIN`). Пароль — из `SEED_SUPPORT_PASSWORD`.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"support","password":"your-support-password"}'
```

Сохраните `access_token`. Если `is_temp_password` = `true`, сначала вызовите `POST /api/v1/auth/change-password`.

### Создание ещё одного организатора (опционально)

Для этого теста достаточно **Support** в БД; supervisor из bootstrap — отдельный пользователь.

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/admin/users/supervisor \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "org_api",
    "password": "orgpass123",
    "first_name": "Ivan",
    "last_name": "Org"
  }'
```

Ожидайте `200` и `"role": "SUPERVISOR"`. Новая строка появится в DBeaver.  
Тот же сценарий в Swagger: `/docs` → Authorize → `POST /api/v1/admin/users/supervisor`.

| Вызывающий | Результат |
|------------|-----------|
| Support | 200 — пользователь создан |
| SUPERVISOR / USER | 403 |
| Дубликат логина | 400 |

## Два способа получить SUPERVISOR

| Способ | Когда |
|--------|-------|
| `bootstrap_users.py` + `SEED_SUPERVISOR_*` | Первый организатор на сервере |
| `POST /admin/users/supervisor` | Дополнительные организаторы (токен Support) |

Когда UI организатора полностью покрывает создание пользователей, можно перестать создавать организаторов через CLI (закомментировать `seed_supervisor_user` в `bootstrap_users.py` на сервере).

## См. также

- [.env.example](../../.env.example) — все имена переменных  
- [CONFIG.md](CONFIG.md) — справочник настроек  
- [API_GUIDE.md](../dev/API_GUIDE.md) — RBAC и маршруты  
