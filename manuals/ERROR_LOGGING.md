# Ошибки и логирование

Описание политики обработки ошибок и логирования в HTTP API и сервисном слое (Stage 1.5).

## Содержание

- [Архитектура](#архитектура)
- [Ответ клиенту](#ответ-клиенту)
- [Категории ошибок](#категории-ошибок)
- [Коды ошибок](#коды-ошибок)
- [Логирование](#логирование)
- [Оповещение администратора](#оповещение-администратора)
- [Где смотреть в коде](#где-смотреть-в-коде)

## Архитектура

```
Клиент → FastAPI → deps (auth/RBAC) → роутер → сервис
                              ↓                    ↓
                         HTTPException         AppError
                              ↓                    ↓
                         detail (RU)     error_handlers → JSON {detail, code}
```

| Слой | Файл | Роль |
|------|------|------|
| Исключения | `src/core/exceptions.py` | Иерархия `AppError`, `RecoverableError` |
| HTTP-маппинг | `src/api/error_handlers.py` | Единый обработчик → JSON |
| Auth/RBAC | `src/api/deps.py` | `HTTPException` без поля `code` |
| Сервисы | `src/services/*.py` | Бросают `AppError`, не знают про HTTP |
| Логи | `src/core/logging_config.py` | `setup_logging()` при старте |
| Алерты | `src/services/notification_service.py` | Заглушка `notify_admin()` |

Роутеры **не** содержат `try/except` для доменных ошибок — исключения всплывают в `error_handlers`.

## Ответ клиенту

### Доменные ошибки (`AppError`)

```json
{
  "detail": "Дедлайн тура истёк",
  "code": "DEADLINE_PASSED"
}
```

- `detail` — человекочитаемый текст на **русском**
- `code` — стабильный машиночитаемый идентификатор для клиентов и тестов

### Auth / RBAC (`deps.py`)

```json
{ "detail": "Недостаточно прав" }
```

Поле `code` **не** возвращается — только строка `detail`.

### Валидация Pydantic

Стандартный ответ FastAPI **422** (список полей) — без поля `code`.

## Категории ошибок

### 1. Нарушение правил конкурса (клиент видит 4xx)

Пользователь или супервайзер сделал недопустимое действие в рамках бизнес-правил.

Примеры:
- прогноз после дедлайна
- изменение правил при `is_locked`
- расчёт тура не в статусе CLOSED
- конкурс на паузе или завершён

**Поведение:** HTTP 400/403/409/422 + `detail` + `code`. В лог — **WARNING** (через `app_error_handler`).

### 2. Восстановимые внутренние проблемы (конкурс продолжается)

Данные неполные или неконсистентные, но не блокируют основной сценарий.

| Место | Проблема | Fallback | Лог |
|-------|----------|----------|-----|
| `scoring_persistence` | прогноз с NULL score | пропуск строки | WARNING |
| `leaderboard_service` | нет participant для tiebreak | `0` очков | WARNING |
| `handlers/predictions` | нет имени команды | `str(team_id)` | WARNING |
| `round_auto_close_service` | тур уже закрыт | пропуск | WARNING |

**Поведение:** операция завершается успешно; клиент **не** получает ошибку.

### 3. Критичные сбои (500)

Невозможно продолжить операцию: необработанное исключение, сбой инфраструктуры.

**Поведение:**
- HTTP 500, `detail`: «Внутренняя ошибка сервера», `code`: `INTERNAL_ERROR`
- лог **ERROR**
- вызов `notify_admin()` (заглушка — запись в лог; позже email/Telegram в одном месте)

## Коды ошибок

| `code` | HTTP | Когда |
|--------|------|-------|
| `NOT_FOUND` | 404 | конкурс, тур, матч, команда, участник не найдены |
| `VALIDATION_ERROR` | 400 | неполный batch прогнозов, дубликат команды, ранний close |
| `SCORE_OUT_OF_RANGE` | 422 | счёт вне [0, max_score_value] |
| `CONTEST_RULE_VIOLATION` | 403 | общее нарушение правила конкурса |
| `DEADLINE_PASSED` | 403 | дедлайн тура истёк |
| `CONTEST_NOT_RUNNING` | 403 | конкурс PAUSED / FINISHED |
| `CONTEST_LOCKED` | 403 | структурные изменения при `is_locked` |
| `GRACE_PERIOD_ACTIVE` | 400 | удаление до истечения grace после паузы |
| `ILLEGAL_TRANSITION` | 409 | недопустимый переход статуса |
| `CONTEST_NOT_PAUSED` | 403 | операция требует PAUSED |
| `CONTEST_DELETE_DISABLED` | 403 | удаление отключено в настройках |
| `INTERNAL_ERROR` | 500 | необработанная ошибка |

Специфичные коды (`DEADLINE_PASSED`, `ROUND_NOT_CLOSED` и т.д.) наследуют базовый HTTP-статус родительского класса.

## Логирование

Настройка через `config/settings.py` (дефолт `log_level=INFO`). Переопределение: env `LOG_LEVEL`. Полная таблица: [CONFIG.md](CONFIG.md#application-defaults-configsettingspy).

Формат строки:

```
2026-06-21 12:00:00 INFO [services.prediction_service] predictions saved user_id=3 round_id=10 count=8
```

Вывод: **stderr** (консоль) и, если `LOG_TO_FILE=true`, файл **`app.log`**. Файл в `.gitignore`.

### Ротация / архивация

Скрипт `src/scripts/archive_logs.py` копирует `app.log` в `logs/archive/app-YYYYMMDD-HHMMSS.log` и обнуляет активный файл, когда:

- размер ≥ `LOG_ARCHIVE_MAX_BYTES` (по умолчанию 5 MiB), **или**
- прошло ≥ `LOG_ARCHIVE_INTERVAL_DAYS` (по умолчанию 7) с последней архивации.

```bash
uv run python src/scripts/archive_logs.py           # по порогам
uv run python src/scripts/archive_logs.py --force   # сейчас (если лог не пуст)
```

Рекомендуется cron (например, раз в неделю). При работающем API после truncate лучше перезапустить Uvicorn — см. docstring скрипта.

Будущее: отдельный **auth.log** для аудита входов — см. `agent_docs/reports/todo.md`.

| Уровень | Назначение | Примеры |
|---------|------------|---------|
| **ERROR** | требует внимания админа | необработанное исключение, `CriticalError`, `ADMIN_ALERT` |
| **WARNING** | восстановимо | пропуск прогноза, auto-close skip, 4xx `AppError` на границе |
| **INFO** | ключевые бизнес-события | сохранены прогнозы, тур рассчитан, pause/resume/finish |
| **DEBUG** | отладка тяжёлых путей | объёмы данных при scoring, auto-close |

**Не логируются:** тела запросов, пароли, каждый успешный GET.

## Оповещение администратора

```python
# src/services/notification_service.py
await notify_admin("unhandled_exception", detail="...", context={...})
```

Вызывается из `error_handlers` при 500. Реальная интеграция (email, Telegram) подключается **только** в этом модуле.

## Где смотреть в коде

| Задача | Файл |
|--------|------|
| Добавить новый тип ошибки | `src/core/exceptions.py` |
| Изменить формат JSON-ответа | `src/api/error_handlers.py` |
| Текст для пользователя | сообщение при `raise` в сервисе (русский) |
| Добавить INFO при мутации | соответствующий `src/services/*.py` |
| Подключить алерт | `src/services/notification_service.py` |

См. также: [API_GUIDE.md — Error Response Format](API_GUIDE.md#error-response-format).
