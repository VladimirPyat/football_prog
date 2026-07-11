# Coder Instructions — Stage 2.1.2: Supervisor Admin UI Fixes

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 2.3 admin shell implemented (`coder_2.3` / current `frontend/src/app/admin/*`).
> **Related backend:** `agent_docs/instructions/coder_1.12_fix.md` (B11 invite/setup, B12 lifecycle, `request-password-reset` API)
> **Scenarios:** `docs/04_supervisor_scenario.md`
> **Reference screens:** `docs/screens/supervisor_settings.jpg`, `docs/screens/supervisor_tours.jpg`, `docs/screens/supervisor_results.jpg`
> **Language policy:** UI copy Russian; code comments English; API `detail` shown as-is.

---

## 1. Objective

Fix supervisor-facing admin UI gaps reported during manual QA. Align behaviour with `docs/04_supervisor_scenario.md` and reference screenshots.

| # | Area | Problem (reported) | Target |
|---|------|-------------------|--------|
| 1 | `/admin/settings/parameters` | Scoring/bonus params not visible; no start/stop contest control | Full read-only rules display + lifecycle CTA per contest status |
| 2 | `/admin/settings/teams` | Default logo 404; uploaded logos invisible | Resolve backend static URLs correctly |
| 3 | `/admin/rounds` | No “create tour” when contest running; missing tour status sidebar | Create draft round anytime; status card per mockup |
| 4 | `/admin/results` | Cannot save results; match status raw English | CLOSED-round workflow + Russian labels + close-tour path |
| 5 | Participants | Cannot confirm invite without user login | **Backend** — `coder_1.12_fix` (B11); modal shows login + temp password + link |
| 6 | Login (`LoginForm`, modal, `/staff/login`) | No password recovery | Checkbox «Забыли пароль?» → email → `request-password-reset` (§4.6) |

**Non-goals (this sub-stage):**

- Full newsletter UI
- E2E suite expansion (tester follow-up)
- Backend logo pipeline changes (upload path is correct; frontend must prefix API host)

---

## 2. Root-cause summary (verified in code)

### 2.1 Parameters — empty scoring section

`ContestParametersForm.tsx` reads wrong keys from `rules_json`:

```ts
const scoring = (rules.scoring as Record<string, unknown>) ?? {};
const bonuses = (rules.bonuses as Record<string, unknown>) ?? {};
```

Backend stores `contest_defaults.json` shape:

```json
{
  "contest_structure": { "total_teams", "matches_per_round", "total_rounds", "deadline_rule_hours", "max_score_value", ... },
  "scoring_rules": {
    "base_points": { "exact_high_score", "exact_score", "diff_plus_outcome", "outcome_only", "miss" },
    "bonuses": { "bonus_1_unique_multiplier_pct", "bonus_2_thresholds", "bonus_3_rank_points", ... }
  },
  "constraints": { ... },
  "tiebreakers": { ... }
}
```

→ `Object.entries(scoring)` is always empty → user sees no rules.

Structural fields (`total_teams`, etc.) **do** bind from `ContestOut` top-level fields — they appear but are readonly when `is_locked`.

### 2.2 Start / Stop contest button

- Screenshot (`supervisor_settings.jpg`): red **«Остановить конкурс»** bottom-right when contest is running.
- Current code: link to `/admin/lifecycle` only for `role === "ADMIN"` (`ContestParametersForm.tsx:142–150`).
- `/admin/lifecycle` redirects non-ADMIN away (`lifecycle/page.tsx:67–68`).
- **Supervisor never sees stop/start controls.**
- API: `POST /contests/{id}/pause|resume|finish` is **ADMIN-only** (`contests.py`, `frontend_api_integration.md` §5.2). See blocker **B12** in §3.

“Запустить” semantics:

| Contest status | Meaning | UI action |
|----------------|---------|-----------|
| `DRAFT`, `!is_locked` | Setup, not started | Hint: activate first round on `/admin/rounds` (first activation → `RUNNING` + `is_locked`) |
| `RUNNING` | Active | **Остановить конкурс** → `POST …/pause` |
| `PAUSED` | Stopped | **Запустить конкурс** → `POST …/resume` |
| `FINISHED` | Ended | No start/stop; show banner only |

### 2.3 Team logos — 404

