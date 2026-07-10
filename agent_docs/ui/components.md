# UI Component Catalogue (Stage 2)

> **Living document** — see update log at the bottom.
> **Refs:** `agent_docs/plans/draft_2.md` (§5, §11), screenshots in `docs/screens/`, **`agent_docs/contracts/admin_ui_status_matrix.md`**, **`agent_docs/ui/design_system.md`** (shared styling & reuse rules).
> **Constraints:** Tailwind only, no external UI libraries, no animations (`docs/02_project_structure.md`). Russian UI copy.

Components grouped by layer. Props are TypeScript-ish sketches; exact types live in `frontend/src/types`.

---

## 0. Maintenance & reuse (mandatory)

This catalogue lists **what** exists. **`design_system.md`** defines **how to style and reuse** shared primitives.

| When | Do |
|------|-----|
| Adding/changing a table, button, badge, banner, or empty state | Check `design_system.md` §3–§4 first; extend existing `lib/table/*` or `components/ui/*` — do not copy-paste Tailwind strings |
| Shipping a new shared component | Add entry below **and** update `design_system.md` + update log in both files |
| Fixing table/button styling on one page | Fix the shared primitive so all consumers of the same taxonomy type inherit the change (see audit: `agent_docs/reports/frontend_design_consistency_audit.md`) |
| Coder / fix instructions | Must include: «Reuse `agent_docs/ui/design_system.md`; update catalogue if new primitive» |

**Shared styling layer (implemented):**

| Module | Path | Purpose |
|--------|------|---------|
| Column tokens | `frontend/src/lib/table/columnStyles.ts` | Width/align for scoreboard columns (`COL_RANK`, `COL_NAME`, `COL_DIGIT2`, `COL_DIGIT3`) |
| Header tokens | `frontend/src/lib/table/tableHeaderStyles.ts` | Thead cell classes (`TH_*`) for contest tables |
| Header helper | `frontend/src/lib/table/headerLabel.tsx` | Multiline `<th>` labels |
| Generic UI | `frontend/src/components/ui/*` | Loading, error, confirm, detail modal, toast |

**Planned extractions (P0–P2):** `DataTable`, `AdminTable`, `Button`, `StatusChip`, `EmptyState`, `Callout` — see `design_system.md` §4.

---

## 1. Layout / shell

### `AppShell` (public) — **Implemented (2.1)** → `frontend/src/components/layout/AppShell.tsx`
Header bar: brand `Sport Prognosis` (left); right side role-aware nav — USER: `Личный кабинет` → `/profile`; SUPERVISOR+: `Управление` → `/admin` + `ContestPicker`. Visitor: `Вход` (opens `LoginModal`). Footer: copyright + link «Вход для организаторов» → `/staff/login`.
- props: `{ children }`; reads `useAuth`.

### `AdminTopNav` (supervisor) — **Implemented (2.3)** → `frontend/src/components/admin/AdminTopNav.tsx`
Top nav: brand `SportPrognosis` + `Сегодня DD.MM.YYYY`; tabs `Настройки` `Туры` `Рассылки` `Результаты` (active link via pathname); right `ContestPicker adminMode` + `+ Новый конкурс` → `CreateContestForm` (**name + slug only** — 2.3.3 S1.1). Post-create setup hint on Parameters.

### `ContestPicker` — **Implemented (2.1, 2.3)** → `frontend/src/components/contest/ContestPicker.tsx`
Dropdown of contests. Supervisor → `GET /contests`; User → `GET /me/contests` (B1); Visitor → `GET /contests/public` (B2). Prop `adminMode` keeps user on admin page when switching contest.

