# Структура проекта: Конкурс прогнозов

## 1. Технический стек (предварительно)
uv менеджер вместо pip

### Backend
- **Framework**: FastAPI 0.109+
- **Server**: Uvicorn (ASGI)
- **Database**: PostgreSQL 15+ (dev: SQLite)
- **ORM**: SQLAlchemy 2.0+ с async support
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Security**: JWT (python-jose), bcrypt для хеширования, CORS (`fastapi.middleware.cors`)
- **HTTP Caching**: Заголовки `Cache-Control`, `ETag` для публичных эндпоинтов (/leaderboard, /results)
- **Testing**: pytest + httpx (integration), pytest-asyncio

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript 5.3+
- **Styling**: Tailwind CSS 3.4+
- **State & Data**: React Context, `next/cache` (App Router), `localStorage` для офлайн-доступа
- **HTTP Client**: fetch API (встроенный) + TypeScript interfaces
- **Forms**: Controlled components (без Formik)
- **Validation**: Zod для клиентской валидации
- **Testing**: Playwright для E2E-тестов

### Кэширование и производительность
- **Backend (FastAPI)**: HTTP-кэширование через заголовки `Cache-Control` (`public, max-age=300, stale-while-revalidate=60`) для публичных эндпоинтов (`/leaderboard`, `/results`, `/predictions` после дедлайна). Приватные данные и формы кэшированию не подлежат. Инвалидация кэша автоматическая при `POST /admin/results/apply`, смене статуса матча на `VOID` или ручной корректировке.
- **Frontend (Next.js)**: Использование встроенного кэширования App Router (`fetch(..., { next: { revalidate: N } })`). Клиентский `localStorage` для мгновенного отображения таблиц при повторном визите. Формы ввода и pre-deadline данные не кэшируются.


### DevOps
- **Containerization**: Docker + docker-compose
- **CI/CD**: GitHub Actions (на этапе 3)
- **Linting**: ruff (Python), ESLint + Prettier (TypeScript)

## 2. Архитектура приложения

### Backend структура

Модульный монолит
Слабосвязанные компоненты (база данных, ядро и т.п.) с перспективой выделения микросервисов.
Интеграционные тесты с использованием провалидирированных данных

### Frontend структура
Предпочтение - модульная архитектура. Модули разделены по назначению: ввод прогнозов пользователей, ввод матчей и результатов организатором, лидерборд
Sliced архитектура - применяем только если при модульном подходе слишком много кода дублируется
playwright integration tests

## 3. Ключевые ограничения

### Backend
- Все эндпоинты защищены RoleChecker middleware
- Pydantic валидация на всех входах API
- Транзакционность при расчете очков (atomic batch update)
- JWT токены с expiration

### Frontend
- No external UI libraries (только Tailwind)
- No animations (простой UX)
- Client-side validation перед отправкой


### Database
- PostgreSQL для production, SQLite для dev
- Alembic migrations version-controlled
- Foreign keys + unique constraints


## 4. Основные сущности (кратко)

| Сущность | Таблица | Ключевые поля |
|----------|---------|---------------|
| User | `users` | id, login, password_hash, role |
| Team | `teams` | id, name, short_name |
| Match | `matches` | id, round_id, team1_id, team2_id, date, score1, score2, status |
| Round | `rounds` | id, number, deadline, status |
| Prediction | `predictions` | id, user_id, round_id, match_id, score1, score2 |
| Score | `scores` | id, user_id, round_id, points_exact, points_diff, points_outcome, bonuses |


