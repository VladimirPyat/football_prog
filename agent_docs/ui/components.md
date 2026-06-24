# UI Component Catalogue (Stage 2)

> **Living document** — see update log at the bottom.
> **Refs:** `agent_docs/plans/draft_2.md` (§5, §11), screenshots in `docs/screens/`.
> **Constraints:** Tailwind only, no external UI libraries, no animations (`docs/02_project_structure.md`). Russian UI copy.

Components grouped by layer. Props are TypeScript-ish sketches; exact types live in `frontend/src/types`.

---

## 1. Layout / shell

### `AppShell` (public) — **Implemented (2.1)** → `frontend/src/components/layout/AppShell.tsx`
Header bar: brand `Sport Prognosis` (left); right side role-aware nav — USER: `Личный кабинет` → `/profile`; SUPERVISOR+: `Управление` → `/admin` + `ContestPicker`. Visitor: `Вход` (opens `LoginModal`). Footer: copyright + link «Вход для организаторов» → `/staff/login`.
- props: `{ children }`; reads `useAuth`.

### `AdminTopNav` (supervisor) — **Stub (2.1.1)** → `frontend/src/components/admin/AdminTopNav.tsx`
Top nav: brand `SportPrognosis` + `Сегодня DD.MM.YYYY`; tabs `Настройки` `Туры` `Рассылки` `Результаты` (disabled, `title="Скоро 2.3"`); right `ContestPicker`. Brand link → `/admin`.
- props: `{ activeTab? }`.

### `ContestPicker` — **Implemented (2.1)** → `frontend/src/components/contest/ContestPicker.tsx`
Dropdown of contests. Supervisor → `GET /contests`; User → `GET /me/contests` (B1); Visitor → `GET /contests/public` (B2).
- props: internal (reads `useAuth`, `useContest`, `useMyContests`); compact `<select>` in header for SUPERVISOR+.

### `NewContestButton`
`+ Новый конкурс` → opens `CreateContestForm` (SUPERVISOR+, SETUP).

### `LoginModal` — **Implemented (2.1)** → `frontend/src/components/layout/LoginModal.tsx`
Overlay with `LoginForm`; closes on success; shows API `detail` on 401.

### `ProtectedRoute` — **Implemented (2.1)** → `frontend/src/components/auth/ProtectedRoute.tsx`
Client guard: `requireAuth` / `requireRole(role)` / `requireNotTempPassword`. Redirects: unauthenticated→`/`, wrong role→`/` (USER-only routes send staff→`/admin`), temp-pw→`/change-password`, completed change-password→`resolvePostLoginPath(user)`.

### `resolvePostLoginPath` — **Implemented (2.1.1)** → `frontend/src/lib/auth/resolvePostLoginPath.ts`
Pure function: temp password → `/change-password`; USER → `/profile`; SUPERVISOR → `/admin/settings/parameters`; ADMIN → `/admin`. Used by `AuthProvider` and `ProtectedRoute`.

### `TempPasswordGuard` — **Implemented (2.1)** → `frontend/src/components/auth/TempPasswordGuard.tsx`
Global layout guard; redirects authenticated `is_temp_password` users to `/change-password`.

---

## 2. Navigation / shared widgets

| Component | Purpose | Key props |
|-----------|---------|-----------|
| `PublicTabs` | Segmented control `Лидерборд / Прогнозы / Результаты` | `{ active, onChange }` |
| `RoundSelector` | Top-right dropdown `Тур N (Текущий)`; disables unavailable rounds | `{ rounds, value, onChange }` |
| `DeadlineCountdown` | Time remaining → «Дедлайн прошёл» | `{ deadline }` |
| `StatusChip` | Colored badge for round/match/contest status | `{ kind, status }` |
| `Toast` / `ToastProvider` | Success/error notifications (no animation lib) | `{ type, message }` — **Implemented (2.1)** → `frontend/src/components/ui/Toast.tsx`, `frontend/src/providers/ToastProvider.tsx` |
| `ConfirmDialog` | Confirm VOID / activate / delete | `{ title, body, onConfirm }` |
| `LoadingState` / `ErrorState` / `EmptyState` | Consistent fetch states | `{ message? }` — **LoadingState, ErrorState implemented (2.1)** → `frontend/src/components/ui/` |
| `RoleBadge` | Show current role | `{ role }` |
| `ContestStatusBanner` | PAUSED / FINISHED / locked notice | `{ contest }` |
| `LockBanner` | «Редактирование параметров недоступно — Конкурс уже запущен» | `{ visible }` |

### Status color map (Tailwind badge classes)

| Round | Match |
|-------|-------|
| DRAFT gray · ACTIVE green · CLOSED orange · CALCULATED blue · PUBLISHED purple | SCHEDULED gray · POSTPONED yellow · CANCELED red · VOID red-outline · FINISHED green |

---

## 3. Data display

### `LeaderboardTable`  (`user_leaderboard.jpg`)
13 columns in order: `Место · Фамилия Имя · Дано прогнозов · Точный кр. счет · Точный счет · Разница · Исход · Бонус 1 · Бонус 2 · Бонус 3 · Очки без бонуса · Очки с бонусами · Всего очков`.
- Bonus cols subtle yellow tint; `Всего очков` green emphasis, right aligned.
- props: `{ rows: ScoreDetail&{rank,predictions_count}[] }`.
- ⚠️ count columns need B4; if absent, hide the four columns (documented fallback).