### `NewContestButton` — **Implemented (2.3)** in `AdminTopNav`
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
| `StatusChip` | Colored badge for round/match/contest status | `{ kind, status }` — **Planned** → extract to `frontend/src/components/ui/StatusChip.tsx`; colours duplicated in `RoundStatusSidebar`, `ContestList` until then — see `design_system.md` §4 |
| `Toast` / `ToastProvider` | Success/error notifications (no animation lib) | `{ type, message }` — **Implemented (2.1)** → `frontend/src/components/ui/Toast.tsx`, `frontend/src/providers/ToastProvider.tsx` |
| `ConfirmDialog` | Confirm VOID / activate / delete | **Implemented (2.3)** → `frontend/src/components/ui/ConfirmDialog.tsx` |
| `LoadingState` / `ErrorState` / `EmptyState` | Consistent fetch states | `{ message? }` — **LoadingState, ErrorState implemented (2.1)** → `frontend/src/components/ui/`; **EmptyState planned** → `frontend/src/components/ui/EmptyState.tsx` |
| `RoleBadge` | Show current role | `{ role }` — **Planned** (low priority) |
| `Button` | Primary / secondary / danger actions | `{ variant, size?, fullWidth?, disabled? }` — **Planned** → `frontend/src/components/ui/Button.tsx`; ~25 files use inline classes today |
| `Callout` | Info / warning / error inline banners | `{ variant, children }` — **Planned** → `frontend/src/components/ui/Callout.tsx` |
| `DataTable` / `AdminTable` | Table shell + scroll wrapper | `{ children, variant?, testId? }` — **Planned** → `frontend/src/components/ui/`; admin tables currently ad-hoc |
| `PreviewBadge` | «Предпросмотр — тур ещё не опубликован» | — **Planned**; duplicated in `RoundLeaderboardPreview`, `RoundResultsPreview` |
| `ContestStatusBanner` | PAUSED / FINISHED / locked notice | **Implemented (2.3)** → `frontend/src/components/admin/ContestStatusBanner.tsx` |
| `LockBanner` | «Редактирование параметров недоступно — Конкурс уже запущен» | **Implemented (2.3)** → `frontend/src/components/admin/LockBanner.tsx` — **settings pages only** (2.3.1 F8) |

### Status color map (Tailwind badge classes)

| Round | Match |
|-------|-------|
| DRAFT gray · ACTIVE green · CLOSED orange · CALCULATED blue · PUBLISHED purple | SCHEDULED gray · POSTPONED yellow · CANCELED red · VOID red-outline · FINISHED green |

**Round status labels (2.3.1):** API `CLOSED` → UI **«Дедлайн»** via `roundStatusLabel()`; contextual hints via `roundStatusHint()` in `frontend/src/lib/admin/format.ts`. Supplementary rounds: **«ДопТурN»** via `formatRoundTitle()` / `formatRoundOptionLabel()` in `roundLabel.ts` (2.3.4 F4).

---

## 3. Data display

### `LeaderboardTable`  (`user_leaderboard.jpg`) — **API-wired (2.4)** ✅ → `frontend/src/components/contest/LeaderboardTable.tsx`
13 columns in order: `Место · Фамилия Имя · Дано прогнозов · Точный кр. счет · Точный счет · Разница · Исход · Бонус 1 · Бонус 2 · Бонус 3 · Очки без бонуса · Очки с бонусами · Всего очков`.
- Bonus cols subtle yellow tint; `Всего очков` green emphasis, right aligned.
- props: `{ rows: LeaderboardTableRow[]; showCountColumns?: boolean }` from `useLeaderboard` + `mapLeaderboardRow`.
- Public gate: fetch only when `round.status === 'PUBLISHED'`; else `ResultsUnavailableMessage`.
- ⚠️ count columns need B4; if absent, hide the four columns (documented fallback).

### `ResultsUnavailableMessage` — **Implemented (2.4)** → `frontend/src/components/contest/ResultsUnavailableMessage.tsx`
Stub for non-`PUBLISHED` rounds on **Лидерборд** / **Результаты** tabs (`data-testid="results-unavailable"`). Copy: `ROUND_NOT_PUBLISHED_COPY`.

