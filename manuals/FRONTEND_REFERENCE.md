# Frontend Reference — Routes, Components & Editable Copy

Human-facing map of the Next.js UI: where routes live, which components implement each feature, and where **user-visible Russian copy** is defined. Use this to change labels, footers, banners, and button text **without searching the repo or asking an agent**.

> **Maintained by @Coder** at the end of each frontend sub-stage (append-only). Living specs remain in `agent_docs/ui/`; this file is the **quick edit guide** for humans.

---

## How to use

1. Find the **route** or **feature** in the tables below.
2. Open the **source file** (and line area if noted).
3. Edit string literals in JSX — UI copy is Russian unless noted.
4. Shared layout (header/footer) → start with **Layout & shell**.

---

## Layout & shell (cross-cutting)

| Area | Component | Source file | Editable copy (examples) |
|------|-----------|-------------|---------------------------|
| Public header/footer | `AppShell` | `frontend/src/components/layout/AppShell.tsx` | Brand «Sport Prognosis», «Вход», «Личный кабинет», «Управление», footer ©, «Вход для организаторов» |
| Login modal | `LoginModal` | `frontend/src/components/layout/LoginModal.tsx` | Heading «Вход» |
| Login form | `LoginForm` | `frontend/src/components/auth/LoginForm.tsx` | Labels «Логин», «Пароль», button «Войти» |
| Staff login page | `/staff/login` | `frontend/src/app/staff/login/page.tsx` | «Вход для организаторов», subtitle |
| Admin top nav | `AdminTopNav` | `frontend/src/components/admin/AdminTopNav.tsx` | Tab labels, brand, «+ Новый конкурс» |

---

## Routes (Stage 2.1 / 2.1.1 baseline)

| Route | Page file | Role / guard | Main features |
|-------|-----------|--------------|---------------|
| `/` | `frontend/src/app/page.tsx` | Public | Contest discovery, redirects when authenticated |
| `/profile` | `frontend/src/app/profile/page.tsx` | USER | Profile hub «Личный кабинет» |
| `/contests` | `frontend/src/app/contests/page.tsx` | USER | Enrolled contests list |
| `/change-password` | `frontend/src/app/change-password/page.tsx` | Auth + temp password | Password change form |
| `/staff/login` | `frontend/src/app/staff/login/page.tsx` | Public | Staff-oriented login |
| `/admin` | `frontend/src/app/admin/page.tsx` | SUPERVISOR+ | Admin dashboard stub |
| `/admin/settings/parameters` | `frontend/src/app/admin/settings/parameters/page.tsx` | SUPERVISOR+ | Contest settings stub |

---

## Features by stage (Coder appends below)

### Stage 2.2 — Predictions & privacy

#### Routes

| Route | Page file | Role / guard | Main features |
|-------|-----------|--------------|---------------|
| `/contest/[contestId]` | `frontend/src/app/contest/[contestId]/page.tsx` | All (privacy per tab) | `PublicTabs` (Лидерборд / Прогнозы / Результаты), `RoundSelector`, `PredictionsMatrix` on Прогнозы tab |
| `/contest/[contestId]/predict/[roundId]` | `frontend/src/app/contest/[contestId]/predict/[roundId]/page.tsx` | USER+ (`requireNotTempPassword`) | `PredictionForm`, `DeadlineCountdown`, batch save 8/8 |

#### Components (editable Russian copy)

| Component | Source file | Key copy |
|-----------|-------------|----------|
| `PublicTabs` | `frontend/src/components/contest/PublicTabs.tsx` | «Лидерборд», «Прогнозы», «Результаты» |
| `RoundSelector` | `frontend/src/components/contest/RoundSelector.tsx` | «Выберите тур:», labels via `formatRoundTitle()` |
| `PredictionForm` | `frontend/src/components/predictions/PredictionForm.tsx` | «Сохранить прогноз», «Редактировать», «Заполните прогнозы на все матчи тура» |
| `DeadlineCountdown` | `frontend/src/components/predictions/DeadlineCountdown.tsx` | Countdown label; «Дедлайн прошёл» |
| `DeadlineWarningBanner` | `frontend/src/components/predictions/DeadlineWarningBanner.tsx` | «До дедлайна осталось менее 24 часов. Успейте сохранить прогноз.» |
| `PredictionsMatrix` | `frontend/src/components/predictions/PredictionsMatrix.tsx` | Table headers «Счет», match columns |
| `PrivacyMask` | `frontend/src/components/predictions/PrivacyMask.tsx` | «Прогноз сделан» |
| `PredictionsVisitorStub` | `frontend/src/components/predictions/PredictionsVisitorStub.tsx` | «Будет доступно после дедлайна» (visitor pre-deadline only) |
| `OutcomeStatsFooter` | `frontend/src/components/predictions/OutcomeStatsFooter.tsx` | «Статистика», П1 / Х / П2 |
| `ProfileMenu` | `frontend/src/components/profile/ProfileMenu.tsx` | «Сделать прогноз» (links to active round) |

