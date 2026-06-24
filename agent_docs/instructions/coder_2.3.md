# Coder Instructions — Stage 2.3: Supervisor Admin UI

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Sub-stages **2.1** and **2.1.1** at `TEST_PASS` (auth shell + role-based routing + admin stubs). **2.2 is not required** — admin UI can ship before prediction form. Backend B1–B6 **RESOLVED** — see `agent_docs/reports/BLOCKED.md`.
> **Plan:** `agent_docs/plans/draft_2.md` § Sub-stage 2.3, §3.6, §11.2.
> **Specs:** `agent_docs/ui/{components,pages,forms_validation,state_management}.md`, `agent_docs/contracts/frontend_api_integration.md`, `docs/04_supervisor_scenario.md`.
> **Screenshots:** `docs/screens/supervisor_*.jpg` — layout/copy binding for admin shell.
> **Language policy:** UI copy Russian; code comments English; API `detail` shown as-is.

---

## 1. Objective

Implement the **Supervisor/Admin operational UI** under `/admin/*`: contest setup (SETUP), round management, results workflow, and ADMIN lifecycle tools. All **business immutability rules must be visible in the UI** (disabled controls + banners), not only enforced by API errors.

| Deliverable | Description |
|-------------|-------------|
| `AdminTopNav` shell | Tabs: Настройки / Туры / Рассылки / Результаты + contest picker + «Новый конкурс» |
| Settings (3 sub-tabs) | Параметры, Участники, Команды — readonly when `is_locked` |
| Round management | Create DRAFT round, activate, edit ACTIVE (restricted), 24h deadline rule |
| Free Tour modal | Pick **POSTPONED** matches only |
| Results entry | Scores → calculate → publish; VOID with confirm |
| ADMIN pages | Lifecycle (pause/resume/finish/delete), recalculate, tie-break, create organizer |
| UI mode engine | `deriveAdminUiMode(contest, round)` — single source for disabled/read-only |

**Non-goals:**

- Real newsletter send/scheduling API → **Stage 3** (placeholder tab + stub modal on deadline save)
- «Загрузить по API» match import → **manual entry only**
- Public tabbed leaderboard/results polish → **2.4**
- Playwright E2E full supervisor suite → **tester_2.3** (Coder adds no E2E unless asked)

---

## 2. Backend prerequisites (verified)

All items in `BLOCKED.md` status table are **RESOLVED** for 2.3:

| ID | Needed for 2.3 | Endpoint / note |
|----|----------------|-----------------|
| B5 | Team logo upload | `POST /api/v1/contests/{id}/teams/{team_id}/logo` (multipart) |
| B6 | Participant status badge | `PENDING` → `ACCEPTED` on password change |
| — | All admin routes | `agent_docs/contracts/api_v1.yaml` v1.2.0 |

**No new backend blockers** for 2.3. If integration reveals a missing endpoint during implementation, append a row to `agent_docs/reports/BLOCKED.md` (do not mock).

**Client-side workaround (not a blocker):** there is no `GET /admin/postponed-matches`. Build Free Tour list by scanning `GET …/rounds` + `GET …/rounds/{id}/predictions` → collect `matches[]` where `status === 'POSTPONED'`.

---

## 3. UI immutability rules (mandatory)

Implement `lib/admin/deriveAdminUiMode.ts` returning flags consumed by all admin forms.

### 3.1 Contest-level (`ContestOut`)

| Signal | UI behaviour |
|--------|--------------|
| `is_locked === false` (SETUP) | Parameters, teams CRUD, participants add/remove **enabled** |
| `is_locked === true` | Show `LockBanner`: «Редактирование параметров недоступно — Конкурс уже запущен…»; **disable** parameters PATCH, team POST/DELETE, participant POST/DELETE; values **readonly** |
| `status === 'PAUSED'` | `ContestStatusBanner`: «Конкурс на паузе»; **disable all mutation buttons** (rounds, results, setup) |
| `status === 'FINISHED'` | Read-only admin; only ADMIN recalculate/lifecycle per role |
| `status === 'DRAFT'` (contest, not round) | Full SETUP before first activation |

First round **activate** sets `is_locked=true` and contest `RUNNING` — refresh contest after activate.

### 3.2 Round-level (`RoundOut` + matches)

