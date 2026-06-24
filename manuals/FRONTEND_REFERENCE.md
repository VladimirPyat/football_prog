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

*(Coder 2.2: append routes, components, and copy table when implemented.)*

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
| `RoundManagementPanel` | `frontend/src/components/admin/RoundManagementPanel.tsx` | «Активировать», «ТУР АКТИВИРОВАН…», 24h deadline errors |
| `ResultsEntryPanel` | `frontend/src/components/admin/ResultsEntryPanel.tsx` | «Рассчитать», «Опубликовать», badge «Применено» |
| `LifecyclePanel` | `frontend/src/components/admin/LifecyclePanel.tsx` | Пауза, Возобновить, Завершить, Пересчитать, Удалить |


### Stage 2.4 — Leaderboard & results

*(Coder 2.4: append routes, components, and copy table when implemented.)*

---

## Update log

| Date | Stage | Summary |
|------|-------|---------|
| 2026-06-24 | 2.1 / 2.1.1 | Baseline shell, auth routes, admin stubs |
| 2026-06-24 | 2.3 | Full supervisor admin UI: settings, rounds, results, lifecycle, B5 logo |