### Stage 2.3 — Supervisor admin UI

#### Routes

| Route | Page file | Role / guard | Main features |
|-------|-----------|--------------|---------------|
| `/admin/settings/parameters` | `frontend/src/app/admin/settings/parameters/page.tsx` | SUPERVISOR+ | Параметры конкурса, scoring cards (readonly), lock banner |
| `/admin/settings/participants` | `frontend/src/app/admin/settings/participants/page.tsx` | SUPERVISOR+ | Invite, table, temp_password modal |
| `/admin/settings/teams` | `frontend/src/app/admin/settings/teams/page.tsx` | SUPERVISOR+ | Teams grid, logo upload (B5) |
| `/admin/rounds` | `frontend/src/app/admin/rounds/page.tsx` | SUPERVISOR+ | DRAFT builder, activate, ACTIVE editor, free tour |
| `/admin/results` | `frontend/src/app/admin/results/page.tsx` | SUPERVISOR+ | Scores, calculate, publish, VOID |
| `/admin/newsletters` | `frontend/src/app/admin/newsletters/page.tsx` | SUPERVISOR+ | Stage 3 placeholder |
| `/admin/lifecycle` | `frontend/src/app/admin/lifecycle/page.tsx` | ADMIN | Pause/resume/finish/delete/recalculate |
| `/admin/users` | `frontend/src/app/admin/users/page.tsx` | ADMIN | Create organizer (SUPERVISOR) |

#### Components (editable Russian copy)

| Component | Source file | Key copy |
|-----------|-------------|----------|
| `AdminTopNav` | `frontend/src/components/admin/AdminTopNav.tsx` | Tabs: Настройки, Туры, Рассылки, Результаты; «+ Новый конкурс» |
| `LockBanner` | `frontend/src/components/admin/LockBanner.tsx` | «Редактирование параметров недоступно — Конкурс уже запущен…» |
| `ContestStatusBanner` | `frontend/src/components/admin/ContestStatusBanner.tsx` | «Конкурс на паузе» / «Конкурс завершён» |
| `ParticipantInviteModal` | `frontend/src/components/admin/ParticipantInviteModal.tsx` | «Участник приглашён», login/temp_password labels |
| `NewsletterPromptModal` | `frontend/src/components/admin/NewsletterPromptModal.tsx` | «Отправить напоминание участникам?» (Stage 3 stub) |
| `FreeTourModal` | `frontend/src/components/admin/FreeTourModal.tsx` | «Свободный тур», «Создать свободный тур» |
| `RoundManagementPanel` | `frontend/src/components/admin/RoundManagementPanel.tsx` | «Активировать», ACTIVE hint (schedule-only), 24h deadline lockout, match action confirms [UPDATED] |
| `MatchEditorRow` | `frontend/src/components/admin/MatchEditorRow.tsx` | Match status `<select>` (DRAFT + ACTIVE); ACTIVE: confirm on CANCELED/POSTPONED/restore [NEW] |
| `RoundBuilderForm` | `frontend/src/components/admin/RoundBuilderForm.tsx` | «Создать черновик тура»; validation errors for empty match dates [UPDATED] |
| `MatchResultRow` | `frontend/src/components/admin/MatchResultRow.tsx` | Score inputs; «Применить» disabled until both scores filled (empty ≠ 0) [NEW] |
| `ResultsEntryPanel` | `frontend/src/components/admin/ResultsEntryPanel.tsx` | «Рассчитать», «Опубликовать», badge «Применено» |
| `LifecyclePanel` | `frontend/src/components/admin/LifecyclePanel.tsx` | Пауза, Возобновить, Завершить, Пересчитать, Удалить |

#### Stage 2.3.2 — ACTIVE round schedule & results UX [NEW]

