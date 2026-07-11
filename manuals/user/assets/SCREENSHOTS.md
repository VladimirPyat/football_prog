# Чеклист скриншотов

Сохраняйте PNG в эту папку (`manuals/user/assets/`). Рекомендуемый размер viewport: **1280×720**.

Перед съёмкой: `uv run python src/scripts/dev_setup.py --run` (API + frontend + dev-фикстура).

## Участник (`USER_GUIDE.md`)

| Файл | URL / состояние | Что должно быть видно |
|------|-----------------|----------------------|
| `user-01-leaderboard.png` | `/contest/1` → вкладка «Лидерборд» | Сводная таблица с очками |
| `user-02-predictions-tab.png` | `/contest/1` → «Прогнозы», опубликованный тур | Матрица прогнозов, шапка «Счёт» |
| `user-03-results-tab.png` | `/contest/1` → «Результаты», опубликованный тур | Фактические счета, очки по матчам |
| `user-04-login-modal.png` | `/` → кнопка «Вход» | Модалка: логин, пароль |
| `user-05-profile.png` | `/profile` (логин участника) | Меню слева, центральная область |
| `user-06-predict-empty.png` | `/contest/1/predict/{activeRoundId}` | Пустая форма, 8 матчей |
| `user-07-predict-filled.png` | тот же URL, все поля заполнены | Кнопка «Сохранить прогноз» активна |
| `user-08-predict-saved.png` | после сохранения | Кнопка «Редактировать» |
| `user-09-privacy-pre-deadline.png` | «Прогнозы», ACTIVE-тур до дедлайна | Свои счета видны, у других «Прогноз сделан» |
| `user-10-privacy-visitor.png` | «Прогнозы» без входа, до дедлайна | Заглушка «Будет доступно после дедлайна» |
| `user-11-predict-blocked.png` | форма прогноза после дедлайна | Поля readonly, кнопка неактивна |

## Организатор (`SUPERVISOR_GUIDE.md`)

| Файл | URL / состояние | Что должно быть видно |
|------|-----------------|----------------------|
| `supervisor-01-parameters.png` | `/admin/settings/parameters` | Параметры конкурса (readonly после старта) |
| `supervisor-02-participants.png` | `/admin/settings/participants` | Таблица участников, статусы |
| `supervisor-03-teams.png` | `/admin/settings/teams` | Сетка команд с логотипами |
| `supervisor-04-newsletters.png` | `/admin/newsletters` | Текущее состояние раздела рассылок |
| `supervisor-05-rounds-draft.png` | `/admin/rounds`, тур DRAFT | Конструктор тура, дедлайн, матчи |
| `supervisor-06-rounds-active.png` | `/admin/rounds`, тур ACTIVE до дедлайна | Редактор активного тура |
| `supervisor-07-rounds-activate-modal.png` | модалка при активации | Предупреждение о блокировке настроек |
| `supervisor-08-rounds-free-tour.png` | кнопка «Свободный тур» | Модалка выбора перенесённых матчей |
| `supervisor-09-results-enter.png` | `/admin/results`, тур CLOSED | Ввод счётов матчей |
| `supervisor-10-results-applied.png` | после «Применить результаты» | Заблокированные счета |
| `supervisor-11-results-void.png` | подтверждение VOID | Диалог отмены матча |
| `supervisor-12-deadline-24h.png` | попытка сменить дедлайн &lt;24 ч | Ошибка / disabled поле |