### `PredictionsMatrix`  (`user_predict.jpg`) — **Implemented (2.2)** → `frontend/src/components/predictions/PredictionsMatrix.tsx`
First column `Счет` + `Тур N` sub-row; one column per match header `TeamA-TeamB`; participant rows with `score1:score2` cells. Footer `OutcomeStatsFooter`.
- Privacy: own row = scores; others pre-deadline = `PrivacyMask`; visitor pre-deadline = stub message.
- props: `{ matches, entries, deadlinePassed, viewer, roundTitle }`.

### `OutcomeStatsFooter` — **Implemented (2.2)** → `frontend/src/components/predictions/OutcomeStatsFooter.tsx`
Per-match `П1 / Х / П2` counts (home win / draw / away win), colored.
- props: `{ matches, entries }` (computed client-side from visible predictions).

### `ResultsMatrix`  (`user_result.jpg`) — **API-wired (2.4)** ✅ → `frontend/src/components/contest/ResultsMatrix.tsx`
First column `Счет`; per-match header + actual `score1:score2` sub-row; cells = per-match points (`0/4/8/12/16`, non-zero green); right columns `Бонус 1 · Бонус 2 · Итого без бон. · Бонус 3 · ИТОГ`. `-` where bonus N/A. Horizontal scroll.
- props: `{ matches: ResultsMatrixMatch[]; rows: ResultsMatrixRow[]; roundLabel }` from `useRoundResults` + `mapRoundResultsRow`.
- Public gate: same as leaderboard (`PUBLISHED` only); `403 RESULTS_NOT_AVAILABLE` → stub.

### Cell atoms
| Component | Renders |
|-----------|---------|
| `ScoreCell` | `N:M` prediction pill — **inline in `PredictionsMatrix`**; planned extract → `components/predictions/ScoreCell.tsx` |
| `PointsCell` / `TotalCell` | points with green highlight when >0 — **inline in `LeaderboardTable`, `ResultsMatrix`**; planned extract → `components/ui/PointsCell.tsx` |
| `PrivacyMask` — **Implemented (2.2)** → `frontend/src/components/predictions/PrivacyMask.tsx` | «Прогноз сделан» |

### Shared table styling (fix 2.5.2)
Contest scoreboard tables (`LeaderboardTable`, `ResultsMatrix`) share `lib/table/columnStyles.ts`, `tableHeaderStyles.ts`, `headerLabel.tsx`.  
**Gap:** `PredictionsMatrix` uses `COL_NAME` only — must adopt full stack (see `frontend_design_consistency_audit.md` §1.1).  
**Gap:** Admin tables (`ParticipantsTable`, `RoundPhasePanel`, `ResultsEntryPanel`, `RoundManagementPanel`, `RoundLeaderboardPreview`) do not use shared tokens — must migrate to `AdminTable` (planned).

---

## 4. Forms (see `ui/forms_validation.md` for rules)