| Source | URL used | Served at |
|--------|----------|-----------|
| Frontend fallback `DEFAULT_TEAM_LOGO_URL` | `/assets/default-team-logo.jpg` | Next.js `:3000` → **404** |
| Backend default (`settings.default_team_logo_url`) | `/static/assets/default-team-logo.jpg` | FastAPI `:8000` ✅ |
| Uploaded logo (`team_logo_service._public_logo_url`) | `/static/teams/{contest_id}/{team_id}.jpg` | FastAPI `:8000` ✅ |

`TeamsGrid` uses `<img src={team.logo_url || DEFAULT_TEAM_LOGO_URL}>` with **no API host prefix**. `next.config.mjs` has no `/static` proxy.

### 2.4 Rounds — cannot create tour

`RoundManagementPanel.tsx:178`:

```tsx
{uiMode.canEditRoundStructure && !hasDraft && (
  <RoundBuilderForm ... />
)}
```

`canEditRoundStructure` = selected round is `DRAFT` (`deriveAdminUiMode.ts:49`).

When supervisor selects **ACTIVE** tour 2 (normal running contest), `canEditRoundStructure` is `false` → **create form hidden**. Only «+ Добавить свободный тур» remains.

`canCreateRound` is computed but **never used**.

Screenshot sidebar **«Статус тура»** (badge, team count, max matches, info box) — **not implemented**.

### 2.5 Results — cannot save

`deriveAdminUiMode.ts:66`:

```ts
const canEnterResults = roundStatus === "CLOSED" && !disableAllMutations;
```

Results page dropdown filters to `CLOSED | CALCULATED | PUBLISHED` only — correct.

Failure modes:

1. User picks tour still `ACTIVE` (deadline passed but not closed) — not in dropdown; no guidance.
2. `closeRound` exists in `useAdminRounds` but is **not wired** in rounds/results UI.
3. `MatchResultRow` shows raw `match.status` (English); save button label «Завершён» not «Применить результаты» per scenario §8.
4. After all matches `FINISHED`, user must click **«Рассчитать»** then **«Опубликовать»** — workflow may be unclear; add hints.

Backend requires round `CLOSED` before `PUT …/matches/{id}/result` (`api_v1.yaml`).

### 2.6 Participant confirmation

`POST /contests/{id}/participants` creates user with `PENDING` status + `temp_password`.

Only path to `ACCEPTED`: `POST /auth/change-password` flips all `PENDING` rows for that user (`participant_service.py`, `api_v1.yaml` auth description).

**No endpoint** to accept on behalf of user. Supervisor cannot complete invite flow without user action. See blocker **B11**.

---

## 3. Backend blockers (do not fake in frontend)

Document in `agent_docs/reports/BLOCKED.md` if not resolved before coding.

### B11 — Participant accept without user login

| Field | Value |
|-------|-------|
| **Need** | Supervisor (or dev script) can flip `contest_participants.status` `PENDING → ACCEPTED` without `change-password` |
| **Workaround (interim)** | Dev script `src/scripts/accept_participants.py --contest-id N --login user@mail` |
| **Target API (later)** | `PATCH /api/v1/contests/{contest_id}/participants/{user_id}` body `{ "status": "ACCEPTED" }` (SUPERVISOR+, SETUP only) **or** `POST …/participants/{user_id}/accept` |
| **Frontend (this stage)** | If API missing: show toast on invite «Приглашение создано. Участник должен сменить временный пароль»; add TODO in participants table for manual accept button once B11 resolved |

**Coder backend stub (minimal, if assigned):**

```python
# src/scripts/accept_participants.py
# CLI: flip PENDING → ACCEPTED for contest_id + login/email
```

### B12 — Supervisor pause/resume

| Field | Value |
|-------|-------|
| **Need** | Supervisor can pause/resume own contest (screenshot + `04_supervisor_scenario.md`) |
| **Current** | `POST /contests/{id}/pause|resume` → `RoleChecker(ADMIN)` only |
| **Fix** | Change dependency to `RoleChecker(SUPERVISOR, ADMIN)` in `src/api/v1/contests.py` |
| **Frontend** | Wire buttons for SUPERVISOR; until B12 fixed, show button disabled + tooltip «Требуется право ADMIN» **only if** API returns 403 — prefer fixing B12 in same PR |

### B13 — Uploaded team logos (frontend-only; not a backend blocker)

Track as frontend task: prefix `NEXT_PUBLIC_API_URL` for paths starting with `/static/`. No backend change required.

