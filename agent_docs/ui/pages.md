# UI Pages Specification (Stage 2)

> **Living document** — see update log at the bottom.
> **Refs:** `agent_docs/plans/draft_2.md` (§3.2, §4, §11), `docs/03_user_scenarios.md`, `docs/04_supervisor_scenario.md`, screenshots `docs/screens/`.
> Routing decision (locked): contest-scoped URLs `/contest/[id]`; public views are **tabs**, not sub-routes.

Role hierarchy: `ADMIN ⊃ SUPERVISOR ⊃ USER`; Visitor = no token.

---

## 1. Public & User pages

### `/` — Home / contest discovery — **Implemented (2.1)** ✅ → `frontend/src/app/page.tsx`
- **Roles:** all (authenticated behaviour differs by role — 2.1.1).
- **Visitor:** list of running contests (`GET /contests/public`, B2) → select → `/contest/{id}`.
- **User (authenticated):** redirect to «Конкурсы» or last contest (participant flow).
- **Supervisor/Admin (authenticated):** redirect to `/admin` (not participant hub).
- Fallback (B2 unavailable/empty): redirect to `NEXT_PUBLIC_DEFAULT_CONTEST_ID`.

### `/contests` — «Конкурсы» — **Implemented (2.1)** ✅ → `frontend/src/app/contests/page.tsx`
- **User:** contests they were invited to (`GET /me/contests`, B1).
- **Supervisor/Admin:** managed contests (`GET /contests`).
- Row → set active contest → navigate to contest page or admin.

### `/contest/[contestId]` — public tabbed page  (`user_*.jpg`) — **Placeholder (2.1)** → `frontend/src/app/contest/[contestId]/page.tsx`
- **Roles:** all (privacy rules per tab).
- **Header:** title `Конкурс спортивных прогнозов` + subtitle; top-right `RoundSelector` (`Тур N (Текущий)`).
- **Tabs (`PublicTabs`):**
  - **Лидерборд** (default): `LeaderboardTable` from `GET /contests/{id}/leaderboard` (global) or round leaderboard when a round is selected.
  - **Прогнозы:** `PredictionsMatrix` + `OutcomeStatsFooter` from `GET …/rounds/{rid}/predictions`. Privacy: current round before deadline → others masked / visitor stub («Будет доступно после дедлайна»); past rounds → full.
  - **Результаты:** `ResultsMatrix` from `GET …/rounds/{rid}/results`. Only CALCULATED/PUBLISHED; else «Результаты будут доступны после подведения итогов».
- Deep link: `/contest/[contestId]/round/[roundId]` preserves selected round (+ tab via query).

### `/contest/[contestId]/predict/[roundId]` — prediction entry
- **Roles:** USER+ (`requireNotTempPassword`).
- `RoundSelector` (current→last). `PredictionForm`: match list (place, time, teams) + `[A] _ : _ [B]`.
- Batch save (8/8, 0..max), Edit/Save toggle, readonly after deadline, 403 handling.
- Source: `GET …/predictions` (prefill), `POST …/predictions`.

### `/profile` — personal hub (USER primary) — **Implemented (2.1)** ✅ → `frontend/src/app/profile/page.tsx`
- **Roles:** **USER only** (2.1.1). SUPERVISOR and ADMIN are redirected to `/admin` — profile is not the staff landing page.
- Sections: `ContactsForm` (email/VK/TG + notify, B3), «Конкурсы» link, «Сделать прогноз» shortcut (active round), «Просмотр результатов», «Личная статистика» (stub), «Выйти».
- **Contacts fallback:** if `GET /auth/me/contacts` fails → fields readonly, Save hidden.
- Default center: active prediction form (if open) or latest results.

### `/change-password` — forced change gate — **Implemented (2.1)** ✅ → `frontend/src/app/change-password/page.tsx`
- **Roles:** authenticated with `is_temp_password=true`.
- `ChangePasswordForm`; on success → **role-based path** via `resolvePostLoginPath` (2.1.1), not hardcoded `/profile`. Blocks all other navigation until done.

### `/staff/login` — staff-oriented login (optional, 2.1.1) — **Planned (2.1.1)**
- **Roles:** Visitor (unauthenticated).
- Same `LoginForm` + `POST /auth/login` as header modal; copy «Вход для организаторов».
- Post-login routing identical to modal (resolver by role).
- Link from `AppShell` footer.

---

## 2. Supervisor / Admin pages

All under `AdminTopNav` shell with `ContestPicker`. **Roles:** SUPERVISOR+ unless marked ADMIN.

### `/admin` — admin landing — **Stub (2.1.1)** → `frontend/src/app/admin/page.tsx`
- **ADMIN:** dashboard stub — placeholder links to lifecycle/users/settings («Скоро — этап 2.3»).
- **SUPERVISOR:** redirect to `/admin/settings/parameters`.
- Guard: `ProtectedRoute requireRole SUPERVISOR+`.