| Component | Used on |
|-----------|---------|
| `LoginForm` | LoginModal — **Implemented (2.1)** → `frontend/src/components/auth/LoginForm.tsx` |
| `ChangePasswordForm` | `/change-password` — **Implemented (2.1)** → `frontend/src/components/auth/ChangePasswordForm.tsx` |
| `PredictionForm` | `/contest/[id]/predict/[rid]` — **Implemented (2.2)** → `frontend/src/components/predictions/PredictionForm.tsx` |
| `ScoreInput` | inside PredictionForm — **Implemented (2.2)** → `frontend/src/components/predictions/ScoreInput.tsx` |
| `PredictionMatchRow` | inside PredictionForm — **Implemented (2.2)** → `frontend/src/components/predictions/PredictionMatchRow.tsx` |
| `ContactsForm` | `/profile` (B3) — **Implemented (2.1)** → `frontend/src/components/profile/ContactsForm.tsx` |
| `CreateContestForm` | NewContestButton — **Implemented (2.3)** → `frontend/src/components/admin/CreateContestForm.tsx` — **name + optional slug only** (2.3.3); structure defaults from backend |
| `ContestParametersForm` | Настройки → Параметры — **Implemented (2.3)** → `frontend/src/components/admin/ContestParametersForm.tsx` — round-robin sync, rules save (2.3.3–2.3.4) |
| `RulesEditorPanel` | Parameters — structured bonus/scoring editor — **Implemented (2.3.4)** → `frontend/src/components/admin/RulesEditorPanel.tsx` |
| `ContestLifecycleActions` | Parameters footer — start / delete / pause CTAs — **Implemented (2.3.3+)** → `frontend/src/components/admin/ContestLifecycleActions.tsx` |
| `ContestStartReadinessPanel` | Parameters — pre-start checklist — **Implemented (2.3.4)** → `frontend/src/components/admin/ContestStartReadinessPanel.tsx` |
| `TeamForm` | Настройки → Команды — **Implemented (2.3)** → `frontend/src/components/admin/TeamForm.tsx` |
| `ParticipantInviteForm` | Настройки → Участники — **Implemented (2.3)** → `frontend/src/components/admin/ParticipantInviteForm.tsx` |
| `RoundBuilderForm` | Туры — **Implemented (2.3)** → `frontend/src/components/admin/RoundBuilderForm.tsx` |
| `MatchEditorRow` | Туры (ACTIVE round) — **Implemented (2.3)** → `frontend/src/components/admin/MatchEditorRow.tsx` |
| `MatchResultForm` / `ResultsEntryGrid` | Результаты — **Implemented (2.3)** → `ResultsEntryPanel`, `MatchResultRow` |
| `FreeTourModal` | Туры — **Implemented (2.3)** → `frontend/src/components/admin/FreeTourModal.tsx` |
| `TiebreakForm` | Участники (ADMIN row action) — **Implemented (2.3)** → `frontend/src/components/admin/TiebreakForm.tsx` |

---

## 5. Admin tables / panels — **Implemented (2.3)**

| Component | Path |
|-----------|------|
| `AdminPageShell` | `frontend/src/components/admin/AdminPageShell.tsx` — banners + settings header |
| `SettingsSubNav` | `frontend/src/components/admin/SettingsSubNav.tsx` |
| `ParticipantsTable` | `frontend/src/components/admin/ParticipantsTable.tsx` |
| `ParticipantInviteModal` | `frontend/src/components/admin/ParticipantInviteModal.tsx` |
| `TeamsGrid` / `TeamLogoUpload` | `frontend/src/components/admin/TeamsGrid.tsx`, `TeamLogoUpload.tsx` |
| `RoundManagementPanel` | `frontend/src/components/admin/RoundManagementPanel.tsx` |
| `RoundPhasePanel` | Per-status main panel (DRAFT/ACTIVE/CLOSED/CALCULATED/PUBLISHED) — **2.3.1** → `frontend/src/components/admin/RoundPhasePanel.tsx` |
| `RoundStatusSidebar` | Status badge + hints + post-deadline copy — **2.3.1/2.3.5** → `frontend/src/components/admin/RoundStatusSidebar.tsx` |
| `RoundLeaderboardPreview` | CALCULATED preview table + `bonuses_pending` note — **2.3.1/2.3.4** → `frontend/src/components/admin/RoundLeaderboardPreview.tsx` |
| `ResultsEntryPanel` | `frontend/src/components/admin/ResultsEntryPanel.tsx` |
| `MatchResultRow` | Per-match result row with gating — **2.3.2** → `frontend/src/components/admin/MatchResultRow.tsx` |
| `LifecyclePanel` | `frontend/src/components/admin/LifecyclePanel.tsx` |
| `CreateOrganizerForm` | `frontend/src/components/admin/CreateOrganizerForm.tsx` |
| `NewsletterPromptModal` | `frontend/src/components/admin/NewsletterPromptModal.tsx` (Stage 3 stub) |

---

## 6. Hooks (see `ui/state_management.md`)

`useAuth`, `useContest`, `useRounds`, `useLeaderboard`, `useRoundResults`, `usePredictionsView`, `usePredictionSubmit`, `useDeadline`, `useMaxScore`, `useMyContests`, `usePublicContests`, `useContacts`, `useToast`.