---

## 4. Implementation tasks

### 4.1 Parameters page — display `rules_json` correctly

**Files:**

- `frontend/src/lib/admin/rulesDisplay.ts` (**new**)
- `frontend/src/components/admin/ContestParametersForm.tsx`
- `frontend/src/components/admin/ContestLifecycleActions.tsx` (**new**)
- `frontend/src/app/admin/settings/parameters/page.tsx`

**`rulesDisplay.ts`:**

Parse `contest.rules_json` and return labeled sections for UI (Russian labels per `supervisor_settings.jpg`):

| Key path | Label |
|----------|-------|
| `scoring_rules.base_points.exact_high_score` | За предсказанный крупный счёт |
| `scoring_rules.base_points.exact_score` | За точный счёт |
| `scoring_rules.base_points.diff_plus_outcome` | За правильную разницу мячей |
| `scoring_rules.base_points.outcome_only` | За правильный исход |
| `scoring_rules.bonuses.bonus_1_unique_multiplier_pct` | Бонус 1: Уникальный прогноз (%) |
| `scoring_rules.bonuses.bonus_2_thresholds` | Бонус 2: Угадано N матчей (render table) |
| `scoring_rules.bonuses.bonus_3_rank_points` | Бонус 3: Топ-3 места в туре |
| `scoring_rules.bonuses.bonus_3_base_threshold_extra` + `bonus_3_extra_points` | Дополнительно (порог очков) |

Also show read-only from `contest_structure`: `deadline_rule_hours`, `max_score_value` if useful.

Replace raw `Object.entries(scoring)` blocks with `RulesDisplayPanel` component using this helper.

**Layout:** two columns «Основные очки» | «Бонусы» like screenshot.

**Lifecycle CTA (`ContestLifecycleActions`):**

Place fixed bottom-right (or below form) per mockup:

```tsx
// RUNNING → red button «Остановить конкурс» → POST contests.pause(id)
// PAUSED  → green «Запустить конкурс» → POST contests.resume(id)
// DRAFT   → blue link «Перейти к турам для запуска» → /admin/rounds
// FINISHED → no button
```

- Visible for **SUPERVISOR and ADMIN** (remove `role === "ADMIN"` gate).
- Use `useContestAdmin().contestId`, `apiPost`, `refetch`, `ConfirmDialog`.
- On success: toast + refetch contest.

**Lock banner:** keep `LockBanner` when `is_locked`; extend copy to match screenshot: «Изменение правил scoring или состава команд невозможно.»

**Tests:** unit test `rulesDisplay.ts` with fixture from `config/contest_defaults.json` shape.

---

### 4.2 Team logos — resolve asset URLs

**Files:**

- `frontend/src/lib/api/resolveAssetUrl.ts` (**new**)
- `frontend/src/lib/admin/format.ts` — fix default constant
- `frontend/src/components/admin/TeamsGrid.tsx`

**`resolveAssetUrl(url: string): string`:**

```ts
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
if (url.startsWith("http://") || url.startsWith("https://")) return url;
if (url.startsWith("/static/")) return `${API}${url}`;
return url; // relative non-static — rare
```

**`format.ts`:**

```ts
export const DEFAULT_TEAM_LOGO_URL =
  process.env.NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL ??
  `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/static/assets/default-team-logo.jpg`;
```

**`TeamsGrid`:**

```tsx
src={resolveAssetUrl(team.logo_url || DEFAULT_TEAM_LOGO_URL)}
```

Add `onError` fallback to `DEFAULT_TEAM_LOGO_URL` once (broken upload file).

**Verify:** Network tab shows `GET http://127.0.0.1:8000/static/assets/default-team-logo.jpg` → 200.

**TODO comment (B13):** any other `<img src={logo_url}>` in admin/participant UI — grep and apply same helper.

---

### 4.3 Rounds page — create tour + status sidebar

**Files:**

- `frontend/src/lib/admin/deriveAdminUiMode.ts`
- `frontend/src/components/admin/RoundManagementPanel.tsx`
- `frontend/src/components/admin/RoundStatusSidebar.tsx` (**new**)

**Fix create-round visibility:**

Change condition for `RoundBuilderForm` from:

```tsx
uiMode.canEditRoundStructure && !hasDraft
```

to:

```tsx
!hasDraft && !uiMode.disableAllMutations
```

