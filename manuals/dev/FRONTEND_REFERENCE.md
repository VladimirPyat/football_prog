# Справочник фронтенда — маршруты, компоненты и редактируемые тексты

Карта UI на Next.js для людей: где находятся маршруты, какие компоненты реализуют каждую функцию и где определены **видимые пользователю русские тексты**. Используйте её, чтобы менять подписи, футеры, баннеры и текст кнопок **без поиска по репозиторию и без обращения к агенту**.

> **Ведётся @Coder** в конце каждого фронтенд-подэтапа (только дополнение). Актуальные спецификации остаются в `agent_docs/ui/`; этот файл — **краткое руководство по редактированию** для людей.

---

## Как использовать

1. Найдите **маршрут** или **функцию** в таблицах ниже.
2. Откройте **файл исходного кода** (и область строк, если указана).
3. Отредактируйте строковые литералы в JSX — тексты UI на русском, если не указано иное.
4. Общий layout (header/footer) → начните с раздела **Layout и shell**.

---

## Layout и shell (сквозные)

| Область | Компонент | Файл исходного кода | Редактируемые тексты (примеры) |
|------|-----------|-------------|---------------------------|
| Публичный header/footer | `AppShell` | `frontend/src/components/layout/AppShell.tsx` | Бренд «Sport Prognosis», «Вход», «Личный кабинет», «Управление», футер ©, «Вход для организаторов» |
| Модальное окно входа | `LoginModal` | `frontend/src/components/layout/LoginModal.tsx` | Заголовок «Вход» |
| Форма входа | `LoginForm` | `frontend/src/components/auth/LoginForm.tsx` | Подписи «Логин», «Пароль», кнопка «Войти» |
| Страница входа для персонала | `/staff/login` | `frontend/src/app/staff/login/page.tsx` | «Вход для организаторов», подзаголовок |
| Верхняя навигация организатора | `AdminTopNav` | `frontend/src/components/admin/AdminTopNav.tsx` | Подписи вкладок, бренд, «+ Новый конкурс» |

---

## Маршруты (базовый набор, этап 2.1 / 2.1.1)

| Маршрут | Файл страницы | Роль / guard | Основные функции |
|-------|-----------|--------------|---------------|
| `/` | `frontend/src/app/page.tsx` | Public | Обзор конкурсов, редирект при авторизации |
| `/profile` | `frontend/src/app/profile/page.tsx` | USER | Личный кабинет «Личный кабинет» |
| `/contests` | `frontend/src/app/contests/page.tsx` | USER | Список конкурсов участника |
| `/change-password` | `frontend/src/app/change-password/page.tsx` | Auth + временный пароль | Форма смены пароля |
| `/staff/login` | `frontend/src/app/staff/login/page.tsx` | Public | Вход для персонала |
| `/admin` | `frontend/src/app/admin/page.tsx` | SUPERVISOR+ | Заготовка дашборда организатора |
| `/admin/settings/parameters` | `frontend/src/app/admin/settings/parameters/page.tsx` | SUPERVISOR+ | Заготовка настроек конкурса |

---

## Функции по этапам (дополняется @Coder ниже)

### Этап 2.2 — прогнозы и приватность

#### Маршруты

| Маршрут | Файл страницы | Роль / guard | Основные функции |
|-------|-----------|--------------|---------------|
| `/contest/[contestId]` | `frontend/src/app/contest/[contestId]/page.tsx` | Все (приватность по вкладке) | `PublicTabs` (Лидерборд / Прогнозы / Результаты), `RoundSelector`, `PredictionsMatrix` на вкладке «Прогнозы» |
| `/contest/[contestId]/predict/[roundId]` | `frontend/src/app/contest/[contestId]/predict/[roundId]/page.tsx` | USER+ (`requireNotTempPassword`) | `PredictionForm`, `DeadlineCountdown`, пакетное сохранение 8/8 |

#### Компоненты (редактируемые русские тексты)

| Компонент | Файл исходного кода | Ключевые тексты |
|-----------|-------------|----------|
| `PublicTabs` | `frontend/src/components/contest/PublicTabs.tsx` | «Лидерборд», «Прогнозы», «Результаты» |
| `RoundSelector` | `frontend/src/components/contest/RoundSelector.tsx` | «Выберите тур:», подписи через `formatRoundTitle()` |
| `PredictionForm` | `frontend/src/components/predictions/PredictionForm.tsx` | «Сохранить прогноз», «Редактировать», «Заполните прогнозы на все матчи тура» |
| `DeadlineCountdown` | `frontend/src/components/predictions/DeadlineCountdown.tsx` | Подпись обратного отсчёта; «Дедлайн прошёл» |
| `DeadlineWarningBanner` | `frontend/src/components/predictions/DeadlineWarningBanner.tsx` | «До дедлайна осталось менее 24 часов. Успейте сохранить прогноз.» |
| `PredictionsMatrix` | `frontend/src/components/predictions/PredictionsMatrix.tsx` | Заголовки таблицы «Счет», столбцы матчей |
| `PrivacyMask` | `frontend/src/components/predictions/PrivacyMask.tsx` | «Прогноз сделан» |
| `PredictionsVisitorStub` | `frontend/src/components/predictions/PredictionsVisitorStub.tsx` | «Будет доступно после дедлайна» (только для посетителя до дедлайна) |
| `OutcomeStatsFooter` | `frontend/src/components/predictions/OutcomeStatsFooter.tsx` | «Статистика», П1 / Х / П2 |
| `ProfileMenu` | `frontend/src/components/profile/ProfileMenu.tsx` | «Сделать прогноз» (ссылка на активный тур) |