**Implemented (2.3):** `useContestAdmin`, `useTeams`, `useParticipants`, `useAdminRounds`, `useRoundMatches`, `useAdminResults`, `useContestStartReadiness` under `frontend/src/hooks/`.

**Pure helpers (`frontend/src/lib/admin/`):**

| Module | Purpose |
|--------|---------|
| `deriveAdminUiMode.ts` | Contest/round phase → capability flags (uses `effectiveRoundStatus` — 2.3.5) |
| `deadlineRule.ts` | Deadline placement + 24h **change** lockout (2.3.1 F2) |
| `roundEffectiveStatus.ts` | ACTIVE + deadline passed → behave as CLOSED (2.3.5) |
| `roundLabel.ts` | `Тур N` / `ДопТурN` labels (2.3.4 F4) |
| `roundScoringPending.ts` | Parse `bonuses_pending` from leaderboard (2.3.4 F5) |
| `contestStartReadiness.ts` | Start gate matrix (2.3.4 F3) |
| `rulesEditor.ts` | `buildRulesJsonPatch()` for PATCH (2.3.4 F2) |
| `matchResultsGating.ts` | Results entry by round/match status (2.3.2) |
| `matchScheduleEdit.ts` | Kickoff reschedule rules on ACTIVE (2.3.1 F3) |
| `collectPostponedMatches.ts` | Free-tour postponed match grouping |
| `format.ts` | `roundStatusLabel`, `roundStatusHint`, `matchPhaseLabel` |

**Public visibility (2.3.1 F12):** `frontend/src/lib/contest/roundPublicVisibility.ts` — `isRoundPubliclyVisible(status)`.

**Implemented (2.1):** `useAuth` → `frontend/src/hooks/useAuth.ts`; `useContest` → `frontend/src/hooks/useContest.ts`; `useMyContests` → `frontend/src/hooks/useMyContests.ts`; `usePublicContests` → `frontend/src/hooks/usePublicContests.ts`; `useContacts` → `frontend/src/hooks/useContacts.ts`; `useToast` → `frontend/src/hooks/useToast.ts`.

**Also (2.1):** `ContestList` → `frontend/src/components/contest/ContestList.tsx`; `ProfileMenu` → `frontend/src/components/profile/ProfileMenu.tsx`.

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-21 | Initial catalogue across layout/shared/data/forms/admin, derived from plan §5 + screenshots §11. Props to refine per sub-stage. |
| 2026-06-23 | Stage 2.1: marked implemented components with `frontend/src/...` paths; added `TempPasswordGuard`, `ContestList`, `ProfileMenu`. |
| 2026-06-24 | Stage 2.1.1: `AdminTopNav` stub; `resolvePostLoginPath`; role-aware `AppShell` nav; `ProtectedRoute` staff redirect from `/profile`. |
| 2026-06-24 | Stage 2.3: full admin component catalogue with `frontend/src/components/admin/*` paths; `deriveAdminUiMode` engine; admin hooks. |
| 2026-06-28 | Stage 2.3.1: `RoundPhasePanel`, `RoundStatusSidebar`, status hints; LockBanner scope; public visibility helper. |
| 2026-06-28 | Stage 2.3.3–2.3.4: slim create; `RulesEditorPanel`, `ContestLifecycleActions`, `ContestStartReadinessPanel`; `roundLabel`, `rulesEditor`, `contestStartReadiness`. |
| 2026-06-28 | Stage 2.3.5: `roundEffectiveStatus`; `MatchResultRow`; removed manual close UX from sidebar. |
| 2026-06-28 | Stage 2.2: prediction form, matrix, privacy, deadline UX, `PublicTabs`, `RoundSelector`. |
| 2026-07-10 | Design consistency audit: §0 maintenance/reuse rules; link to `design_system.md`; marked planned primitives (`Button`, `StatusChip`, `EmptyState`, `DataTable`, …); documented `lib/table/*` shared layer and gaps (`PredictionsMatrix`, admin tables). Report: `agent_docs/reports/frontend_design_consistency_audit.md`. |