Always show section title **«Создать тур»** (not only inside DRAFT selected round). `RoundBuilderForm` already has heading «Создать тур (черновик)».

Update `canCreateRound` in `deriveAdminUiMode.ts`:

```ts
const canCreateRound = !disableAllMutations && !rounds.some(r => r.status === "DRAFT");
```

Pass `hasDraft` from rounds list OR use inside panel. Wire `canCreateRound` to form `disabled` prop.

**`RoundStatusSidebar`** (right column on `lg:` grid, per `supervisor_tours.jpg`):

When `selectedRound` set, show card:

- **Статус тура** — badge with `roundStatusLabel(status)`; map colors: DRAFT gray, ACTIVE green, CLOSED orange, CALCULATED blue, PUBLISHED purple (`draft_2.md`)
- **Команд:** `contest.total_teams`
- **Макс. матчей:** `contest.matches_per_round`
- **Матчей в туре:** `matches.length` / `matches_per_round`
- Info box when `ACTIVE`: «ТУР АКТИВИРОВАН. Менять можно только статус матча и дату.»
- When `ACTIVE && deadlinePassed`: show **«Закрыть тур»** button → `closeRound(roundId)` then refetch (enables results entry)

Wire `closeRound` from `useAdminRounds` in `admin/rounds/page.tsx` → pass to panel.

**Match status in table:** use `matchStatusLabel()` — add to `format.ts` (mirror `MatchEditorRow` STATUS_OPTIONS + FINISHED, VOID).

When `!canEditStatusAndDate`, show Russian label not raw enum.

---

### 4.4 Results page — save workflow

**Files:**

- `frontend/src/components/admin/ResultsEntryPanel.tsx`
- `frontend/src/components/admin/MatchResultRow.tsx`
- `frontend/src/lib/admin/format.ts`
- `frontend/src/app/admin/results/page.tsx`

**Close tour path:**

If selected round is `ACTIVE` and deadline passed (reuse `useRoundMatches.deadlinePassed`):

- Show amber banner: «Дедлайн прошёл. Закройте тур, чтобы ввести результаты.»
- Button **«Закрыть тур»** → `closeRound` → refetch rounds (round becomes `CLOSED`, appears in results dropdown).

Import `closeRound` from `useAdminRounds` in results page.

**Match status:** `matchStatusLabel(match.status)` in `MatchResultRow`.

**Save button:** rename «Завершён» → **«Сохранить»** or **«Применить»** per row; keep per-match save (API is per-match). Add section hint:

> «Введите счёт для каждого матча и нажмите „Применить“. Когда все матчи завершены — „Рассчитать“, затем „Опубликовать“.»

**Empty state:** if no `CLOSED|CALCULATED|PUBLISHED` rounds:

> «Нет туров, готовых к вводу результатов. Закройте активный тур на странице „Туры“.»

**Optional:** after last match saved, auto-focus «Рассчитать» button.

**Unit:** extend `deriveAdminUiMode.test.ts` — ACTIVE + deadlinePassed should not set `canEnterResults`.

---

### 4.5 Participants — document B11

**Files:**

- `frontend/src/app/admin/settings/participants/page.tsx`
- `frontend/src/components/admin/ParticipantsTable.tsx` (if exists)

No fake accept button without API. Ensure status column shows `participantStatusLabel` («Ожидает» / «Принято»).

After invite modal: clarify copy that acceptance happens when user changes temp password.

Add comment + link to B11 in code:

```ts
// B11: full accept flow in coder_1.12_fix — invite modal shows setup_url
```

---

### 4.6 Login — password recovery (checkbox)

**Prerequisite:** `POST /api/v1/auth/request-password-reset` from `coder_1.12_fix.md` §2.4.

**Files:**

- `frontend/src/components/auth/LoginForm.tsx` (shared by `LoginModal`, `/staff/login`)
- `frontend/src/components/auth/PasswordResetRequest.tsx` (**new**, optional extract)
- `frontend/src/lib/api/endpoints.ts` — `auth.requestPasswordReset`
- `frontend/src/lib/validation/login.ts` — optional `emailSchema` for reset

**UX (Russian):**

Below the password field, before «Войти»:

```
☐ Забыли пароль?
```

When **checked**, expand inline block (do not navigate away):

| Field | Label |
|-------|-------|
| Email | «Email, указанный при регистрации» |
| Button | «Отправить ссылку для восстановления» |