| Round status | UI behaviour |
|--------------|--------------|
| **DRAFT** | Create/edit matches (≤ `matches_per_round`), set deadline, **Активировать** with confirm modal |
| **ACTIVE** | **Structure frozen:** no add/remove matches, no team1/team2 swap, no «create round» overwrite. **Allowed:** match **status** (`SCHEDULED`→`POSTPONED`/`CANCELED`), match **date_time** (per backend + screenshot). **Deadline:** editable only if client 24h pre-check passes; on successful save → **NewsletterPromptModal** (stub). Show hint: «ТУР АКТИВИРОВАН. Менять можно только статус матча и дату.» |
| **ACTIVE + deadline passed** | Same as ACTIVE but emphasize warning: «Дедлайн прошел. Менять команды нельзя. Только статус и дату.» Disable deadline if `<24h` to first match would fail |
| **CLOSED** | Round editor readonly; **Results** page enabled for score entry |
| **CALCULATED** | Results locked; show **Опубликовать** |
| **PUBLISHED** | Fully immutable; badge «Применено» |

**User rule (stricter than backend where needed):** after activation, treat tour as **non-editable** except match **status** changes (postpone/cancel) and **date/time** — never re-open team pickers or match count.

### 3.3 Match status (round editor + results)

| Action | UI | API |
|--------|-----|-----|
| Перенести | status → `POSTPONED` | `PATCH …/admin/matches/{id}/status` |
| Отменить (в туре) | status → `CANCELED` | same |
| Отменить (VOID, results) | `ConfirmDialog` → `VOID` | same; toast if `recalculation_triggered` |

### 3.4 24-hour deadline rule

Client pre-check before PATCH deadline (mirror `round_service.set_deadline`):

```ts
deadline <= earliestMatchDateTime - deadline_rule_hours * 3600_000
```

- `deadline_rule_hours` from `contest.rules_json.contest_structure.deadline_rule_hours` (not hardcoded 24).
- Invalid → disable Save + inline error «Дедлайн должен быть не позже чем за N ч до первого матча».
- Still handle API `400`/`403` if client clock differs.

### 3.5 Newsletter stub (Stage 3)

On **successful deadline change** (PATCH round deadline):

```tsx
<NewsletterPromptModal
  open={showNewsletterStub}
  title="Отправить напоминание участникам?"
  body="Функция рассылок будет доступна на Stage 3. Сохранить без рассылки."
  primaryLabel="Закрыть"
/>
```

No API call — informational only. Same pattern optional after round activation (defer unless time).

---

## 4. Scope — files to create/modify

```
frontend/src/
  app/admin/
    layout.tsx                          # AdminTopNav + requireRole SUPERVISOR+
    settings/
      layout.tsx                        # sub-tabs: Параметры | Участники | Команды
      parameters/page.tsx
      participants/page.tsx
      teams/page.tsx
    rounds/page.tsx
    results/page.tsx
    newsletters/page.tsx                # placeholder Stage 3
    lifecycle/page.tsx                  # ADMIN only
    users/page.tsx                      # ADMIN only — create organizer
  components/admin/
    AdminTopNav.tsx
    SettingsSubNav.tsx
    LockBanner.tsx
    ContestStatusBanner.tsx
    ContestParametersForm.tsx
    ParticipantsTable.tsx
    ParticipantInviteForm.tsx
    ParticipantInviteModal.tsx          # shows temp_password
    TeamsGrid.tsx
    TeamForm.tsx
    TeamLogoUpload.tsx                  # B5 multipart
    RoundManagementPanel.tsx
    RoundBuilderForm.tsx                # DRAFT create
    MatchEditorRow.tsx
    FreeTourModal.tsx
    ResultsEntryPanel.tsx
    MatchResultRow.tsx
    NewsletterPromptModal.tsx           # stub
    LifecyclePanel.tsx
    TiebreakForm.tsx
    CreateOrganizerForm.tsx
    CreateContestForm.tsx
  lib/admin/
    deriveAdminUiMode.ts
    collectPostponedMatches.ts
    deadlineRule.ts                     # 24h client check
  lib/api/endpoints.ts                  # extend admin paths
  hooks/
    useContestAdmin.ts                  # GET/PATCH contest
    useTeams.ts
    useParticipants.ts
    useAdminRounds.ts
    useRoundMatches.ts                  # GET predictions → matches[]
    useAdminResults.ts

agent_docs/ui/components.md             # UPDATE §5.4 admin + paths
agent_docs/ui/pages.md                  # UPDATE §2 admin routes ✅
agent_docs/ui/forms_validation.md       # UPDATE admin Zod if paths differ
agent_docs/ui/state_management.md       # UPDATE admin hooks
agent_docs/contracts/frontend_api_integration.md  # logo multipart, admin matrix
agent_docs/progress/stage_2.md          # APPEND handoff
manuals/FRONTEND_REFERENCE.md           # APPEND §2.3 routes, components, editable copy
```