### Этап 2.3 — UI организатора (`/admin/*`)

#### Маршруты

| Маршрут | Файл страницы | Роль / guard | Основные функции |
|-------|-----------|--------------|---------------|
| `/admin/settings/parameters` | `frontend/src/app/admin/settings/parameters/page.tsx` | SUPERVISOR+ | Параметры конкурса, карточки начисления очков (только чтение), баннер блокировки |
| `/admin/settings/participants` | `frontend/src/app/admin/settings/participants/page.tsx` | SUPERVISOR+ | Приглашение, таблица, модальное окно temp_password |
| `/admin/settings/teams` | `frontend/src/app/admin/settings/teams/page.tsx` | SUPERVISOR+ | Сетка команд, загрузка логотипа (B5) |
| `/admin/rounds` | `frontend/src/app/admin/rounds/page.tsx` | SUPERVISOR+ | Конструктор `DRAFT`, активация, редактор `ACTIVE`, свободный тур |
| `/admin/results` | `frontend/src/app/admin/results/page.tsx` | SUPERVISOR+ | Очки, расчёт, публикация, VOID |
| `/admin/newsletters` | `frontend/src/app/admin/newsletters/page.tsx` | SUPERVISOR+ | Заготовка этапа 3 |
| `/admin/lifecycle` | `frontend/src/app/admin/lifecycle/page.tsx` | Только Поддержка (SUPPORT) | Пауза/возобновление/завершение/удаление/пересчёт |
| `/admin/users` | `frontend/src/app/admin/users/page.tsx` | Только Поддержка (SUPPORT) | Создание организатора (SUPERVISOR) |

#### Компоненты (редактируемые русские тексты)

| Компонент | Файл исходного кода | Ключевые тексты |
|-----------|-------------|----------|
| `AdminTopNav` | `frontend/src/components/admin/AdminTopNav.tsx` | Вкладки: Настройки, Туры, Рассылки, Результаты; «+ Новый конкурс» |
| `LockBanner` | `frontend/src/components/admin/LockBanner.tsx` | «Редактирование параметров недоступно — Конкурс уже запущен…» |
| `ContestStatusBanner` | `frontend/src/components/admin/ContestStatusBanner.tsx` | «Конкурс на паузе» / «Конкурс завершён» |
| `ParticipantInviteModal` | `frontend/src/components/admin/ParticipantInviteModal.tsx` | «Участник приглашён», подписи login/temp_password |
| `NewsletterPromptModal` | `frontend/src/components/admin/NewsletterPromptModal.tsx` | «Отправить напоминание участникам?» (заготовка этапа 3) |
| `FreeTourModal` | `frontend/src/components/admin/FreeTourModal.tsx` | «Свободный тур», «Создать свободный тур» |
| `RoundManagementPanel` | `frontend/src/components/admin/RoundManagementPanel.tsx` | «Активировать», подсказка для `ACTIVE` (только расписание), блокировка изменения дедлайна 24ч, подтверждения действий с матчем [UPDATED] |
| `MatchEditorRow` | `frontend/src/components/admin/MatchEditorRow.tsx` | `<select>` статуса матча (`DRAFT` + `ACTIVE`); на `ACTIVE`: подтверждение при `CANCELED`/`POSTPONED`/восстановлении [NEW] |
| `RoundBuilderForm` | `frontend/src/components/admin/RoundBuilderForm.tsx` | «Создать черновик тура»; ошибки валидации для пустых дат матчей [UPDATED] |
| `MatchResultRow` | `frontend/src/components/admin/MatchResultRow.tsx` | Поля ввода счёта; «Применить» отключена, пока не заполнены оба счёта (пусто ≠ 0) [NEW] |
| `ResultsEntryPanel` | `frontend/src/components/admin/ResultsEntryPanel.tsx` | «Рассчитать», «Опубликовать», значок «Применено» |
| `LifecyclePanel` | `frontend/src/components/admin/LifecyclePanel.tsx` | Пауза, Возобновить, Завершить, Пересчитать, Удалить |

#### Этап 2.3.2 — расписание тура `ACTIVE` и UX результатов [NEW]