### `PredictionsMatrix`  (`user_predict.jpg`)
First column `Счет` + `Тур N` sub-row; one column per match header `TeamA-TeamB`; participant rows with `score1:score2` cells. Footer `OutcomeStatsFooter`.
- Privacy: own row = scores; others pre-deadline = `PrivacyMask`; visitor pre-deadline = stub message.
- props: `{ matches, entries, deadlinePassed, currentUserId }`.

### `OutcomeStatsFooter`
Per-match `П1 / Х / П2` counts (home win / draw / away win), colored.
- props: `{ matches, entries }` (computed client-side from visible predictions, or from API if provided).

### `ResultsMatrix`  (`user_result.jpg`)
First column `Счет`; per-match header + actual `score1:score2` sub-row; cells = per-match points (`0/4/8/12/16`, non-zero green); right columns `Бонус 1 · Бонус 2 · Итого без бон. · Бонус 3 · ИТОГ`. `-` where bonus N/A. Horizontal scroll.
- props: `{ matches, results }`.

### Cell atoms
| Component | Renders |
|-----------|---------|
| `ScoreCell` | `N:M` |
| `PointsCell` | points with green highlight when >0 |
| `PrivacyMask` | «Прогноз сделан» |

---

## 4. Forms (see `ui/forms_validation.md` for rules)

| Component | Used on |
|-----------|---------|
| `LoginForm` | LoginModal — **Implemented (2.1)** → `frontend/src/components/auth/LoginForm.tsx` |
| `ChangePasswordForm` | `/change-password` — **Implemented (2.1)** → `frontend/src/components/auth/ChangePasswordForm.tsx` |
| `PredictionForm` | `/contest/[id]/predict/[rid]` |
| `ScoreInput` | inside PredictionForm / ResultsEntryGrid |
| `ContactsForm` | `/profile` (B3) — **Implemented (2.1)** → `frontend/src/components/profile/ContactsForm.tsx` |
| `CreateContestForm` | NewContestButton |
| `ContestParametersForm` | Настройки → Параметры |
| `TeamForm` | Настройки → Команды |
| `ParticipantInviteForm` | Настройки → Участники |
| `RoundBuilderForm` | Туры |
| `MatchEditorRow` | Туры (ACTIVE round) |
| `MatchResultForm` / `ResultsEntryGrid` | Результаты |
| `FreeTourModal` | Туры |
| `TiebreakForm` | Участники (ADMIN row action) |

---

## 5. Admin tables / panels

| Component | Features |
|-----------|----------|
| `ParticipantsTable` | cols `Имя · Email · [Выслать приглашение] · Статус · Действия`; status PENDING/ACCEPTED; invite shows returned `temp_password`; delete disabled when locked |
| `TeamsGrid` | team chips (2-letter badge + name) + `Добавить команду` card (disabled when locked) |
| `RoundManagementPanel` | round dropdown, deadline picker, 8-match grid, right `Статус тура` card, `+ Добавить свободный тур` |
| `ResultsEntryPanel` | round dropdown, per-match `Завершён`/`Отменить` + score inputs, `Применено` lock badge |
| `LifecyclePanel` (ADMIN) | pause/resume/finish/delete + grace timer |
| `RecalculateButton` (ADMIN) | `POST …/admin/recalculate` with confirm |
| `NewslettersPlaceholder` | «Скоро (Stage 3)» page for `Рассылки` tab |

---

## 6. Hooks (see `ui/state_management.md`)

`useAuth`, `useContest`, `useRounds`, `useLeaderboard`, `useRoundResults`, `usePredictionsView`, `usePredictionSubmit`, `useDeadline`, `useMaxScore`, `useMyContests`, `usePublicContests`, `useContacts`, `useToast`.

**Implemented (2.1):** `useAuth` → `frontend/src/hooks/useAuth.ts`; `useContest` → `frontend/src/hooks/useContest.ts`; `useMyContests` → `frontend/src/hooks/useMyContests.ts`; `usePublicContests` → `frontend/src/hooks/usePublicContests.ts`; `useContacts` → `frontend/src/hooks/useContacts.ts`; `useToast` → `frontend/src/hooks/useToast.ts`.

**Also (2.1):** `ContestList` → `frontend/src/components/contest/ContestList.tsx`; `ProfileMenu` → `frontend/src/components/profile/ProfileMenu.tsx`.

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-21 | Initial catalogue across layout/shared/data/forms/admin, derived from plan §5 + screenshots §11. Props to refine per sub-stage. |
| 2026-06-23 | Stage 2.1: marked implemented components with `frontend/src/...` paths; added `TempPasswordGuard`, `ContestList`, `ProfileMenu`. |
| 2026-06-24 | Stage 2.1.1: `AdminTopNav` stub; `resolvePostLoginPath`; role-aware `AppShell` nav; `ProtectedRoute` staff redirect from `/profile`. |