Copy default team logo per `coder_1.9.md`:

```
frontend/public/assets/default-team-logo.jpg   # from static/assets/ or docs/screens/
NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL=/assets/default-team-logo.jpg
```

---

## 5. Admin shell & routing

### 5.1 `AdminTopNav` (`supervisor_*.jpg`)

- Brand `SportPrognosis` + `Сегодня DD.MM.YYYY`
- Tabs (highlight active):
  - **Настройки** → `/admin/settings/parameters`
  - **Туры** → `/admin/rounds`
  - **Рассылки** → `/admin/newsletters` (placeholder)
  - **Результаты** → `/admin/results`
- Right: `ContestPicker` (`GET /contests`) + `+ Новый конкурс` → `CreateContestForm` modal
- Guard: `ProtectedRoute requireRole(['SUPERVISOR','ADMIN'])`
- USER role → redirect `/` or 403 toast

### 5.2 Settings layout

Shared header: `{contest.name} — Настройки` + `SettingsSubNav` tabs.

Redirect `/admin/settings` → `/admin/settings/parameters`.

---

## 6. Pages & API mapping

All paths prefixed with `/api/v1/contests/{contestId}` unless noted.

### 6.1 Parameters — `/admin/settings/parameters`

**Source:** `GET/PATCH …/` (contest detail).

- Fields: `total_teams`, `total_rounds`, `matches_per_round`, `is_round_robin` (label «Произвольное количество» = inverted checkbox).
- Scoring cards: read values from `rules_json` (display-only in 2.3 if PATCH rules blocked when locked).
- Save disabled when `is_locked`.
- ADMIN: red **Остановить конкурс** → link to lifecycle or inline pause/finish confirm.

### 6.2 Participants — `/admin/settings/participants`

| Action | API | When disabled |
|--------|-----|---------------|
| List | `GET …/participants` | — |
| Invite | `POST …/participants` | `is_locked` |
| Delete | `DELETE …/participants/{user_id}` | `is_locked` |
| Tie-break | `PUT …/participants/{uid}/exceptional-tiebreak` | ADMIN only; **allowed when locked** |

- Table columns: Имя, Email (+ invite button per row if design matches screenshot), Статус (`PENDING`→«Ожидает», `ACCEPTED`→«Принято»), Действия.
- On invite success: modal with `login`, `temp_password` (copy-friendly).

### 6.3 Teams — `/admin/settings/teams`

| Action | API | When disabled |
|--------|-----|---------------|
| List | `GET …/teams` | — |
| Create | `POST …/teams` | `is_locked` |
| Patch | `PATCH …/teams/{id}` | `is_locked` |
| Delete | `DELETE …/teams/{id}` | `is_locked` |
| Logo | `POST …/teams/{id}/logo` multipart field `file` | `is_locked` |

- Grid: 2-letter badge + name; use `logo_url` or `NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL`.
- Form note: «Доступно только до старта конкурса» when `!is_locked`.
- Validate: `short_name` max 4 chars; file PNG/JPG/GIF ≤2MB client-side.

### 6.4 Rounds — `/admin/rounds` (`supervisor_tours.jpg`)

**Data:**

- `GET …/rounds` — round dropdown
- `GET …/rounds/{id}/predictions` — `matches[]` for selected round (supervisor auth OK)
- `GET …/teams` — team pickers for DRAFT builder only

**DRAFT flow:**

