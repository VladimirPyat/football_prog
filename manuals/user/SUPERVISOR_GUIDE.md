# Инструкция для организатора

Пошаговое руководство для роли **SUPERVISOR** (организатор конкурса): настройка, туры, результаты, публикация.

> **Статус:** черновик. Скриншоты — плейсхолдеры (жёлтые блоки `📷 СКРИН`). После съёмки замените блок на `![описание](assets/имя-файла.png)`. Чеклист файлов: [assets/SCREENSHOTS.md](assets/SCREENSHOTS.md).

**Вход:** `/staff/login` → логин организатора → рабочая область `/admin/*`.

**Связанные документы:** продуктовая спека [`docs/04_supervisor_scenario.md`](../../docs/04_supervisor_scenario.md) · QA-чеклист [SUPERVISOR_TESTING_SCENARIOS.md](../testing/SUPERVISOR_TESTING_SCENARIOS.md) · [FRONTEND_REFERENCE.md](../dev/FRONTEND_REFERENCE.md)

---

## Общие правила

- Все операции — через UI или API, **без прямого SQL**.
- После **первой активации тура** конкурс **блокируется** (`is_locked`): параметры, состав команд и участников менять нельзя.
- **Дедлайн** на активном туре: изменение возможно только пока до текущего дедлайна остаётся не менее **24 часов** (правило `deadline_rule_hours`).
- Пути `/admin/*` — историческое имя UI организатора; доступны роли `SUPERVISOR` и Support.

---

## 1. Настройка конкурса

Верхнее меню: **Настройки** · **Туры** · **Рассылки** · **Результаты**.

### 1.1. Параметры конкурса

**URL:** `/admin/settings/parameters`

Отображаются (после старта — **только чтение**):

- число команд (по умолчанию 16), туров (30), матчей в туре (8);
- формула очков (12 / 8 / 4);
- правила бонусов 1–3 и пороги.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-01-parameters.png"><code>assets/supervisor-01-parameters.png</code></a> — параметры конкурса (readonly после старта)
</span></p>

### 1.2. Участники

**URL:** `/admin/settings/participants`

| Элемент | Описание |
|---------|----------|
| Таблица | Имя, email, статус («Ожидаем» / «Принято») |
| **До старта** | Добавить email → «Выслать приглашение» → временный пароль |
| **После старта** | Кнопки «Добавить» / «Удалить» неактивны |

> **Важно:** перед активацией **первого тура** подтвердите всех участников — иначе неподтверждённые (`PENDING`) будут удалены.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-02-participants.png"><code>assets/supervisor-02-participants.png</code></a> — таблица участников
</span></p>

### 1.3. Команды

**URL:** `/admin/settings/teams`

- Таблица: название, сокращение, логотип.
- **До старта** — можно добавлять команды и загружать логотипы.
- **После старта** — «Добавить команду» неактивна (кроме настраиваемых исключений для кубков).

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-03-teams.png"><code>assets/supervisor-03-teams.png</code></a> — сетка команд
</span></p>

### 1.4. Рассылки

**URL:** `/admin/newsletters`

Планируемый функционал (Stage 3):

- список рассылок: тип, текст, дата, статус;
- создание «Разово» / «По расписанию» с подстановками `{tournament_name}`, `{round_number}`, `{deadline_date}`;
- шаблон «Напоминание о дедлайне» за 1 / 2 / 3 суток.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-04-newsletters.png"><code>assets/supervisor-04-newsletters.png</code></a> — раздел «Рассылки» (текущее состояние UI)
</span></p>

---

## 2. Туры и расписание

**URL:** `/admin/rounds`

### 2.1. Создание тура (DRAFT)

1. Выберите номер тура (1–30).
2. Задайте **дедлайн** (datetime picker). При создании: `сейчас < дедлайн < время первого матча`.
3. Добавьте матчи:
   - **«Загрузить по API»** — внешнее расписание;
   - **«Добавить матч»** — вручную (команды, дата/время).
4. Ограничения: **не более 8 матчей**, каждая команда — **не более одного раза** в туре.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-05-rounds-draft.png"><code>assets/supervisor-05-rounds-draft.png</code></a> — тур в статусе DRAFT
</span></p>

### 2.2. Активация тура

1. Проверьте матчи и дедлайн.
2. Нажмите **«Активировать»** (или аналог).
3. Подтвердите модалку: после активации **редактирование настроек конкурса запрещено**.
4. Статус тура: `DRAFT` → `ACTIVE`. При первой активации конкурс переходит в `RUNNING`, `is_locked = true`.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-07-rounds-activate-modal.png"><code>assets/supervisor-07-rounds-activate-modal.png</code></a> — модалка предупреждения при активации
</span></p>