### `/admin/layout.tsx` — admin shell — **Stub (2.1.1)**
- `AdminTopNav` with tabs Настройки / Туры / Рассылки / Результаты — disabled or «Скоро 2.3» until full UI in 2.3.
- `ContestPicker` in header when applicable.

### `/admin/settings/parameters` — Настройки → Параметры  (`supervisor_settings.jpg`) — **Stub (2.1.1)** → placeholder; **Full UI (2.3)**
- `LockBanner` when `is_locked`. Fields readonly when locked: `Количество команд`, `Количество туров`, `Число матчей в туре`, `Произвольное количество`.
- Scoring cards (`Основные очки`, `Бонусы`) from `rules_json`. `Остановить конкурс` (pause/finish, ADMIN).
- Source: `GET/PATCH /contests/{id}`.

### `/admin/settings/participants` — Участники  (`supervisor_settings2.jpg`)
- `ParticipantsTable`; `+ Добавить участника` (disabled when locked); invite → `temp_password` shown.
- Source: `GET/POST/DELETE …/participants`. ADMIN row action: tie-break (`PUT …/exceptional-tiebreak`).

### `/admin/settings/teams` — Команды  (`supervisor_settings3.jpg`)
- `TeamsGrid` + add-team card (`Название`, `Сокращение ≤4`, `Логотип` upload B5). Disabled when locked.
- Source: `GET/POST/PATCH/DELETE …/teams`. Logo: B5 upload, fallback `logo_url`.

### `/admin/rounds` — Туры  (`supervisor_tours.jpg`)
- `RoundManagementPanel`: round dropdown, `Дедлайн прогнозов` picker (24h rule), 8-match grid (`Домашняя/Гостевая/Статус/Время`), right `Статус тура` card, `+ Добавить свободный тур`.
- Warnings when active/deadline passed (only status+date editable).
- Source: `POST/PATCH …/admin/rounds`, `…/activate|close`, `…/free-tour`, `PATCH …/matches/{id}/status`.

### `/admin/results` — Результаты  (`supervisor_results.jpg`)
- `ResultsEntryPanel`: round dropdown, per-match `Завершён`/`Отменить` + score inputs, `Применить результаты` → calculate → publish workflow; `Применено` lock badge.
- Source: `PUT …/matches/{id}/result`, `PATCH …/matches/{id}/status` (VOID), `POST …/rounds/{id}/calculate|publish`.

### `/admin/newsletters` — Рассылки
- `NewslettersPlaceholder` («Скоро — Stage 3»). Tab visible per screenshot; no API.

### `/admin/lifecycle` — Contest lifecycle (ADMIN)
- `LifecyclePanel`: pause/resume/finish/delete (confirm `DELETE` + grace), `RecalculateButton`.
- Source: `POST …/pause|resume|finish`, `DELETE …/contests/{id}`, `POST …/admin/recalculate`.

### `/admin/users` — Create organizer (ADMIN)
- Form → `POST /admin/users/supervisor`.

---

## 3. Role × route access matrix

| Route | Visitor | USER | SUPERVISOR | ADMIN |
|-------|---------|------|------------|-------|
| `/` | ✅ | ✅ | ✅ | ✅ |
| `/contests` | ✅ public list | ✅ invited | ✅ | ✅ |
| `/contest/[id]` (Лидерборд/Результаты) | ✅ | ✅ | ✅ | ✅ |
| `/contest/[id]` Прогнозы (current round) | stub | own+masked | full | full |
| `/contest/[id]/predict/[rid]` | ❌ | ✅ | ✅ | ✅ |
| `/profile` | ❌ | ✅ | ❌ → `/admin` | ❌ → `/admin` |
| `/change-password` | ❌ | ✅ (temp) | ✅ (temp) | ✅ (temp) |
| `/staff/login` | ✅ | ❌† | ❌† | ❌† |
| `/admin`, `/admin/settings/*` (stub 2.1.1) | ❌ | ❌ | ✅ | ✅ |
| `/admin/rounds`, `/admin/results`, `/admin/newsletters` | ❌ | ❌ | ✅ | ✅ |
| `/admin/lifecycle`, `/admin/users` | ❌ | ❌ | ❌ | ✅ |

\* Результаты only when round CALCULATED/PUBLISHED.

† `/staff/login` is a login page for unauthenticated visitors; authenticated users use role-based nav.

---

## Update log

| Date | Change |
|------|--------|
| 2026-06-21 | Initial page specs per role with routes, data sources, screenshot refs, access matrix. |
| 2026-06-23 | Stage 2.1: marked `/`, `/contests`, `/profile`, `/change-password` ✅; `/contest/[id]` placeholder. |
| 2026-06-24 | Stage 2.1.1: `/profile` USER-only (staff redirect `/admin`); `/admin` stubs; `/staff/login` optional; `resolvePostLoginPath` post-login routing. |