1. `RoundBuilderForm`: number, deadline, up to `matches_per_round` rows (team1, team2, datetime).
2. Zod: unique teams in round, 24h deadline rule, count ≤ limit.
3. `POST …/admin/rounds` → `{ round_id, status: 'DRAFT' }`.
4. **Активировать** → `ConfirmDialog`: «После активации редактирование структуры тура будет запрещено» → `POST …/admin/rounds/{id}/activate`.
5. Refetch contest (`is_locked` should become true on first activation).

**ACTIVE editing:**

- `PATCH …/admin/rounds/{id}` with `{ deadline?, matches: [{ match_id, date_time?, status? }] }`.
- UI disables fields per §3.2.
- On deadline PATCH success → `NewsletterPromptModal`.

**Free Tour:**

- Button `+ Добавить свободный тур` → `FreeTourModal`.
- List from `collectPostponedMatches(contestId)` — checkbox per POSTPONED match, new datetime per match, tour deadline.
- `POST …/admin/rounds/free-tour`.

**No «Загрузить по API»** button (or disabled with tooltip «Stage 3+»).

### 6.5 Results — `/admin/results` (`supervisor_results.jpg`)

**Round selector** → load matches via `GET …/rounds/{id}/predictions` or results when available.

| Step | Condition | API |
|------|-----------|-----|
| Enter scores | round `CLOSED`, all matches finished | `PUT …/admin/matches/{id}/result` |
| Calculate | all FINISHED scores entered | `POST …/admin/rounds/{id}/calculate` |
| Publish | status `CALCULATED` | `POST …/admin/rounds/{id}/publish` |

- Per row: match name, date, `[Завершён]` (sets FINISHED via result PUT), `[Отменить]` → VOID confirm.
- After calculate+publish: inputs disabled, badge **Применено**.
- Verify public: `GET …/rounds/{id}/results` returns data (smoke link to `/contest/{id}` tab in 2.4).

**VOID → leaderboard:** after VOID on calculated round, optional `GET …/leaderboard` shows updated points (tester verifies).

### 6.6 Newsletters — `/admin/newsletters`

Static placeholder: «Раздел рассылок — Stage 3. Создание и отправка писем пока недоступны.»

### 6.7 Lifecycle — `/admin/lifecycle` (ADMIN)

- `POST …/pause` | `…/resume` | `…/finish`
- `DELETE …/` body `{ confirm: 'DELETE' }` with grace warning
- `POST …/admin/recalculate`
- When `PAUSED`: banner + disable mutations app-wide via `deriveAdminUiMode`

### 6.8 Users — `/admin/users` (ADMIN)

- `POST /api/v1/admin/users/supervisor` — create organizer form per `manuals/API_GUIDE.md`

---

## 7. API client extensions

Add to `lib/api/endpoints.ts` and typed wrappers:

```ts
// multipart example — team logo
async function uploadTeamLogo(contestId: number, teamId: number, file: File) {
  const fd = new FormData();
  fd.append('file', file);
  return apiFetch<{ logo_url: string }>(
    `/api/v1/contests/${contestId}/teams/${teamId}/logo`,
    { method: 'POST', body: fd, headers: {} /* no Content-Type; browser sets boundary */ },
  );
}
```

Handle `403` codes: `CONTEST_LOCKED`, `CONTEST_NOT_RUNNING`, `DEADLINE_PASSED` → toast + sync UI mode.

---

## 8. Validation (Zod)

Reuse schemas from `agent_docs/ui/forms_validation.md`:

- `ContestParametersForm`, `TeamForm`, `ParticipantInviteForm`, `RoundBuilderForm`, `MatchResultForm`, `FreeTourModal`, `TiebreakForm`, `CreateOrganizerForm`, `CreateContestForm`.

Add `deadlineRule.ts` unit tests mirroring backend edge cases.

---

## 9. Unit tests (Vitest) — add in 2.3

| File | Tests |
|------|-------|
| `lib/admin/deadlineRule.test.ts` | 24h pass/fail boundaries |
| `lib/admin/deriveAdminUiMode.test.ts` | locked/paused/round status flags |
| `lib/admin/collectPostponedMatches.test.ts` | filters POSTPONED only |

Run: `npm run test:unit`.

---

## 10. Documentation maintenance (required)

### 10.1 Living specs (`agent_docs/`)

Same as 2.1 — update living docs with **Implemented (2.3)** annotations and file paths; append update log rows.

