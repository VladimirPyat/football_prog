# Логика начисления очков

Правила начисления очков конкурса, бонусы, тай-брейки и реализация движка.

## Содержание

- [Статус реализации](#статус-реализации)
- [Источник конфигурации](#источник-конфигурации)
- [Архитектура движка](#архитектура-движка)
- [Базовые очки](#базовые-очки)
- [Бонусы](#бонусы)
- [Порядок вычислений](#порядок-вычислений)
- [Ранг за тур](#ранг-за-тур)
- [Тай-брейки и итоговая таблица](#тай-брейки-и-итоговая-таблица)
- [Сохранение результатов начисления](#сохранение-результатов-начисления)
- [Ограничения валидации](#ограничения-валидации)
- [Правило отсутствия прогноза](#правило-отсутствия-прогноза)

## Статус реализации [UPDATED]

| Слой | Статус |
|-------|--------|
| Правила хранятся в БД (`contests.rules_json`) | ✅ Заполняются через [CONFIG.md](../setup/CONFIG.md) |
| Чистый движок начисления очков (`src/scoring/`) | ✅ Этап 1.1 — реализован и проверен (90/90) |
| Сохранение результатов начисления (`src/services/scoring_persistence.py`) | ✅ Этап 1.2 — реализовано и проверено (90/90) |
| Сервис лидерборда (`src/services/leaderboard_service.py`) | ✅ Этап 1.3 — агрегирует очки + тай-брейк [NEW] |
| Эндпоинты API (`/leaderboard`, `/results`) | ✅ Этап 1.3 — см. [API_GUIDE.md](API_GUIDE.md) [UPDATED] |

## Источник конфигурации [UPDATED]

Значения по умолчанию из `config/contest_defaults.json`, сохраняются `src/scripts/seed.py` в `contests.rules_json`.

Путь доступа во время выполнения:

```
contests.rules_json → ScoringRules accessor → score_round() → Score rows in DB
```

Схему таблицы `scores` см. в [DB_REFERENCE.md](DB_REFERENCE.md).

## Архитектура движка [NEW]

Движок начисления очков — это **чистый Python-модуль** без зависимостей от базы данных или I/O. Все числовые константы читаются из словаря `rules` через `ScoringRules`.

| Файл | Роль |
|------|------|
| `src/scoring/types.py` | Датаклассы входа/выхода: `MatchResult`, `UserPrediction`, `UserRoundScore`, `StandingRow`, перечисление `Category` |
| `src/scoring/rules.py` | `ScoringRules` — типизированный доступ к `rules_json`; без магических чисел в коде движка |
| `src/scoring/engine.py` | `score_round(results, predictions, participant_ids, rules) → dict[user_id, UserRoundScore]` |
| `src/scoring/standings.py` | `build_standings(per_user_rounds, manual_overrides) → list[StandingRow]` |

### Основные типы

```python
@dataclass(frozen=True)
class UserRoundScore:
    user_id: int
    base_points: int
    count_exact_high: int   # exclusive hit counts (frequency, not points)
    count_exact: int
    count_diff: int
    count_outcome: int
    correct_outcomes: int   # base_points >= 4
    bonus1: int
    bonus2: int
    bonus3: int
    total_without_bonus3: int   # base + bonus1 + bonus2
    total_with_bonus3: int      # + bonus3
    round_rank: int             # dense rank within the round
    per_match: tuple[MatchScore, ...]

@dataclass
class StandingRow:
    user_id: int
    total_points: int
    exact_scores_count: int       # sum of exact_high + exact across rounds
    total_without_bonuses: int    # sum of base_points only
    correct_diffs_count: int
    exact_high_count: int; exact_count: int; diff_count: int; outcome_count: int
    total_predictions: int
    rank: int
    tiebreaker_status: str | None  # "manual_override" when manual key decided order
```

## Базовые очки [UPDATED]

Одна эксклюзивная категория на матч. `sign(x) = 1 / 0 / -1`.

| Категория | Ключ | Очки | Условие |
|----------|-----|--------|-----------|
| `EXACT_HIGH` | `exact_high_score` | 16 | `p==r` AND (`abs(r1-r2) >= 3` OR `r1+r2 > 3`) |
| `EXACT` | `exact_score` | 12 | `p==r`, не high |
| `DIFF` | `diff_plus_outcome` | 8 | `sign(p1-p2)==sign(r1-r2)` AND одинаковая абсолютная разница |
| `OUTCOME` | `outcome_only` | 4 | только `sign(p1-p2)==sign(r1-r2)` |
| `MISS` | `miss` | 0 | Иначе |

**Примеры:**
- прогноз `2:1`, результат `2:1` → `EXACT` (12 очков; diff=1, sum=3 — не high)
- прогноз `3:0`, результат `3:0` → `EXACT_HIGH` (16 очков; diff=3 ≥ 3)
- прогноз `2:1`, результат `3:2` → `DIFF` (8 очков; оба +1)
- прогноз `2:0`, результат `3:0` → `OUTCOME` (4 очка; тот же знак, другая разница)
- прогноз `0:0`, результат `0:0` → `EXACT` (12 очков; 0:0 — реальный счёт, а не отсутствие прогноза)

Настраивается через `rules_json.scoring_rules.base_points`.

## Бонусы [UPDATED]

Применяются сверх базовых очков. Значения по умолчанию из seed см. в [CONFIG.md](../setup/CONFIG.md).

### Бонус 1 — уникальный верный исход (`bonus_1_unique_multiplier_pct`)

- **Область:** на матч, суммируется по туру.
- **Условие:** ровно один участник спрогнозировал исход (HOME/DRAW/AWAY), который действительно произошёл. Этот участник получает `int(base_pts * pct / 100)`.
- **Уникальность:** по **исходу** (1/X/2), а НЕ по точному счёту.
- **Множитель по умолчанию:** `200.0` → бонус = 2 × базовые очки за этот матч.
- **Защита:** пользователь должен фактически спрогнозировать этот матч (отсутствие прогноза = без бонуса, без штрафа).

### Бонус 2 — серия верных исходов (`bonus_2_thresholds`)

- **Область:** на тур.
- **Условие:** количество матчей, где `base_points >= 4` (исход угадан верно).
- **Пороги по умолчанию** (действует наибольший подходящий):

| Мин. верных исходов | Бонусные очки |
|---------------------|--------------|
| 6 | 8 |
| 7 | 12 |
| 8 | 16 |

### Бонус 3 — место в туре + бонус за высокий счёт (`bonus_3_rank_points`)

- **Область:** на тур.
- **База для ранжирования:** `basis = base + bonus1 + bonus2` (без самого bonus3).
- **Защита:** `base_points == 0` → `bonus3 = 0` (без места, без надбавки).
- **Место:** по **уникальным** значениям `basis` по убыванию; при равенстве пользователи делят место.

| Место | Бонусные очки |
|-------|--------------|
| 1-е | 12 |
| 2-е | 8 |
| 3-е | 4 |

- **Надбавка:** `+4`, если `basis >= bonus_3_base_threshold_extra` (по умолчанию 50).
- `bonus3 = rank_pts + extra`

**Пример расчёта (тур 1):**
- starchenkov_c: basis=56 → 1-е место → 12 + надбавка(+4) = **16**
- shutov: basis=44 → 2-е место → 8 (без надбавки) = **8**
- kuznetsov: basis=36 → 3-е место (делит с russkov) → 4 = **4**
- russkov: basis=36 → 3-е место (делит) → 4 = **4**

## Порядок вычислений [NEW]

В рамках тура, строго по порядку:
1. Базовые очки + счётчики категорий по паре (пользователь, матч)
2. Бонус 1 (требует прогнозы всех пользователей для проверки уникальности по матчу)
3. Бонус 2 (требует количество `correct_outcomes` по пользователю)
4. Бонус 3 (требует `basis = base + bonus1 + bonus2` для ВСЕХ пользователей → ранжирование)
5. Итоги: `total_without_bonus3 = base + bonus1 + bonus2`; `total_with_bonus3 = + bonus3`
6. Плотный (dense) ранг тура по `total_with_bonus3`

При VOID или изменении результата: полный пересчёт тура выполняется в одной атомарной транзакции.

## Ранг за тур [NEW]

`round_rank` использует **плотное ранжирование (dense ranking)** по `total_with_bonus3` по убыванию:
- Равные суммы → одинаковый ранг
- Следующая отличающаяся меньшая сумма → rank + 1 (а не rank + количество равных)
- Пример: суммы 30, 20, 20, 10 → ранги **1, 2, 2, 3**
- Тай-брейков на уровне тура нет (тай-брейки применяются только к итоговой таблице)
- Участники без прогнозов включаются и получают последний ранг

## Тай-брейки и итоговая таблица [UPDATED]

`build_standings()` в `src/scoring/standings.py`. Применяются последовательно — каждый следующий ключ разрешает равенство по всем предыдущим:

1. `total_points DESC` — сумма `total_with_bonus3` по всем турам
2. `exact_scores_count DESC` — сумма `count_exact_high + count_exact`
3. `total_without_bonuses DESC` — сумма только `base_points` (без бонусов)
4. `correct_diffs_count DESC` — сумма `count_diff`
5. `manual_override DESC` — `contest_participants.exceptional_tiebreak_points` (задаётся администратором в рамках конкурса; по умолчанию 0) [UPDATED]

**Было → Стало:** критерий 5 был в `users.exceptional_tiebreak_points` (этап 1.2.1). Этап 1.4 перенёс его в `contest_participants.exceptional_tiebreak_points` — для пользователя **в рамках конкретного конкурса**, может обновляться Поддержкой (SUPPORT) в любой момент (даже если конкурс заблокирован). `LeaderboardService` загружает участников конкурса и передаёт `manual_overrides` в `build_standings()`.

`tiebreaker_status = "manual_override"` устанавливается для строк, чья позиция определена критерием 5.

Ответы API лидерборда включают `exceptional_tiebreak_points` по каждой строке. См. [API_GUIDE.md](API_GUIDE.md#endpoints-reference).

> Бонусы влияют только на `total_points` (критерий 1); они исключены из критериев 2–4.

**Проверенные примеры тай-брейка (агрегат туров 1–9):**
- shutov (320 очков) против kurakov (320 очков) → shutov выигрывает по `exact_scores_count` 7 > 5
- volchenko (232 очка) против serov (232 очка) → volchenko выигрывает по `exact_scores_count` 5 > 4

<a id="scoring-persistence"></a>

## Сохранение результатов начисления [NEW]

`src/services/scoring_persistence.py` связывает чистый движок и базу данных.

```python
async def calculate_round(session, round_id) -> int   # CLOSED → CALCULATED
async def recalculate_round(session, round_id) -> int # re-run after VOID/result change
```

**Поток:**
1. Загрузить матчи `FINISHED` (счёт не NULL; `VOID`/`SCHEDULED` исключены) + все прогнозы + все ID участников из БД.
2. Преобразовать в типы движка (`MatchResult`, `UserPrediction`).
3. Вызвать `score_round(results, predictions, participant_ids, rules=contest.rules_json)`.
4. Отобразить `UserRoundScore` → строку БД `Score` (включая столбцы `count_*`).
5. Выполнить upsert всех строк в **одной атомарной транзакции**.
6. Перевести тур `CLOSED → CALCULATED`.

`recalculate_round` сначала удаляет существующие строки `Score` для тура, затем вставляет их заново — также атомарно.

<a id="validation-constraints"></a>

## Ограничения валидации [NEW]

Из `rules_json.constraints` (значения по умолчанию из seed):

| Ключ | По умолчанию | Значение |
|-----|---------|---------|
| `allow_partial_prediction_save` | `false` | Только пакетно: все матчи или ни одного |
| `require_all_matches_per_round` | `true` | Прогноз обязателен для каждого матча тура |
| `score_validation_range` | `[0, 20]` | Проверяется через DB CHECK — см. [DB_REFERENCE.md](DB_REFERENCE.md) |
| `max_teams_per_round_usage` | `1` | Команда встречается не более одного раза за тур |

Структурные ограничения из `contest_structure`:

| Ключ | По умолчанию | Значение |
|-----|---------|---------|
| `deadline_rule_hours` | `24` | **Только блокировка изменения** [UPDATED]: для тура в статусе `ACTIVE` организатор может изменить дедлайн через PATCH только при `now <= current_deadline - N часов`. **Не** требует, чтобы дедлайн был за N часов до первого матча. |
| `max_score_value` | `20` | Максимальный счёт матча (также проверяется на уровне API/БД) |

**Было → Стало (2026-06-27):** **установка** дедлайна при создании/PATCH не зависит от `deadline_rule_hours`: должно выполняться `now < deadline < earliest_match`. Значение 24 часа ограничивает **редактирование** существующего дедлайна на активных турах (`assert_deadline_change_allowed` в `round_service.py`). См. [API_GUIDE.md — round_service](API_GUIDE.md#round_servicepy-updated).

Валидация round-robin (когда `is_round_robin=true`):

- `matches_per_round == total_teams / 2`
- `total_rounds == (total_teams - 1) * 2`

## Правило отсутствия прогноза [UPDATED]

**Было → Стало:** правила существовали только в спецификации; теперь закреплены движком и слоем сохранения.

| Сценарий | Корректное представление |
|----------|------------------------|
| Игрок прогнозирует `0:0` | Строка с `score1=0, score2=0` |
| Игрок не сделал прогноз | **Отсутствие строки** в `predictions` |
| Игрок получает очки за матч | Только если строка прогноза существует и результат совпадает |

- `score_round()` использует только явные строки прогнозов; отсутствие никогда не трактуется как `0:0`.
- Проверено: у serov 0 строк прогнозов в туре 4, и он получает 0 очков за этот тур.
- Никогда не вставляйте NULL или 0 как признак отсутствующего прогноза.
