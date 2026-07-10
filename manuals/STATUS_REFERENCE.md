# Справочник статусов

Человекочитаемое описание статусов конкурса, тура и матча: что означает каждое значение, как оно меняется и где реализовано в коде.

> **Важно:** в API и БД всегда используются **английские** значения (`ACTIVE`, `CLOSED`, …). На фронте они переводятся в подписи для супервайзера и участника. Менять значения в API не нужно — меняются только **подписи в UI**.

См. также: [ARCHITECTURE.md](ARCHITECTURE.md#lifecycle-state-machines), [DB_REFERENCE.md](DB_REFERENCE.md), [API_GUIDE.md](API_GUIDE.md), контракт [contest_lifecycle_flow.md](../agent_docs/contracts/contest_lifecycle_flow.md).

---

## 1. Конкурс (`contests.status`)

Отдельно от статуса смотрите флаг **`is_locked`**: после первой активации тура параметры конкурса (команды, правила, участники) больше не редактируются, даже пока конкурс «идёт».

| API | Подпись в UI (сейчас) | Что это значит |
|-----|----------------------|----------------|
| `DRAFT` | Черновик / «Настройка» | Конкурс создан, но ещё не запущен. Можно менять параметры, команды, приглашать участников. |
| `RUNNING` | Идёт | Рабочий режим: прогнозы, туры, результаты, расчёт очков. |
| `PAUSED` | Приостановлен | Все изменяющие операции заблокированы; публичное чтение (таблица, туры) доступно. Нужен перед безопасным удалением конкурса. |
| `FINISHED` | Завершён | Конкурс досрочно завершён; мутации запрещены (кроме Support-пересчёта по политике API). |

### Переходы

```
DRAFT ──(первая активация тура)──► RUNNING ──pause──► PAUSED
                                      │                  │
                                      │             resume│
                                      └──finish──────────┴──► FINISHED
```

При **первой активации любого тура**: `is_locked = true`, `status` становится `RUNNING`.

### Где в коде

| Слой | Файл | Назначение |
|------|------|------------|
| Модель / enum | `src/database/models.py` → `ContestLifecycleStatus` | Допустимые значения + CHECK в БД |
| Сервис | `src/services/contest_lifecycle_service.py` | `pause_contest`, `resume_contest`, `finish_contest`, `assert_contest_running` |
| API | `src/api/v1/contest_lifecycle.py` (и contest-scoped аналоги) | `POST …/pause`, `…/resume`, `…/finish` |
| Создание | `src/services/contest_setup_service.py` | Новый конкурс всегда в `DRAFT` |
| Фронт — типы | `frontend/src/types/api.ts` → `ContestStatus` | TypeScript union |
| Фронт — список | `frontend/src/components/contest/ContestList.tsx` → `STATUS_LABELS` | Подписи в списке конкурсов |
| Фронт — панель организатора | `frontend/src/lib/admin/deriveAdminUiMode.ts` | Баннеры паузы/завершения, блокировка кнопок |
| Фронт — действия | `frontend/src/components/admin/ContestLifecycleActions.tsx` | Пауза / возобновление |
| Фронт — баннер | `frontend/src/components/admin/ContestStatusBanner.tsx` | «Конкурс на паузе» / завершён |

---

## 2. Тур (`rounds.status`)

Статус **тура** не путать со статусом **конкурса**. Тур «Черновик» (`DRAFT`) может существовать при уже запущенном конкурсе (`RUNNING`).

### Жизненный цикл

```
DRAFT ──activate──► ACTIVE ──дедлайн прошёл + close──► CLOSED
                                                      │
                                            calculate ▼
                                                 CALCULATED
                                                      │
                                              publish ▼
                                                 PUBLISHED
```

**Автозакрытие:** при каждом contest-scoped запросе API вызывается `auto_close_expired_rounds`: если тур `ACTIVE` и `now >= deadline`, статус становится `CLOSED` (то же, что ручной `POST …/close`).

### Таблица статусов

| API | Подпись в UI **сейчас** | **Рекомендуемая** подпись | Что это значит для супервайзера |
|-----|-------------------------|---------------------------|----------------------------------|
| `DRAFT` | Черновик | Черновик | Тур собран (матчи, дедлайн), но участники **ещё не** принимают прогнозы. Можно активировать. |
| `ACTIVE` | Активен | Приём прогнозов *(опционально)* | Участники заполняют прогнозы до поля `deadline`. |
| `CLOSED` | Закрыт | **Дедлайн** | Дедлайн прогнозов прошёл. Прогнозы закрыты; на вкладке **Результаты** вводятся счёта матчей. |
| `CALCULATED` | Рассчитан | Рассчитан | Очки посчитаны (`POST …/calculate`). Можно **исправить счёт** на «Результаты» (авто-пересчёт) или **опубликовать** тур в общую таблицу. |
| `PUBLISHED` | Опубликован | Опубликован | Тур **подтверждён**; публичная таблица и матрица результатов **доступны** участникам и гостям. |

### 2.3 Видимость таблицы и результатов (политика продукта)

| Аудитория | Статусы тура | Поведение |
|-----------|--------------|-----------|
| Участник (`USER`), гость | только `PUBLISHED` | `GET …/leaderboard`, `GET …/results` — данные; иначе заглушка |
| Участник, гость | `CALCULATED`, `CLOSED`, `ACTIVE`, `DRAFT` | UI: **«Будет доступно после проверки организатором»**; не вызывать публичные LB/results |
| Супервайзер (`/admin/rounds`) | `CALCULATED` | **Предпросмотр** таблицы тура перед «Опубликовать» |
| Супервайзер | `CLOSED` | Ввод счетов матчей; очки в `scores` ещё нет |

> **Важно — два слоя данных:**
> - **`CALCULATED`** — очки уже в таблице `scores` (после «Рассчитать»), но **не показываются публично** до `PUBLISHED`.
> - **`PUBLISHED`** — супервайзер нажал «Опубликовать»; тот же `scores`, тур открыт для всех.

**Реализация (Stage 2.3.1) [UPDATED]:**

| Слой | Файл | Правило |
|------|------|---------|
| Backend | `src/services/leaderboard_service.py` | `_allowed_round_statuses`: публичный GET — только `PUBLISHED`; для `SUPERVISOR`/Support (ADMIN) — также `CALCULATED` (preview) |
| Backend | `get_global_leaderboard` | Агрегировать только туры `PUBLISHED` |
| Backend | `contest_ops.py`, `admin_misc.py` | Optional Bearer → `viewer_role` на round LB/results |
| Frontend | `frontend/src/lib/contest/roundPublicVisibility.ts` | `isRoundPubliclyVisible(status) => status === 'PUBLISHED'` |
| Frontend | Leaderboard / Results (2.4+) | Проверка статуса **до** fetch; иначе stub |

### 2.4 Правило дедлайна и редактирование тура [UPDATED]

| Правило | Где | Смысл |
|---------|-----|-------|
| **Размещение дедлайна** | `validate_round_deadline_placement` | `now < deadline < первый_матч` — при создании тура и смене дедлайна |
| **24h lockout** | `assert_deadline_change_allowed` | На **ACTIVE** туре: менять дедлайн можно только пока `now <= deadline - deadline_rule_hours` (по умолчанию 24 ч) |
| **Редактирование тура** | `PATCH …/admin/rounds/{id}` | Допустимо в `DRAFT` или `ACTIVE` |
| **Состав после дедлайна** | тот же PATCH | На **ACTIVE** после `now >= deadline`: нельзя менять `team1_id` / `team2_id` |
| **Даты матчей** | `POST …/admin/rounds` | Дата матча не может быть в прошлом |

**Before → After:** `deadline_rule_hours` больше **не** требует ставить дедлайн за N часов до первого матча — только ограничивает **окно изменения** дедлайна на активном туре. См. [API_GUIDE.md](API_GUIDE.md#round_servicepy-updated).

### 2.5 Расписание матчей на ACTIVE туре (frontend, Stage 2.3.2) [NEW]

| Действие | Условие | UI |
|----------|---------|-----|
| Смена команд | Запрещено после активации тура | Селекты команд только в `DRAFT` |
| Перенос времени (несколько часов) | До `date_time` матча | `datetime-local` + «Сохранить»; предупреждение при сдвиге ≥ 7 суток |
| Отмена (`CANCELED`) | Пока матч не `CANCELED`/`FINISHED`/`VOID` | Статус в `<select>` → подтверждение → PATCH |
| Перенос (`POSTPONED`) | Из `SCHEDULED` | Статус в `<select>` → подтверждение → PATCH → модалка свободного тура |
| Восстановление (`SCHEDULED`) | Только **Support (ADMIN)** из `CANCELED`/`POSTPONED` | Статус в `<select>` → подтверждение |

Правила: `frontend/src/lib/admin/matchScheduleEdit.ts`. Ввод счёта на «Результаты»: пустые поля ≠ 0 (`matchResultSchema` без `z.coerce` на пустую строку).

### Dev fixture (после `dev_setup` + `finalize_dev_fixture`, Stage 1.14)

Справочная дата для дедлайнов: **2026-06-27** UTC.

| Тур | `rounds.status` | `scores` | Назначение для ручного QA |
|-----|-----------------|----------|---------------------------|
| 1–9 | `PUBLISHED` | 10 × 9 = 90 | Публичная история / leaderboard |
| 10 | `CALCULATED` | 10 | Предпросмотр супервайзера; публикация вручную |
| 11 | `CLOSED` | 0 | Ввод результатов → «Рассчитать» (см. `coder_2.3.1_fix` §9.9) |

Скрипт: `src/scripts/finalize_dev_fixture.py`; вызывается из `dev_setup.py` (не из `load_test_data.py`, чтобы pytest оставался на `CLOSED` 1–9).

> **Запланированное изменение UI:** для API-значения `CLOSED` показывать **«Дедлайн»**, а не «Закрыт» — точнее отражает фазу «дедлайн прошёл, ждём счета». В БД и API остаётся `CLOSED`.

### Что можно делать в каждой фазе (кратко)

| Статус | Прогнозы участников | Редактирование тура (панель организатора) | Результаты |
|--------|---------------------|------------------------------|------------|
| `DRAFT` | Нет | Полное (матчи, команды, дедлайн) | Нет |
| `ACTIVE` | Да, пока `now < deadline` | **Frontend [UPDATED]:** состав матчей (команды) **не редактируется** — только расписание: перенос времени до начала матча (независимо от дедлайна прогнозов), отмена (с подтверждением), статус «Перенесён» + свободный тур; восстановление `CANCELED`/`POSTPONED` → `SCHEDULED` — только **Support (ADMIN)**. Кнопка «Сохранить» не блокируется 24h lockout дедлайна, если меняли только матчи. **Backend:** PATCH отклоняет смену команд на ACTIVE туре. | Нет |
| `CLOSED` | Нет | Только просмотр на «Туры» | Ввод счёта |
| `CALCULATED` | Нет | Только просмотр | Правка счёта + авто-пересчёт, публикация / VOID |
| `PUBLISHED` | Нет | Только просмотр | Только VOID (с пересчётом) |

Подробная матрица операций: [contest_lifecycle_flow.md](../agent_docs/contracts/contest_lifecycle_flow.md).

### Где в коде

| Слой | Файл | Назначение |
|------|------|------------|
| Модель / enum | `src/database/models.py` → `RoundStatus` | Пять значений статуса тура |
| Машина состояний | `src/services/round_service.py` → `transition_round`, `close_round`, `set_deadline` | Допустимые переходы; активация ставит `contest.is_locked` |
| Автозакрытие | `src/services/round_auto_close_service.py` | `ACTIVE → CLOSED` по дедлайну |
| Расчёт / публикация | `src/services/scoring_persistence.py` | `CLOSED → CALCULATED`, публикация `→ PUBLISHED` |
| API (legacy shim) | `src/api/v1/admin_rounds.py` | `POST create`, `PATCH`, `activate`, `close`, `calculate`, `publish` |
| API (contest-scoped) | `src/api/v1/contest_ops.py` | Те же операции с `{contest_id}` |
| Прогнозы | `src/services/prediction_service.py` | Требует `round.status == ACTIVE` и `now < deadline` |
| Фронт — подписи | `frontend/src/lib/admin/format.ts` → `roundStatusLabel()` | **Единая точка** для русских названий тура |
| Фронт — E2E дубль | `frontend/e2e/fixtures/adminApi.ts` → `ROUND_STATUS_LABELS` | Должен совпадать с `format.ts` после смены подписей |
| Фронт — режим UI | `frontend/src/lib/admin/deriveAdminUiMode.ts` | `canEditRoundStructure` (DRAFT only), `canEditMatchStatusAndDate`, … |
| Фронт — расписание ACTIVE | `frontend/src/lib/admin/matchScheduleEdit.ts` | Kickoff reschedule, cancel/postpone rules [NEW] |
| Фронт — строка матча | `frontend/src/components/admin/MatchEditorRow.tsx` | Status `<select>`, confirm on CANCELED/POSTPONED/restore [UPDATED] |
| Фронт — страница | `frontend/src/components/admin/RoundManagementPanel.tsx` | Список туров, редактор, активация |
| Фронт — карточка | `frontend/src/components/admin/RoundStatusSidebar.tsx` | Бейдж статуса, «Закрыть тур», список матчей |
| Фронт — результаты | `frontend/src/components/admin/ResultsEntryPanel.tsx` | Выпадающий список туров `CLOSED` / `CALCULATED` / `PUBLISHED` |

### Смена подписи `CLOSED` → «Дедлайн»

При правке фронта обновить:

1. `frontend/src/lib/admin/format.ts` — `roundStatusLabel`
2. `frontend/e2e/fixtures/adminApi.ts` — `ROUND_STATUS_LABELS` (если тесты ищут текст «Закрыт», обновить селекторы)
3. При необходимости — подсказки в `RoundStatusSidebar` (фаза «дедлайн прошёл — введите результаты»)

---

## 3. Матч (`matches.status`)

Статус отдельного матча в туре. Не путать со статусом тура: матч может быть `POSTPONED` внутри тура `ACTIVE` или `CLOSED`.

| API | Подпись в UI | Что это значит |
|-----|--------------|----------------|
| `SCHEDULED` | Запланирован | Матч в расписании тура; игра ещё не сыграна (или счёт не внесён). Стартовое значение при создании тура. |
| `POSTPONED` | Перенесён | Матч перенесён на другую дату **в рамках операционки тура** (супервайзер на «Туры»). Такой матч можно включить в **свободный тур** (Free Tour). |
| `CANCELED` | Отменён | Матч в туре отменён **до/без** финального счёта; не играется в этом туре. Участвует в расчёте как отменённый (без очков за исход). |
| `VOID` | Аннулирован | Матч **аннулирован после ввода результата** (на вкладке «Результаты»). Очки за матч обнуляются; при статусе тура `CALCULATED` запускается пересчёт тура. |
| `FINISHED` | Завершён | Финальный счёт внесён (`score1`, `score2`); матч учтён при расчёте очков. |

### Отменён vs аннулирован

| | `CANCELED` | `VOID` |
|---|------------|--------|
| **Где меняют** | Страница **Туры** (редактор матча) | Страница **Результаты** (кнопка с подтверждением) |
| **Когда** | До/вместо игры, без финального счёта | После того как результат уже был внесён |
| **Пересчёт тура** | При следующем `calculate` | Сразу, если тур уже `CALCULATED` |

### Где в коде

| Слой | Файл | Назначение |
|------|------|------------|
| Модель / enum | `src/database/models.py` → `MatchStatus` | Пять значений |
| Результат + FINISHED | `src/services/match_service.py` → `set_result` | При `round.status` `CLOSED` или `CALCULATED` и `now >= deadline`; на `CALCULATED` — авто `recalculate_round` |
| Статус POSTPONED / CANCELED / VOID | `src/services/match_service.py` → `change_status` | PATCH статуса; VOID на `CALCULATED` → `recalculate_round` |
| API | `src/api/v1/admin_matches.py`, `contest_ops.py` | `PUT …/result`, `PATCH …/status` |
| Фронт — подписи | `frontend/src/lib/admin/format.ts` → `matchStatusLabel()` | Русские названия |
| Фронт — туры | `frontend/src/components/admin/MatchEditorRow.tsx` | Select статуса: `POSTPONED`, `CANCELED` |
| Фронт — результаты | `frontend/src/components/admin/MatchResultRow.tsx` | Отображение статуса, VOID |
| Фронт — типы | `frontend/src/types/api.ts` → `MatchStatus` | TypeScript union |

---

## 4. Сводка: API ↔ UI (туры и матчи)

Единый источник подписей для панели организатора — **`frontend/src/lib/admin/format.ts`**.

### Туры — текущее и целевое

| API | UI сейчас | UI целевое |
|-----|-----------|------------|
| `DRAFT` | Черновик | Черновик |
| `ACTIVE` | Активен | Активен *(или «Приём прогнозов» — на усмотрение)* |
| `CLOSED` | Закрыт | **Дедлайн** |
| `CALCULATED` | Рассчитан | Рассчитан |
| `PUBLISHED` | Опубликован | Опубликован |

### Матчи

| API | UI |
|-----|-----|
| `SCHEDULED` | Запланирован |
| `POSTPONED` | Перенесён |
| `CANCELED` | Отменён |
| `VOID` | Аннулирован |
| `FINISHED` | Завершён |

---

## 5. Связанные статусы (кратко)

| Объект | Поле | Значения | Где подписи |
|--------|------|----------|-------------|
| Участник конкурса | `contest_participants.status` | `PENDING`, `ACCEPTED` | `participantStatusLabel()` в `format.ts` |
| Глобальная роль | `users.role` | `USER`, `SUPERVISOR`, `ADMIN` (support) | Не статусная машина; RBAC в API |

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2026-06-27 | Первоначальная версия; рекомендация `CLOSED` → «Дедлайн» в UI |
| 2026-06-27 | §2.3: публичный LB/results только при `PUBLISHED`; stub «Будет доступно после проверки организатором» |
| 2026-06-27 | §2.3.1: backend visibility реализован; §2.4: правило дедлайна (placement vs 24h lockout), PATCH тура в DRAFT/ACTIVE |
| 2026-06-27 | §2.5 + ACTIVE matrix: frontend schedule-only on ACTIVE; `set_result` on CALCULATED + auto-recalc (backend) |