| Модуль | Файл исходного кода | Поведение |
|--------|-------------|----------|
| Режим UI | `frontend/src/lib/admin/deriveAdminUiMode.ts` | `canEditRoundStructure` → только `DRAFT`; изменение расписания на `ACTIVE` |
| Правила расписания | `frontend/src/lib/admin/matchScheduleEdit.ts` | Перенос до начала матча; отмена в любой момент; восстановление Поддержкой (SUPPORT); подсказка о переносе на 7 дней |
| Валидация счёта | `frontend/src/lib/validation/admin.ts` | `matchResultSchema`: пустая строка недопустима (не приводится к `0`) |
| Панели фаз | `frontend/src/components/admin/RoundPhasePanel.tsx` | Панели только для чтения `CLOSED` / `CALCULATED` / `PUBLISHED` на `/admin/rounds` |
| Предпросмотр лидерборда | `frontend/src/components/admin/RoundLeaderboardPreview.tsx` | Предпросмотр для персонала по турам `CALCULATED` |
| Публичная видимость | `frontend/src/lib/contest/roundPublicVisibility.ts` | Загрузка лидерборда/результатов только когда `round.status === 'PUBLISHED'` |

**Было → Стало:** туры в статусе `ACTIVE` больше не показывают `<select>` команд после активации. Изменения статуса используют тот же паттерн выпадающего списка, что и выбор тура, с `ConfirmDialog` для разрушительных переходов.


### Этап 2.4 — лидерборд и результаты (подключение API)

Публичная страница конкурса `/contest/[contestId]` — вкладки **Лидерборд** и **Результаты** используют реальные данные API. **Визуальная разметка не изменена** (существующие компоненты `LeaderboardTable` / `ResultsMatrix`).

| Модуль | Файл исходного кода | Поведение |
|--------|-------------|----------|
| Публичные пути | `frontend/src/lib/api/endpoints.ts` → `contestPublic` | `roundLeaderboard`, `roundResults`, опциональный глобальный `leaderboard` |
| Хук лидерборда | `frontend/src/hooks/useLeaderboard.ts` | `GET …/rounds/{rid}/leaderboard` (без авторизации); `enabled`, когда вкладка активна + тур `PUBLISHED` |
| Хук результатов | `frontend/src/hooks/useRoundResults.ts` | `GET …/rounds/{rid}/results`; отображает `points[]` → `match_points[]` |
| Маппер лидерборда | `frontend/src/lib/leaderboard/mapLeaderboardRow.ts` | API `ScoreDetail` + место → строка таблицы; столбцы count из B4 опциональны |
| Маппер результатов | `frontend/src/lib/results/mapRoundResultsRow.ts` | `base_points` по матчу в порядке `matches[]`; `total_without_bonus3` → `total_without_bonus` |
| Публичный шлюз | `frontend/src/lib/contest/roundPublicVisibility.ts` + `roundResultsGuard.ts` | Загрузка только когда `status === 'PUBLISHED'`; иначе заготовка, без сетевых запросов |
| UI-заготовка | `frontend/src/components/contest/ResultsUnavailableMessage.tsx` | `data-testid="results-unavailable"`; текст `ROUND_NOT_PUBLISHED_COPY` |
| Подключение страницы | `frontend/src/app/contest/[contestId]/page.tsx` | Удалён `contestDisplayMock`; состояния loading/error/bonuses_pending |

**Тексты (RU):**

| Условие | Сообщение |
|-----------|---------|
| Тур не в статусе `PUBLISHED` | «Будет доступно после проверки организатором» |
| Пустой `points[]` после загрузки | «Не удалось загрузить очки по матчам» |
| `bonuses_pending` | `BONUSES_PENDING_FALLBACK_MESSAGE` (янтарный баннер) |

**Отложено:** кэширование ETag `If-None-Match` для лидерборда/результатов (заготовка `lib/api/cache.ts` остаётся); переключатель глобального лидерборда «Общий» в `RoundSelector`.

**Тесты:** `mapLeaderboardRow.test.ts`, `mapRoundResultsRow.test.ts`, `roundResultsGuard.test.ts` (+ существующий `roundPublicVisibility.test.ts`).

---

## Журнал изменений

| Дата | Этап | Описание |
|------|-------|---------|
| 2026-06-24 | 2.1 / 2.1.1 | Базовый shell, маршруты авторизации, заготовки admin |
| 2026-06-24 | 2.3 | Полный UI организатора: настройки, туры, результаты, жизненный цикл, логотип B5 |
| 2026-06-27 | 2.3.2 | Редактирование только расписания на `ACTIVE`, подтверждения статуса матча, защита от пустого счёта в результатах |
| 2026-06-28 | 2.2 | Форма прогноза, матрица приватности, UX дедлайна, вкладка конкурса «Прогнозы» |
| 2026-07-08 | 2.4 | Подключение публичного API лидерборда/результатов; шлюз `PUBLISHED`; удалён мок со страницы конкурса |