| File | Updates |
|------|---------|
| `agent_docs/ui/components.md` | Admin components + paths |
| `agent_docs/ui/pages.md` | Full `/admin/*` route map |
| `agent_docs/ui/forms_validation.md` | Admin Zod forms |
| `agent_docs/ui/state_management.md` | Admin hooks |
| `agent_docs/contracts/frontend_api_integration.md` | Logo multipart, admin API matrix |

### 10.2 Human frontend map (`manuals/FRONTEND_REFERENCE.md`) — required

Append to **§ Stage 2.3** (do not overwrite prior stages). Goal: a human can find and edit admin UI copy without searching the repo.

For **each new `/admin/*` route** add a row (route, page file, role guard, main features).

For **each new or materially changed admin component** add a row (component, source file, editable Russian copy, notes).

Include at minimum for 2.3:

- `/admin/settings/{parameters,participants,teams}`, `/admin/rounds`, `/admin/results`, `/admin/newsletters`, `/admin/lifecycle`, `/admin/users`
- `AdminTopNav`, `LockBanner`, `ContestStatusBanner`, modals (`ParticipantInviteModal`, `FreeTourModal`, `NewsletterPromptModal`)
- Key mutation buttons and banners («Активировать», «Опубликовать», 24h errors, lock/pause messages)

Append one row to **Update log** at the bottom of `FRONTEND_REFERENCE.md`.

If a **new backend gap** is discovered, add to `BLOCKED.md`:

```markdown
### OPEN — B7: …
- **Why:** …
- **Blocks:** 2.3 …
- **Fallback:** …
```

---

## 11. Acceptance criteria (2.3 done)

Manual + automated (tester_2.3):

- [ ] **SETUP:** create teams, invite participant (show `temp_password`), edit parameters — while `!is_locked`
- [ ] **Activate round** → `is_locked=true` → parameters/teams/participants forms **disabled**, `LockBanner` visible
- [ ] **24h rule** blocks invalid deadline in UI (Save disabled + error before API)
- [ ] **Deadline change** → `NewsletterPromptModal` stub appears (no send)
- [ ] **ACTIVE round:** team/add-match disabled; status POSTPONED/CANCELED works; date editable
- [ ] **Free Tour:** only POSTPONED matches selectable; new tour created
- [ ] **Results:** enter scores → **calculate** → **publish** → public `GET …/results` has data
- [ ] **VOID match** (after calculated) → leaderboard reflects zero/recalc (spot-check)
- [ ] **ADMIN pause** → mutation buttons disabled across admin
- [ ] **Logo upload** works (B5); default logo when none
- [ ] `npm run build` + `npm run test:unit` pass
- [ ] Living docs updated
- [ ] `manuals/FRONTEND_REFERENCE.md` §2.3 appended (routes + components + copy)

---

## 12. Implementation order

1. `deriveAdminUiMode` + banners
2. `AdminTopNav` + `/admin/layout.tsx` guards
3. Settings: parameters → participants → teams (+ logo upload)
4. Rounds: DRAFT builder → activate → ACTIVE editor + 24h + newsletter stub
5. `FreeTourModal` + postponed collector
6. Results panel + calculate/publish workflow
7. ADMIN lifecycle + users + tie-break on participants
8. Newsletters placeholder page
9. Vitest for admin rules
10. Update `agent_docs/ui/*`, `frontend_api_integration.md`, `BLOCKED.md` if needed
11. Append `manuals/FRONTEND_REFERENCE.md` §2.3
12. Append handoff → `stage_2.md`

---

## 13. Handoff

Append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Coder (2.3 supervisor admin UI)
- STATUS: READY_FOR_TEST
- Scope: /admin settings, rounds, results, lifecycle, B5 logo upload
- UI rules: is_locked readonly, ACTIVE round restrictions, 24h, newsletter stub
- Verified: npm run build, npm run test:unit; manual checklist §11
- Docs updated: ui/*, frontend_api_integration.md, manuals/FRONTEND_REFERENCE.md §2.3
- Next: agent_docs/instructions/tester_2.3.md
```

---

## 14. Explicitly OUT OF SCOPE

- Sending emails / newsletter CRUD
- External schedule API import
- Public leaderboard tab polish (2.4)
- Full Playwright supervisor suite (tester)
- Mobile-specific admin layouts beyond horizontal scroll
