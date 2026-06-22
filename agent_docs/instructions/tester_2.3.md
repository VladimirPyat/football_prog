# Tester Instructions — Stage 2.3: Supervisor Admin UI

> **Status gate:** @Coder `READY_FOR_TEST` for 2.3 in `agent_docs/progress/stage_2.md`.
> **Prerequisites:** Sub-stages **2.1** and **2.2** at `TEST_PASS`; backend B1–B6 **RESOLVED** — see `agent_docs/reports/BLOCKED.md`.
> **Reference:** `instructions/coder_2.3.md`, `docs/04_supervisor_scenario.md` (E2E §), `docs/06_front_tests.md`, `agent_docs/contracts/frontend_api_integration.md`.
> **Strategy:** Unit (Vitest) + E2E (Playwright) — **agent runs**; visual/mobile UX — **human** (agent reminds in report).

---

## 1. Objective

Verify Stage **2.3** frontend deliverables:

1. **Unit tests** — `deriveAdminUiMode`, `deadlineRule`, `collectPostponedMatches` (`npm run test:unit`).
2. **E2E (Playwright)** — supervisor admin flows: SETUP, lock after activate, 24h rule, ACTIVE round restrictions, newsletter stub, results workflow, VOID, Free Tour, ADMIN pause, RBAC.
3. **Build** — `npm run build` succeeds.
4. **Docs** — Coder updated living UI specs (§10 of `coder_2.3.md`).
5. **Blockers** — new backend gaps → append `agent_docs/reports/BLOCKED.md`; resolved constraints → confirm Stage 2.3 checklist in `BLOCKED.md`.

**Non-goals (later sub-stages):**

- Public tabbed leaderboard/results polish → **2.4**
- Real newsletter send/scheduling → **Stage 3**
- Full user prediction E2E (`prediction_validation`, `user_full_flow`) → covered in **2.2** / **2.4**
- Visual pixel-perfect match to `supervisor_*.jpg` → **manual human**
- Backend API regression beyond UI integration smoke → Stage 1 tests

---

## 2. Test environment

### 2.1 Backend (Terminal 1)

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/load_test_data.py    # contest id=1 RUNNING, rounds 1–9 CLOSED, round 10 ACTIVE
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

**Data profiles:**

| Profile | Source | Use for |
|---------|--------|---------|
| **Loaded** | `load_test_data.py` → contest `id=1`, `is_locked=true` | LockBanner on settings, Free Tour (round 10), VOID on calculated round (round 9) |
| **Fresh DRAFT** | `POST /api/v1/contests` via E2E fixture | SETUP CRUD, activate → lock, 24h, full results pipeline |

Fresh contests avoid polluting loaded contest state. Prefer **API setup in `beforeEach`** + UI assertions (real backend, no route mocks).

### 2.2 Frontend env

`frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL=/assets/default-team-logo.jpg
```

### 2.3 Credentials

| Role | Login | Password source |
|------|-------|-----------------|
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` from root `.env` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` from root `.env` |
| USER | `user` | `user` (loader) |

Do **not** commit passwords.

### 2.4 Playwright

Same as `tester_2.1.md` §2.4: `webServer` on `:3000`, `baseURL` `http://127.0.0.1:3000`. Both `:8000` and `:3000` must be up.

---

## 3. Scope — files you may create/modify

```
frontend/e2e/fixtures/
  auth.ts                         # extend login helper from 2.1
  adminApi.ts                     # NEW — API helpers: token, createContest, addTeams, createRound, …
frontend/e2e/
  admin_rbac.spec.ts              # NEW
  admin_setup.spec.ts             # NEW — SETUP + lock
  admin_setup_locked.spec.ts      # NEW — LockBanner on loaded contest
  supervisor_create_round.spec.ts # NEW — DRAFT → activate
  supervisor_24h_rule.spec.ts     # NEW — deadline validation + newsletter stub
  supervisor_active_round.spec.ts # NEW — ACTIVE restrictions
  supervisor_free_tour.spec.ts    # NEW — POSTPONED only
  supervisor_results.spec.ts      # NEW — scores → calculate → publish
  supervisor_void_match.spec.ts   # NEW — VOID → leaderboard
  admin_pause.spec.ts             # NEW — ADMIN pause blocks mutations
  admin_logo_upload.spec.ts       # NEW — optional if flaky in CI
agent_docs/reports/test_2.3.md    # NEW — verdict report
```