### 2.3. Редактирование ACTIVE-тура (до дедлайна)

**Разрешено:**

- смена домашней / гостевой команды;
- дата и время матча;
- статус матча: «Состоится» / «Перенесён» / «Отменён».

**Запрещено:**

- добавлять или удалять матчи;
- менять дедлайн, если до текущего дедлайна осталось **менее 24 часов**.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-06-rounds-active.png"><code>assets/supervisor-06-rounds-active.png</code></a> — редактор ACTIVE-тура
</span></p>

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-12-deadline-24h.png"><code>assets/supervisor-12-deadline-24h.png</code></a> — ошибка при попытке сменить дедлайн &lt;24 ч
</span></p>

### 2.4. Свободный тур (Free Tour)

Для перенесённых матчей (`POSTPONED`):

1. Нажмите **«Свободный тур»**.
2. В модалке выберите матчи из разных туров.
3. Укажите новую дату/время (команды не меняются).
4. Активируйте — матчи переносятся в отдельный тур и исчезают из исходного.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-08-rounds-free-tour.png"><code>assets/supervisor-08-rounds-free-tour.png</code></a> — модалка «Свободный тур»
</span></p>

---

## 3. Результаты и публикация

**URL:** `/admin/results`

### 3.1. Ввод счётов

1. Выберите **завершённый** тур (`CLOSED` — дедлайн прошёл).
2. Для каждого матча введите счёт (0–20) и статус **«Завершён»**.
3. Нажмите **«Применить результаты»**.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-09-results-enter.png"><code>assets/supervisor-09-results-enter.png</code></a> — ввод результатов матчей
</span></p>

### 3.2. После применения

Система автоматически:

- блокирует введённые счета;
- запускает **пакетный расчёт** очков;
- обновляет лидерборд;
- переводит тур: `CLOSED` → `CALCULATED` → `PUBLISHED`.

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-10-results-applied.png"><code>assets/supervisor-10-results-applied.png</code></a> — результаты применены, поля заблокированы
</span></p>

### 3.3. Отмена матча (VOID)

Если матч признан несостоявшимся **после** ввода результата:

1. Нажмите **«Отменить»** у матча.
2. Подтвердите в диалоге.
3. Статус: `FINISHED` → `VOID`, очки за матч = 0, лидерборд пересчитывается.

> Вернуть `FINISHED` из UI нельзя — только через Support (техподдержка).

<p><span style="display:inline-block;background:#fff3cd;color:#664d03;padding:6px 12px;border-radius:4px;border:1px solid #ffc107">
📷 <strong>СКРИН:</strong> <a href="assets/supervisor-11-results-void.png"><code>assets/supervisor-11-results-void.png</code></a> — подтверждение отмены матча (VOID)
</span></p>

---

## 4. Жизненный цикл (кратко)

```text
Тур:     DRAFT → ACTIVE → CLOSED → CALCULATED → PUBLISHED
Конкурс: DRAFT → RUNNING (при первой активации тура, is_locked=true)
```

| Статус тура | Что можно |
|-------------|-----------|
| `DRAFT` | Редактировать состав, дедлайн, активировать |
| `ACTIVE` | Участники сдают прогнозы; ограниченное редактирование матчей |
| `CLOSED` | Дедлайн прошёл; ввод результатов |
| `CALCULATED` | Очки посчитаны, ожидает публикации |
| `PUBLISHED` | Данные видны участникам на вкладках «Прогнозы» / «Результаты» |

Подробнее: [STATUS_REFERENCE.md](../dev/STATUS_REFERENCE.md).

---

## 5. Частые вопросы

**Не могу добавить участника** — конкурс уже запущен (`is_locked`). Новых участников добавляет Support или нужно было пригласить до старта.

**Дедлайн не сохраняется** — проверьте правило 24 ч и что дедлайн раньше первого матча.

**Организатор хочет тоже играть** — заведите отдельный логин `USER` и пригласите его в конкурс.

**Нужен пересчёт / пауза / восстановление конкурса** — операции Support, не организатора. См. [API_GUIDE](../dev/API_GUIDE.md).

---

## Чеклист самопроверки

- [ ] Параметры и команды настроены до первой активации
- [ ] Все участники подтверждены до старта
- [ ] Тур создаётся с ≤8 матчами, команды уникальны в туре
- [ ] Активация тура блокирует настройки
- [ ] Правило 24 ч на дедлайн работает
- [ ] Результаты применяются и публикуются
- [ ] VOID обнуляет очки и пересчитывает таблицу
- [ ] Свободный тур забирает POSTPONED-матчи из исходного тура