**Behaviour:**

1. Checkbox toggles visibility of email + submit (collapsed by default).
2. `POST /auth/request-password-reset` with `{ email }`.
3. **Always** show success copy (even if email unknown — API privacy):  
   «Если адрес найден, мы отправили ссылку для восстановления пароля.»
4. On API error (network/500) — toast or inline error with `detail`.
5. Unchecking checkbox hides block; does not clear success message until form remount (optional).

**Scope:** same component on:

- `LoginModal` (header «Вход»)
- `/staff/login` page

**Out of scope here:** `/auth/setup` page (consume link) — `coder_1.12_fix` §2.5.

**No backend work** in this task if 1.12 API already merged; otherwise stub UI disabled with tooltip «Скоро».

---

## 5. Backend tasks

**Defer to `coder_1.12_fix.md`** — B11 (invite/setup, `dev_invite_setup.py`), B12 (lifecycle + training mode). This frontend task has no backend changes except consuming APIs from 1.12.

---

## 6. Verification checklist

Manual (supervisor login after `dev_setup.py`):

| Step | Check |
|------|-------|
| Parameters | Scoring rules visible with Russian labels; structural fields readonly when locked |
| Parameters | RUNNING → red «Остановить конкурс» works (after B12) |
| Parameters | PAUSED → «Запустить конкурс» works |
| Teams | Default logo visible; uploaded logo visible after B5 upload |
| Rounds | «Создать тур» visible while contest RUNNING and no DRAFT exists |
| Rounds | Sidebar shows status badge + counts |
| Rounds | «Закрыть тур» after deadline → status CLOSED |
| Results | CLOSED tour → scores editable → save → calculate → publish |
| Results | Match status in Russian |
| Login | Checkbox «Забыли пароль?» → email → success message |

Automated:

```bash
cd frontend && npm run lint && npm run type-check
cd frontend && npm test -- --run deriveAdminUiMode rulesDisplay  # if added
uv run ruff check src/ && uv run mypy src/   # if backend touched
```

---

## 7. Living docs (append only)

After `TEST_PASS`, append to `agent_docs/contracts/frontend_api_integration.md` changelog:

- Asset URL resolution via `resolveAssetUrl`
- Supervisor pause/resume if B12 shipped
- Login password recovery checkbox + `request-password-reset` integration

Do **not** modify `docs/` specs.

---

## 8. File checklist

| Action | Path |
|--------|------|
| NEW | `frontend/src/lib/admin/rulesDisplay.ts` |
| NEW | `frontend/src/lib/api/resolveAssetUrl.ts` |
| NEW | `frontend/src/components/auth/PasswordResetRequest.tsx` (optional) |
| EDIT | `frontend/src/components/auth/LoginForm.tsx` |
| EDIT | `frontend/src/lib/api/endpoints.ts` |
| NEW | `frontend/src/components/admin/ContestLifecycleActions.tsx` |
| NEW | `frontend/src/components/admin/RoundStatusSidebar.tsx` |
| EDIT | `frontend/src/components/admin/ContestParametersForm.tsx` |
| EDIT | `frontend/src/components/admin/RoundManagementPanel.tsx` |
| EDIT | `frontend/src/components/admin/ResultsEntryPanel.tsx` |
| EDIT | `frontend/src/components/admin/MatchResultRow.tsx` |
| EDIT | `frontend/src/components/admin/TeamsGrid.tsx` |
| EDIT | `frontend/src/lib/admin/format.ts` |
| EDIT | `frontend/src/lib/admin/deriveAdminUiMode.ts` |
| EDIT | `frontend/src/app/admin/rounds/page.tsx` |
| EDIT | `frontend/src/app/admin/results/page.tsx` |
| EDIT (backend) | Defer B11/B12 to `coder_1.12_fix.md` |

---

## 9. Screenshot alignment notes

**`supervisor_settings.jpg`:**

- Info banner when locked (blue/amber) — extend `LockBanner` text
- Two-column scoring layout
- Red «Остановить конкурс» bottom-right

**`supervisor_tours.jpg`:**

- Tour selector + match table left; status card right
- Green «Тур активен» badge near match count
- «+ Добавить свободный тур» remains secondary action
- Primary: ability to create next numbered tour

**`supervisor_results.jpg`:**

- Score inputs per match
- Batch actions after all finished
- Status badges in Russian