You may **extend** Coder's Vitest files if coverage gaps found (document in report).

**Do NOT modify:** `docs/`, Python `src/` (backend bugs → report as blockers in `BLOCKED.md`).

---

## 4. E2E fixtures — `adminApi.ts` (recommended)

Use `request` from `@playwright/test` or `fetch` with supervisor token. Example helpers:

```ts
const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

export async function apiLogin(login: string, password: string) {
  const r = await fetch(`${API}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login, password }),
  });
  return (await r.json()).access_token as string;
}

export async function createDraftContest(token: string, name: string) {
  const r = await fetch(`${API}/api/v1/contests`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      total_teams: 4,
      total_rounds: 2,
      matches_per_round: 2,
      is_round_robin: false,
    }),
  });
  return (await r.json()).id as number;
}
```

Add: `addTeam`, `createDraftRound`, `activateRound`, `postponeMatch`, `pauseContest`, `getLeaderboard`, `getPublicResults`.

UI helper:

```ts
export async function loginSupervisor(page: Page) {
  // reuse 2.1 login; assert admin nav reachable
  await login(page, 'supervisor', process.env.E2E_SUPERVISOR_PASSWORD!);
}

export async function selectContestInPicker(page: Page, contestName: string) {
  // ContestPicker — select by visible name
}
```

Store supervisor password in `frontend/.env.local` as `E2E_SUPERVISOR_PASSWORD` (gitignored) or read in test from env passed by CI — never hardcode in spec files.

---

## 5. Unit tests (Vitest) — mandatory

Run from `frontend/`:

```bash
npm run test:unit
```

### 5.1 Required coverage (Coder or Tester adds tests)

| ID | Target | Assert |
|----|--------|--------|
| `[UNIT-DEADLINE-RULE]` | `lib/admin/deadlineRule.ts` | Valid deadline passes; deadline ≥ first_match − Nh fails; uses `deadline_rule_hours` from rules, not hardcoded 24 |
| `[UNIT-UI-MODE-LOCKED]` | `lib/admin/deriveAdminUiMode.ts` | `is_locked` → setup mutations disabled |
| `[UNIT-UI-MODE-PAUSED]` | `deriveAdminUiMode` | `status=PAUSED` → all mutations disabled |
| `[UNIT-UI-MODE-ACTIVE]` | `deriveAdminUiMode` | Round ACTIVE → structure frozen; status/date allowed |
| `[UNIT-UI-MODE-CLOSED]` | `deriveAdminUiMode` | Round CLOSED → results entry enabled |
| `[UNIT-POSTPONED-COLLECT]` | `lib/admin/collectPostponedMatches.ts` | Only `status === 'POSTPONED'` included; dedupe by match id |

**Pass:** all tests green.

---

## 6. E2E tests (Playwright) — mandatory

Use real API. Selectors: `getByRole`, `getByLabel`, Russian visible text from `coder_2.3.md` / screenshots.

Mark slow suites with `test.describe.serial` when they share one fresh contest.

### 6.1 `[E2E-ADMIN-RBAC]` — `admin_rbac.spec.ts`

1. Visitor → `/admin/settings/parameters` → redirect home or login; no admin content.
2. Login as `user/user` → `/admin/rounds` → blocked (redirect or 403 message).
3. Login as supervisor → `/admin/settings/parameters` → 200; `AdminTopNav` tabs visible (**Настройки**, **Туры**, **Рассылки**, **Результаты**).

### 6.2 `[E2E-ADMIN-SETUP]` — `admin_setup.spec.ts`

**Setup:** fresh DRAFT contest via API; select in `ContestPicker`.

1. `/admin/settings/parameters` — edit `total_teams` or `matches_per_round` → **Сохранить** → success (toast or persisted after reload).
2. `/admin/settings/teams` — **Добавить команду** → create 2+ teams; Save enabled while `!is_locked`.
3. `/admin/settings/participants` — invite by email → modal shows `login` + `temp_password` (copy-friendly).
4. Assert: **Добавить/Удалить** participant enabled; no `LockBanner`.

Maps to BLOCKED checklist: **SETUP**.

### 6.3 `[E2E-ADMIN-LOCK]` — `admin_setup_locked.spec.ts` + part of `supervisor_create_round.spec.ts`

**Path A (fresh contest):** after first round **Активировать** in §6.5:

1. Refetch `/admin/settings/parameters` → `LockBanner` visible («Редактирование параметров недоступно…»).
2. Parameters **Сохранить** disabled.
3. Teams: **Добавить команду** / delete disabled.
4. Participants: invite / delete disabled.
5. Optional API check: `GET /contests/{id}` → `is_locked === true`.

**Path B (loaded contest id=1):** supervisor opens settings → same LockBanner + disabled controls without mutating data.

Maps to: **Activate round → is_locked=true → forms disabled**.

### 6.4 `[E2E-SUPERVISOR-CREATE-ROUND]` — `supervisor_create_round.spec.ts`

**Setup:** fresh DRAFT contest + ≥4 teams (API or UI).

1. `/admin/rounds` — `RoundBuilderForm`: 2 matches, deadline **≥3 days** before first match.
2. Create DRAFT → round appears in selector.
3. **Активировать** → confirm modal («редактирование структуры…») → accept.
4. Round status **ACTIVE**; contest locked (§6.3).
5. Assert: add-match / team pickers **disabled**; hint «ТУР АКТИВИРОВАН…» visible.

Source: `docs/04_supervisor_scenario.md` E2E § `supervisor_create_round.spec.ts`.

### 6.5 `[E2E-SUPERVISOR-24H]` — `supervisor_24h_rule.spec.ts`

**Setup:** fresh contest, teams, DRAFT round with first match in **+2 days**.

1. Set deadline to **+1 day** (violates 24h) → **Сохранить** disabled **or** inline error «Дедлайн должен быть не позже чем за N ч…»; no successful PATCH.
2. Set deadline to **+3 days** before first match → Save enabled → save succeeds.
3. After successful deadline PATCH on **ACTIVE** round → **`NewsletterPromptModal`** opens (title about напоминание); **Закрыть** dismisses; **no** network call to newsletter API.

Maps to: **24h rule** + **newsletter stub**.

### 6.6 `[E2E-SUPERVISOR-ACTIVE-ROUND]` — `supervisor_active_round.spec.ts`

**Setup:** ACTIVE round before deadline (fresh or round 10 on loaded contest if deadline not passed).

1. Team1/team2 selectors **disabled**; **Добавить матч** disabled.
2. Change match **status** → **Перенесён** (`POSTPONED`) → save succeeds.
3. Change match **date_time** → save succeeds.
4. Optional: **Отменить** → `CANCELED` → save succeeds.

Maps to: **ACTIVE round: structure frozen; status + date editable**.

### 6.7 `[E2E-SUPERVISOR-FREE-TOUR]` — `supervisor_free_tour.spec.ts`

**Setup:** loaded contest `id=1` — postpone one match in round 10 via UI (or API then UI).

1. Click **+ Добавить свободный тур** / **Свободный тур**.
2. Modal lists **only** POSTPONED matches; SCHEDULED matches **not** selectable.
3. Select match, set new datetime + tour deadline → submit.
4. Assert: new round created; POSTPONED match removed from source round (API `GET …/rounds/{id}/predictions` or UI list count).

Source: `docs/04` §7, `supervisor_free_tour.spec.ts`.

### 6.8 `[E2E-SUPERVISOR-RESULTS]` — `supervisor_results.spec.ts`

**Setup:** fresh contest — full pipeline **or** API helper:

1. Create teams (2×2 matches), activate round.
2. Move all match datetimes + deadline to **past** (API PATCH) so round can close.
3. Enter scores for all matches on `/admin/results` → **Завершён** / result inputs.
4. **Рассчитать** / **calculate** → round `CALCULATED`.
5. **Опубликовать** → `PUBLISHED`; badge **Применено**; inputs disabled.
6. API smoke: `GET /api/v1/contests/{id}/rounds/{roundId}/results` returns non-empty payload.

Alternative on loaded data: use round **9** if UI allows score entry on CLOSED round — document which path used in report.

Maps to: **Results → calculate → publish → public results**.

### 6.9 `[E2E-SUPERVISOR-VOID]` — `supervisor_void_match.spec.ts`

**Setup:** round in **CALCULATED** or **PUBLISHED** state with known leaderboard points (loaded round 9 or fresh after §6.8).

1. `/admin/results` — pick match → **Отменить** → confirm dialog.
2. Match → **VOID**; toast if `recalculation_triggered`.
3. `GET …/leaderboard` (API or public page stub): affected users' points decreased / match contributes 0 (spot-check one user vs pre-VOID snapshot).

Source: `docs/04` §9, `supervisor_void_match.spec.ts`.

### 6.10 `[E2E-ADMIN-PAUSE]` — `admin_pause.spec.ts`

**Setup:** login as **ADMIN**; contest RUNNING (loaded id=1 OK).

1. `/admin/lifecycle` → **Пауза** / pause → success.
2. `ContestStatusBanner` «Конкурс на паузе» on `/admin/rounds` and `/admin/settings/parameters`.
3. Mutation buttons disabled: round save, team add, result entry, activate.
4. **Возобновить** / resume → mutations enabled again (spot-check one button).

Maps to: **ADMIN pause blocks mutations**.

### 6.11 `[E2E-ADMIN-LOGO]` — `admin_logo_upload.spec.ts` (optional)

**Setup:** fresh DRAFT contest.

1. `/admin/settings/teams` — upload small PNG/JPG ≤2MB.
2. Preview updates; `logo_url` from API response used in grid.
3. After `is_locked` — upload control disabled.

Skip with `[SKIP-LOGO-FIXTURE]` if CI lacks test image — note in report; manual required.

Maps to BLOCKED: **Team logo upload (B5)**.

### 6.12 `[E2E-ADMIN-NEWSLETTERS-PLACEHOLDER]` — (in `admin_rbac` or separate)

1. `/admin/newsletters` → static placeholder text «Stage 3» / «недоступны».
2. No crash; tab navigates from `AdminTopNav`.

---

## 7. Build & lint

```bash
cd frontend
npm run lint          # if configured
npm run build
```

| ID | Pass criteria |
|----|---------------|
| `[BUILD]` | `npm run build` exit 0 |
| `[LINT]` | no errors (warnings noted) |

---

## 8. Documentation audit (read-only)

| ID | Pass criteria |
|----|---------------|
| `[DOC-UI-COMPONENTS]` | `agent_docs/ui/components.md` — §5.4 admin components marked **Implemented (2.3)** + paths |
| `[DOC-UI-PAGES]` | `agent_docs/ui/pages.md` — `/admin/*` routes marked ✅ |
| `[DOC-FORMS]` | `agent_docs/ui/forms_validation.md` — admin Zod paths match code |
| `[DOC-INTEGRATION]` | `frontend_api_integration.md` — logo multipart, admin matrix, update log |
| `[DOC-CODER-HANDOFF]` | `stage_2.md` has Coder 2.3 `READY_FOR_TEST` entry |

---

## 9. Blocker verification — `BLOCKED.md`

After all tests:

1. Confirm **Stage 2.3 readiness checklist** items match test results.
2. If all pass and no new API gaps → note in `test_2.3.md`: «Stage 2.3 checklist verified; no new blockers».
3. If UI exposes a **missing or incorrect backend contract** → append to `BLOCKED.md`:

```markdown
### OPEN — B7: …
- **Why:** E2E `[E2E-…]` …
- **Blocks:** 2.3 / 2.4
- **Fallback:** …
```

Do **not** remove RESOLVED B1–B6 entries.

---

## 10. Manual checklist — human developer (agent reminds, does NOT execute)

Per `docs/06_front_tests.md` — include in `test_2.3.md`:

> Разработчик должен вручную проверить перед релизом 2.3:
> - [ ] Layout `AdminTopNav` vs `supervisor_*.jpg` (tabs, contest picker, «Новый конкурс»)
> - [ ] Settings sub-tabs: Параметры / Участники / Команды
> - [ ] `LockBanner` / `ContestStatusBanner` copy and placement
> - [ ] Round editor: disabled states visually distinct (not just silent no-op)
> - [ ] Results grid columns vs `supervisor_results.jpg`
> - [ ] `NewsletterPromptModal` copy; newsletters placeholder page
> - [ ] Team logo 64×64 preview; default asset when no upload
> - [ ] Мобильная ширина ~375px — admin tables horizontal scroll OK

Agent verdict **TEST_PASS** does not require manual checklist completion — only that reminder is present.

---

## 11. Execution order

```bash
# 1. Unit
cd frontend && npm run test:unit

# 2. E2E (backend + frontend up)
npm run test:e2e

# 3. Build
npm run build

# 4. Doc audit + BLOCKED review (read files)
```

Prefer running admin E2E in order: **RBAC → SETUP → create_round → 24h → active → results → void → free_tour → pause** to reduce DB contention. Use fresh contests where tests mutate SETUP state.

---

## 12. Report template — `agent_docs/reports/test_2.3.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-DEADLINE-RULE]` | PASS/FAIL | |
| `[UNIT-UI-MODE-*]` | PASS/FAIL | |
| `[UNIT-POSTPONED-COLLECT]` | PASS/FAIL | |
| `[E2E-ADMIN-RBAC]` | PASS/FAIL | |
| `[E2E-ADMIN-SETUP]` | PASS/FAIL | |
| `[E2E-ADMIN-LOCK]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-CREATE-ROUND]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-24H]` | PASS/FAIL | newsletter modal seen Y/N |
| `[E2E-SUPERVISOR-ACTIVE-ROUND]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-FREE-TOUR]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-RESULTS]` | PASS/FAIL | public GET results OK |
| `[E2E-SUPERVISOR-VOID]` | PASS/FAIL | leaderboard delta noted |
| `[E2E-ADMIN-PAUSE]` | PASS/FAIL | |
| `[E2E-ADMIN-LOGO]` | PASS/FAIL/SKIP | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| BLOCKED.md | OK / NEW B7 | |
| Manual checklist | REMINDER | §10 |

**Verdict:** `TEST_PASS` / `TEST_FAIL` with blockers for @Coder.

On **TEST_PASS:**

- Stage 2.3 frontend ready for **2.4** (public leaderboard/results).
- Stage 2.3 readiness checklist in `BLOCKED.md` can be marked done by user/plan owner.

---

## 13. Acceptance mapping (Coder §11 + BLOCKED checklist)

| Criterion | Test ID |
|-----------|---------|
| SETUP: teams, invite, parameters | `[E2E-ADMIN-SETUP]` |
| Activate → `is_locked` → disabled + LockBanner | `[E2E-ADMIN-LOCK]`, `[E2E-SUPERVISOR-CREATE-ROUND]` |
| 24h blocks invalid deadline in UI | `[E2E-SUPERVISOR-24H]`, `[UNIT-DEADLINE-RULE]` |
| Deadline save → newsletter stub | `[E2E-SUPERVISOR-24H]` |
| ACTIVE: status/date only | `[E2E-SUPERVISOR-ACTIVE-ROUND]`, `[UNIT-UI-MODE-ACTIVE]` |
| Free Tour: POSTPONED only | `[E2E-SUPERVISOR-FREE-TOUR]`, `[UNIT-POSTPONED-COLLECT]` |
| Results calculate → publish | `[E2E-SUPERVISOR-RESULTS]` |
| VOID → leaderboard updated | `[E2E-SUPERVISOR-VOID]` |
| ADMIN pause blocks mutations | `[E2E-ADMIN-PAUSE]`, `[UNIT-UI-MODE-PAUSED]` |
| Logo upload B5 | `[E2E-ADMIN-LOGO]` |
| `deriveAdminUiMode` unit coverage | `[UNIT-UI-MODE-*]` |
| `npm run build` + `test:unit` | `[BUILD]`, `[UNIT-*]` |
| Living docs updated | `[DOC-*]` |

---

## 14. Progress update

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.3.md
- Unit: N passed; E2E: M passed (K skipped)
- Build: OK
- BLOCKED.md: no new blockers / B7 added (…)
- Manual UX checklist: reminded in report §10
- Next: instructions/coder_2.4.md
```

On **TEST_FAIL**, append `STATUS: TEST_FAIL` with `[TEST-ID]` blockers.

---

## 15. Explicitly OUT OF SCOPE

- `[E2E-PREDICT-*]`, `[E2E-PRIVACY-*]` → 2.2
- `[E2E-LEADERBOARD-*]`, public tabbed page → 2.4
- Real newsletter CRUD/send
- «Загрузить по API» schedule import
- `toHaveScreenshot()` vs `docs/screens/` (full visual regression)
- ADMIN lifecycle delete grace-period edge cases (backend `test_contest_lifecycle_1_4.py` covers API)
- Tie-break form / create organizer — smoke optional; not blocking 2.3 unless Coder marked ready