| Module | Source file | Behavior |
|--------|-------------|----------|
| UI mode | `frontend/src/lib/admin/deriveAdminUiMode.ts` | `canEditRoundStructure` → `DRAFT` only; schedule edits on `ACTIVE` |
| Schedule rules | `frontend/src/lib/admin/matchScheduleEdit.ts` | Reschedule until kickoff; cancel anytime; ADMIN restore; 7-day postpone hint |
| Score validation | `frontend/src/lib/validation/admin.ts` | `matchResultSchema`: empty string invalid (not coerced to `0`) |
| Phase panels | `frontend/src/components/admin/RoundPhasePanel.tsx` | CLOSED / CALCULATED / PUBLISHED read-only panels on `/admin/rounds` |
| Leaderboard preview | `frontend/src/components/admin/RoundLeaderboardPreview.tsx` | Staff preview for `CALCULATED` rounds |
| Public visibility | `frontend/src/lib/contest/roundPublicVisibility.ts` | Fetch LB/results only when `round.status === 'PUBLISHED'` |

**Before → After:** ACTIVE tours no longer show team `<select>`s after activation. Status changes use the same dropdown pattern as tour selection, with `ConfirmDialog` for destructive transitions.


### Stage 2.4 — Leaderboard & results (API wiring)

Public contest page `/contest/[contestId]` — **Лидерборд** and **Результаты** tabs use live API data. **Visual layout unchanged** (existing `LeaderboardTable` / `ResultsMatrix` components).

| Module | Source file | Behavior |
|--------|-------------|----------|
| Public paths | `frontend/src/lib/api/endpoints.ts` → `contestPublic` | `roundLeaderboard`, `roundResults`, optional global `leaderboard` |
| Leaderboard hook | `frontend/src/hooks/useLeaderboard.ts` | `GET …/rounds/{rid}/leaderboard` (no auth); `enabled` when tab active + round `PUBLISHED` |
| Results hook | `frontend/src/hooks/useRoundResults.ts` | `GET …/rounds/{rid}/results`; maps `points[]` → `match_points[]` |
| LB mapper | `frontend/src/lib/leaderboard/mapLeaderboardRow.ts` | API `ScoreDetail` + rank → table row; B4 count columns optional |
| Results mapper | `frontend/src/lib/results/mapRoundResultsRow.ts` | `base_points` per match in `matches[]` order; `total_without_bonus3` → `total_without_bonus` |
| Public gate | `frontend/src/lib/contest/roundPublicVisibility.ts` + `roundResultsGuard.ts` | Fetch only when `status === 'PUBLISHED'`; else stub, no network |
| Stub UI | `frontend/src/components/contest/ResultsUnavailableMessage.tsx` | `data-testid="results-unavailable"`; copy `ROUND_NOT_PUBLISHED_COPY` |
| Page wiring | `frontend/src/app/contest/[contestId]/page.tsx` | Removed `contestDisplayMock`; loading/error/bonuses_pending states |

**Copy (RU):**

| Condition | Message |
|-----------|---------|
| Round not `PUBLISHED` | «Будет доступно после проверки организатором» |
| Empty `points[]` after fetch | «Не удалось загрузить очки по матчам» |
| `bonuses_pending` | `BONUSES_PENDING_FALLBACK_MESSAGE` (amber banner) |

**Deferred:** ETag `If-None-Match` caching for LB/results (`lib/api/cache.ts` stub remains); global «Общий» leaderboard selector in `RoundSelector`.

**Tests:** `mapLeaderboardRow.test.ts`, `mapRoundResultsRow.test.ts`, `roundResultsGuard.test.ts` (+ existing `roundPublicVisibility.test.ts`).

---

## Update log

| Date | Stage | Summary |
|------|-------|---------|
| 2026-06-24 | 2.1 / 2.1.1 | Baseline shell, auth routes, admin stubs |
| 2026-06-24 | 2.3 | Full supervisor admin UI: settings, rounds, results, lifecycle, B5 logo |
| 2026-06-27 | 2.3.2 | ACTIVE schedule-only editing, match status confirms, empty score guard on results |
| 2026-06-28 | 2.2 | Prediction form, privacy matrix, deadline UX, contest Прогнозы tab |
| 2026-07-08 | 2.4 | Public LB/results API wiring; PUBLISHED gate; mock removed from contest page |
