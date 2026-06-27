# Coder Instructions — Stage 2.3.1 Fix: Round Statuses, 24h Rule, Pre-Deadline Match Edit

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 2.3 admin UI shipped; `coder_2.1.2_fix_supervisor` applied; manual QA feedback 2026-06-27.
> **Related:** `agent_docs/contracts/contest_lifecycle_flow.md`, `agent_docs/instructions/coder_2.3.md` §3.2–3.4, `agent_docs/instructions/backend/coder_1.2.md` §6.
> **Follow-up tester:** `agent_docs/instructions/tester_2.3.1_fix_rounds.md` (rounds/status/24h/LB UI fix; E2E infra remains `tester_2.3.1_fix.md`).
> **Human glossary:** `manuals/STATUS_REFERENCE.md` — статусы, переходы, API vs UI; `CLOSED` → подпись «Дедлайн».
> **Language policy:** UI copy Russian; code comments English; API `detail` Russian.

---

## 1. Objective

Close supervisor confusion around **round statuses**, fix **misapplied 24h deadline rule**, and restore **match editing before prediction deadline** on ACTIVE tours.

| ID | Area | Problem | Target |
|----|------|---------|--------|
| **F1** | Status glossary | UI shows «Черновик / Активен / Опубликован» without lifecycle context; mixed with contest `DRAFT` | In-app glossary + sidebar hints; doc sync |
| **F2** | 24h rule | Create/change blocked when first match is &lt;24h away — feels like «матчи только через сутки» | **New policy (§3)** — 24h applies to **changing** deadline, not to match kickoff time |
| **F3** | Match edit | After activate, teams/matches frozen even **before** deadline | Full structure edit while `ACTIVE && now < deadline`; restricted after deadline |
| **F4** | Backend parity | `PATCH …/rounds/{id}` allows team swap on ACTIVE even after deadline | Enforce deadline-aware guards server-side |
| **F5** | UX copy | Activate modal: «структура запрещена навсегда» | «До дедлайна можно править матчи; после дедлайна — только статус и дату» |
| **F6** | Per-status UI | `/admin/rounds` treats CLOSED/CALCULATED/PUBLISHED alike | **§9** — distinct panels per round status |
| **F7** | `CALCULATED` clarity | Supervisor thinks CALCULATED = only match scores | §9.3 — preview `scores` + «Опубликовать»; CLOSED = before calculate |
| **F8** | `LockBanner` | Shown on Туры/Результаты when `is_locked` | Banner **only** on `/admin/settings/*` |
| **F9** | Create tour CTA | Hidden when existing tour selected / draft exists | «+ Создать тур» always beside selector; disable at `total_rounds` cap |
| **F10** | `DRAFT` edit | No edit path for saved draft | «Редактировать» → same `RoundBuilderForm`, pre-filled |
| **F11** | `PUBLISHED` | No void/cancel entry on rounds page | «Отменить» → stub modal (future VOID) |
| **F12** | Public leaderboard | `CALCULATED` visible in public API/UI today | **PUBLISHED only** for participants/visitors; stub until publish (§9.9) |

**Related data fixture:** `agent_docs/instructions/coder_1.14_data_fix.md` — dev DB rounds 1–9 `PUBLISHED`, 10 `CALCULATED`, 11 `CLOSED` for manual QA.

**Execution order vs other instructions:** see §15.

**Non-goals:**

- `/admin` → `/supervisor` rename → `coder_1.13_supervisor_rename.md`
- Newsletter send API → Stage 3
- Changing user-side 24h **warning banner** on predict form (`coder_2.2` — «&lt;24h to deadline») — unchanged

---

## 2. Status glossary (LOCKED — explain in UI)

Two **independent** state machines. Do not conflate them.

### 2.1 Contest lifecycle (`contests.status`)

| API | RU label (UI) | Meaning |
|-----|---------------|---------|
| `DRAFT` | Настройка | Contest not started; parameters/teams/participants editable (`!is_locked`) |
| `RUNNING` | Идёт | Operational; predictions + rounds + results (`is_locked`) |
| `PAUSED` | На паузе | All mutations frozen |
| `FINISHED` | Завершён | Terminal read-only |

`is_locked=true` after **first round activation** — not the same as round `DRAFT`.

### 2.2 Round lifecycle (`rounds.status`) — what supervisor sees on `/admin/rounds`

```
DRAFT ──activate──► ACTIVE ──deadline passed + close──► CLOSED
                                                      │
                                            calculate ▼
                                                 CALCULATED
                                                      │
                                              publish ▼
                                                 PUBLISHED
```

| API | RU label | Supervisor meaning |
|-----|----------|-------------------|
| `DRAFT` | **Черновик** | Tour composed, not open for predictions |
| `ACTIVE` | **Активен** | Predictions open until `deadline` |
| `CLOSED` | **Дедлайн** *(UI label; API `CLOSED`)* | Дедлайн прогнозов прошёл; счета матчей вводятся; **очки участников ещё не в `scores`** |
| `CALCULATED` | **Рассчитан** | `POST …/calculate` выполнен — строки в **`scores`**; супервайзер **проверяет** и жмёт «Опубликовать» |
| `PUBLISHED` | **Опубликован** | Тур подтверждён; публичная таблица/матрица (VOID — редкое исключение) |

**Частая путаница (зафиксировать в подсказках UI):**

| Вопрос | Ответ |
|--------|--------|
| «Рассчитан» = вписаны только счета матчей? | **Нет.** Это фаза **`CLOSED`** (и частично ввод на «Результаты»). |
| «Рассчитан» = очки в БД? | **Да** — таблица `scores`, не `matches.score1/2`. |
| «Рассчитан» = очки в БД? | **Да** — таблица `scores`, не `matches.score1/2`. |
| Виден ли лидерборд до «Опубликовать»? | **Нет** для участников и гостей — только `PUBLISHED` (§9.9). Супервайзер видит **превью** на «Туры» при `CALCULATED`. |

**«Опубликован»** = супервайзер подтвердил тур; **только тогда** таблица/результаты доступны публично.
Pair with short hint in `RoundStatusSidebar`:

- `ACTIVE` → «Участники делают прогнозы до дедлайна»
- `CLOSED` → «Дедлайн прошёл. Введите счета матчей и просмотрите прогнозы»
- `CALCULATED` → «Очки посчитаны. Проверьте таблицу и нажмите „Опубликовать“»
- `PUBLISHED` → «Тур зафиксирован в общей таблице»

### 2.3 Where labels live

- `frontend/src/lib/admin/format.ts` — `roundStatusLabel()` — **`CLOSED` → «Дедлайн»** (API unchanged)
- Add `roundStatusHint(status: RoundStatus): string` next to labels; use in `RoundStatusSidebar`
- Optional: `matchPhaseLabel(match, roundStatus)` — for CLOSED rounds show **«Идёт»** when `SCHEDULED` and `date_time <= now` (display only)

---

## 3. 24-hour rule — policy correction (LOCKED)

### 3.1 Current implementation (wrong for product intent)

**Backend** `round_service.set_deadline` + **create round** in `admin_rounds.py` / `contest_ops.py`:

```text
cutoff = earliest_match − deadline_rule_hours
• new_deadline must be < cutoff          (≥24h before first match)
• if now > cutoff → DEADLINE_CHANGE_CLOSED
```

**Effect:** if first match is in 1 hour, **no valid deadline** → cannot create/activate such a tour. Reads as «матчи только через 24 часа».

**Frontend** `deadlineRule.ts` mirrors the same (`isDeadlineValid`).

### 3.2 Intended semantics (user-approved 2026-06-27)

| Rule | Detail |
|------|--------|
| **Match kickoff** | `date_time >= now()` — may be in 1 hour; only not in the past |
| **Deadline placement** (create + any new value) | `now() < deadline < earliest_match` — predictions close before first kickoff |
| **24h rule = edit lockout only** | Supervisor may **change** deadline only while `now() <= deadline − deadline_rule_hours` |
| **Not required** | First match ≥24h in the future |

**Examples** (`deadline_rule_hours = 24`):

| Scenario | Allowed? |
|----------|----------|
| First match in 2h, deadline in 1h | ✅ Create/activate |
| First match in 2h, deadline in 3h (after match) | ❌ `deadline` must be before first match |
| Active tour, deadline in 30h, supervisor moves deadline | ✅ |
| Active tour, deadline in 10h, supervisor moves deadline | ❌ `DEADLINE_CHANGE_CLOSED` |
| Match in 5 days, deadline in 2 days | ✅ |

**Newsletter stub** (unchanged): still show `NewsletterPromptModal` after successful deadline PATCH.

### 3.3 Backend changes

**File:** `src/services/round_service.py`

Replace `set_deadline` validation with:

```python
# Placement (new_deadline)
if new_deadline >= earliest:
    raise ValidationError("Дедлайн должен быть раньше первого матча тура")
if new_deadline <= now:
    raise ValidationError("Дедлайн должен быть в будущем")

# 24h edit lockout (uses CURRENT deadline on round, before assignment)
current_deadline = round_.deadline  # tz-aware
change_cutoff = current_deadline - timedelta(hours=deadline_rule_hours)
if now > change_cutoff:
    raise ContestRuleError("Окно изменения дедлайна закрыто", code="DEADLINE_CHANGE_CLOSED")
```

**Create round** (`admin_rounds.py`, `contest_ops.py`):

- Remove `dl >= cutoff` check against `earliest − Nh`
- Validate: each match `date_time >= now`, `now < deadline < earliest`
- Optional: warn if `deadline > now + timedelta(hours=deadline_rule_hours)` is false — not an error

**Helper** (recommended): `validate_round_deadline_placement(deadline, earliest_match, *, now)` in `round_service.py` — reuse from create + set_deadline.

### 3.4 Frontend changes

**File:** `frontend/src/lib/admin/deadlineRule.ts`

| Function | New behaviour |
|----------|---------------|
| `isDeadlineValid(deadline, earliest, ruleHours)` | `deadline < earliest` only (drop `− ruleHours`) |
| `canChangeDeadline(now, currentDeadline, ruleHours)` | `now <= currentDeadline − ruleHours` |
| `deadlineErrorMessage` | «Дедлайн должен быть раньше первого матча тура» |
| `deadlineChangeClosedMessage` | «Изменить дедлайн можно не позже чем за N ч до текущего дедлайна» |

**`deriveAdminUiMode.ts`:**

```ts
canEditDeadline =
  !disableAllMutations &&
  (roundStatus === "DRAFT" ||
    (isActiveRound && !deadlinePassed && canChangeDeadline(...)));
```

Pass `round.deadline` into mode derivation (already available on `RoundOut`).

**`RoundManagementPanel`:** disable Save + inline error when change window closed (ACTIVE only).

### 3.5 Tests to update

| Suite | Change |
|-------|--------|
| `tests/unit/test_services_1_2.py` | `[DL-24H-*]` — new semantics |
| `tests/integration/test_deadline_batch_1_2.py` | same |
| `tests/api/test_operational_gaps_1_4.py` | `[OP-24H-RULE]` |
| `frontend/src/lib/admin/deadlineRule.test.ts` | placement vs lockout |
| `frontend/e2e/supervisor_24h_rule.spec.ts` | invalid = inside 24h of **current** deadline, not first match −12h |
| `frontend/e2e/supervisor_active_round.spec.ts` | if pre-deadline structure edit added — extend or split spec |

### 3.6 Contract updates (mandatory after impl)

- `agent_docs/contracts/contest_lifecycle_flow.md` — §3 add **3.5 Deadline rules** with table above
- `agent_docs/contracts/api_v1.yaml` — bump patch version; document `DEADLINE_CHANGE_CLOSED` trigger text
- `agent_docs/contracts/frontend_api_integration.md` — supervisor deadline UX bullets
- `manuals/API_GUIDE.md` — `set_deadline` section (via polish handoff or direct if in scope)

---

## 4. Match editing on ACTIVE (F3, F4) — updated 2026-06-27

### 4.1 Intended UI rules (supervisor)

| Round state | Editable on frontend |
|-------------|----------------------|
| `DRAFT` | Full structure: teams, dates, deadline, activate |
| `ACTIVE` | **No team changes.** Reschedule kickoff until match start (ignores prediction deadline). Cancel anytime (confirm). Long league postpone → status `POSTPONED` + free tour. Restore `CANCELED`/`POSTPONED` → `SCHEDULED` **ADMIN only**. |
| `CLOSED`+ | Read-only on rounds page; results on `/admin/results` |

**Rationale:** After activation participants may have predictions; league calendar is not changed via supervisor UI — only schedule exceptions (short reschedule, cancel, free tour).

**Backend:** No change in this pass — PATCH may still accept team swaps before prediction deadline; enforce later (see `agent_docs/reports/todo.md`).

### 4.2 Frontend

**`deriveAdminUiMode.ts`:**

```ts
const canEditRoundStructure = !disableAllMutations && roundStatus === "DRAFT";

const canEditMatchStatusAndDate =
  !disableAllMutations && (roundStatus === "DRAFT" || isActiveRound);
```

**`matchScheduleEdit.ts` + `MatchEditorRow`:** kickoff-based reschedule; cancel/postpone with `ConfirmDialog`; admin restore.

**Save button:** do **not** disable on 24h deadline lockout when only match fields changed — lockout applies to deadline field only.

**`ConfirmDialog` (activate):** «После активации … Состав матчей изменить уже нельзя — только перенос времени до начала, отмена или перенос в свободный тур.»

**Hint (ACTIVE):** «Тур активен. Состав матчей изменить нельзя. До начала матча можно перенести время; отмена — в любой момент. Перенос на другую неделю — через «Перенести (свободный тур)».»

### 4.3 Backend (unchanged)

**`PATCH …/admin/rounds/{round_id}`** — still allows `team1_id`/`team2_id` while `now < deadline` on ACTIVE. Frontend-only restriction until backend hardening.

Add/remove matches on ACTIVE: **optional stretch** — only if `RoundBuilderForm` already POSTs full round; else document as follow-up **F3b** in report.

### 4.4 Unit tests

Extend `deriveAdminUiMode.test.ts`:

- `ACTIVE + !deadlinePassed` → `canEditRoundStructure === true`
- `ACTIVE + deadlinePassed` → `canEditRoundStructure === false`, `canEditMatchStatusAndDate === true`

---

## 9. Per-status UI on `/admin/rounds` (F6–F11) — LOCKED

Reference: `docs/screens/supervisor_tours.jpg`, `manuals/STATUS_REFERENCE.md`.

**Principle:** selecting a tour in the dropdown switches **mode** of the main panel + sidebar. Do **not** reuse the same match grid for `CLOSED` / `CALCULATED` / `PUBLISHED`.

Implement `RoundPhasePanel` (or branch inside `RoundManagementPanel`) driven by `selectedRound.status`.

### 9.1 Shared chrome (all statuses)

| Element | Rule |
|---------|------|
| Tour `<select>` | Unchanged; label uses `roundStatusLabel()` |
| **«+ Создать тур»** | Always visible **next to** `<select>` (same row). See §10 |
| **«+ Добавить свободный тур»** | Keep as secondary link when no `DRAFT` |
| `LockBanner` | **Not** on this page — §10 |

### 9.2 `DRAFT` — Черновик (F10)

| UI | Behaviour |
|----|-----------|
| Primary CTA | **«Редактировать»** (replaces inline full editor as default view) |
| On click | Open **`RoundBuilderForm`** in edit mode: same fields as create, **pre-filled** from `matches` + `deadline` + `number` |
| Save | `PATCH …/rounds/{id}` (extend client payload for structure if needed) or delete+recreate only if PATCH insufficient — prefer PATCH |
| Secondary | **«Активировать»** (existing confirm §4.2) |
| Hide | Read-only match table until «Редактировать» or show collapsed summary |

**Non-goal:** duplicate a second form component — reuse `RoundBuilderForm` with `initialValues` prop.

### 9.3 `ACTIVE` — Активен

Keep current editor (§4) + deadline + save. Sidebar hints per §2.2.

### 9.4 `CLOSED` — Дедлайн (F6, F7)

**Meaning in UI:** prediction deadline passed; **participant points not calculated yet** (`scores` empty).

| Area | Content |
|------|---------|
| Sidebar badge | **Дедлайн** |
| Hint | «Дедлайн прогнозов прошёл. Введите счета матчей и при необходимости просмотрите прогнозы участников.» |
| Match list | Read-only: teams, date, display status |
| Match display status | `FINISHED` → «Завершён»; `SCHEDULED` + kickoff ≤ now → **«Идёт»**; `SCHEDULED` + future → «Запланирован» |
| Actions (two buttons) | |

```tsx
// Stub until dedicated routes exist — same modal pattern as NewsletterPromptModal
<Button onClick={() => setStub('predictions')}>Просмотр прогнозов участников</Button>
<Button onClick={() => setStub('results')}>Ввод результатов матчей</Button>
```

| Button | Phase 1 behaviour | Phase 2 (link when ready) |
|--------|-------------------|---------------------------|
| Просмотр прогнозов | Modal: «Будет реализовано в следующих версиях» | `/admin/…` or modal with `GET …/predictions` post-deadline |
| Ввод результатов | Modal stub **or** `Link` to `/admin/results?round={id}` if results page already handles `CLOSED` |

**Do not** show PUBLISHED-style «Применено» or CALCULATED preview here.

### 9.5 `CALCULATED` — Рассчитан (F7)

**Meaning in UI:** `scores` rows exist; supervisor **reviews** before publish.

| Area | Content |
|------|---------|
| Hint | «Очки участников посчитаны. Проверьте промежуточную таблицу. После проверки нажмите „Опубликовать“.» |
| Preview table | **Admin-only** preview (§9.9): `GET …/leaderboard` as SUPERVISOR **or** dedicated preview hook — **not** shown on public contest pages |
| Mark as preview | Small badge **«Предпросмотр — тур ещё не опубликован»** |
| Primary CTA | **«Опубликовать»** → `POST …/publish` + refetch |
| Secondary | Link «Открыть на вкладке Результаты» → `/admin/results?round={id}` |

**Not** the same layout as `CLOSED` (no «Идёт», no «ввод счетов» as primary).

### 9.6 `PUBLISHED` — Опубликован (F11)

| Area | Content |
|------|---------|
| Hint | «Тур опубликован в общей таблице.» |
| Match list | Read-only, same as today |
| **«Отменить»** | Opens modal: «Отмена сыгранных матчей будет реализована в будущих версиях.» Single button **«Закрыть»**. No API call. |
| Badge | Keep **«Применено»** (green) in sidebar / header |

**Note:** VOID on results page remains for rare ops; this button is intentional **stub** for product parity with mockups.

### 9.7 Stub modal (reuse)

```tsx
<ConfirmDialog
  open={stubOpen}
  title="Скоро"
  message="Будет реализовано в будущих версиях."
  confirmLabel="Закрыть"
  onConfirm={() => setStubOpen(false)}
  onCancel={() => setStubOpen(false)}
/>
```

Use for: PUBLISHED «Отменить», CLOSED buttons until wired.

### 9.8 `ResultsEntryPanel` alignment

| Round status | Results page |
|--------------|--------------|
| `CLOSED` | Score entry + «Рассчитать» (existing) |
| `CALCULATED` | Read-only scores + «Опубликовать» |
| `PUBLISHED` | Read-only + VOID (existing) |

Ensure copy distinguishes **ввод счетов матчей** (CLOSED) vs **проверка очков** (CALCULATED). Optional query `?round=` from rounds page.

### 9.9 Public leaderboard & results visibility (F12) — LOCKED

**Product rule:** until supervisor publishes the round, **participants and visitors must not see** that round in the public leaderboard or results matrix.

| Audience | Round status | Leaderboard / results matrix |
|----------|--------------|------------------------------|
| Visitor, USER | `PUBLISHED` | ✅ Show data (API + UI) |
| Visitor, USER | `CALCULATED`, `CLOSED`, `ACTIVE`, `DRAFT` | ❌ Stub only — **do not render standings** |
| SUPERVISOR / ADMIN on `/admin/rounds` | `CALCULATED` | ✅ **Preview table** for verification (§9.5) |
| SUPERVISOR on `/admin/results` | `CALCULATED` | Existing workflow + «Опубликовать» |

**Public UI copy (LOCKED):**

```text
Будет доступно после проверки организатором
```

Use on: contest leaderboard tab, per-round leaderboard, results matrix, round selector when status ≠ `PUBLISHED`. Optional secondary line: «Организатор ещё не опубликовал результаты тура».

#### 9.9.1 Frontend implementation

1. **Helper** `frontend/src/lib/contest/roundPublicVisibility.ts`:

```ts
export function isRoundPubliclyVisible(status: RoundStatus): boolean {
  return status === "PUBLISHED";
}
```

2. **Before fetch:** if `!isRoundPubliclyVisible(round.status)` → render stub; **skip** `GET …/leaderboard` and `GET …/results` for that round.

3. **Round selector** (public contest pages, Stage 2.4+): list only `PUBLISHED` rounds, or show non-published with disabled + tooltip.

4. **Global leaderboard:** aggregate **only** tours with `status === 'PUBLISHED'` (filter client-side from `GET …/rounds` + leaderboard response, or rely on backend §9.9.2).

5. **Link «Проверить публичные результаты»** on admin results (`ResultsEntryPanel`): enable only when `selectedRound.status === 'PUBLISHED'`; if `CALCULATED` → disabled + tooltip «Сначала опубликуйте тур».

6. **Components** (create or extend when 2.4 lands): `LeaderboardPanel`, `ResultsMatrix`, `PredictionsMatrix` post-deadline — all gate on `isRoundPubliclyVisible`.

#### 9.9.2 Backend alignment (same fix — do not rely on UI alone)

Current code (`leaderboard_service.py`) allows `CALCULATED` on public GET — **change**:

| Function | New rule |
|----------|----------|
| `get_round_leaderboard` | Default (no auth / USER): **`PUBLISHED` only** → else `403` `RESULTS_NOT_AVAILABLE` |
| `get_round_leaderboard` | SUPERVISOR/ADMIN of contest: allow **`CALCULATED`** (supervisor preview) |
| `get_global_leaderboard` | Sum **`scores` only for rounds `PUBLISHED`** |
| `get_round_results` | Same split as round leaderboard |

Pass `viewer_role` (from JWT deps) into service layer or check in router before call.

**Tests to update:**

- `tests/api/test_calculate_leaderboard_1_4.py` — public GET round LB before publish → 403; after publish → 200
- `tests/api/test_leaderboard_counts.py` — publish before public round LB
- Integration tests that assumed CALCULATED visible publicly

**Contracts (mandatory):** `api_v1.yaml`, `contest_lifecycle_flow.md` §3.3 — «public GET leaderboard/results: `PUBLISHED` only».

---

## 10. Lock banner scope & create-tour button (F8, F9)

### 10.1 `LockBanner` only on Settings

**Problem:** `AdminPageShell` always renders `LockBanner` when `is_locked` — including `/admin/rounds` and `/admin/results`.

**Fix:**

```tsx
// AdminPageShell.tsx
interface AdminPageShellProps {
  showSettingsNav?: boolean;
  showSetupLockBanner?: boolean; // NEW — default false
}
// Render LockBanner only when showSetupLockBanner === true
```

| Route | `showSetupLockBanner` |
|-------|------------------------|
| `/admin/settings/*` | `true` |
| `/admin/rounds`, `/admin/results`, `/admin/newsletters`, lifecycle | `false` |

`deriveAdminUiMode`: split `showLockBanner` → `showSetupLockBanner` (settings only) vs operational pages.

### 10.2 «+ Создать тур» always visible

**Problem:** `RoundManagementPanel` hides «Создать тур» section when `hasDraft` or when user only selects an existing tour; user sees only lock banner text.

**Fix:**

1. Move **«+ Создать тур»** to the **selector row** (beside `<select>`).
2. On click: scroll/focus `RoundBuilderForm` below **or** open drawer/modal with `RoundBuilderForm` — same component as today.
3. **Disable** (with `title` tooltip) when:

```ts
const atRoundCap = rounds.length >= contest.total_rounds;
const hasDraft = rounds.some((r) => r.status === "DRAFT");
const createDisabled = uiMode.disableAllMutations || atRoundCap || hasDraft;
```

| Condition | Tooltip |
|-----------|---------|
| `atRoundCap` | «Достигнут лимит туров ({total_rounds}) из настроек конкурса» |
| `hasDraft` | «Сначала активируйте или удалите черновик тура» |
| `PAUSED` / `FINISHED` | existing pause banner |

4. **Remove** dependency on `!hasDraft` for **showing** the button — only for **disabling**.
5. `canCreateRound` in `deriveAdminUiMode.ts`: change from `!hasDraftRound` hide logic to `!atRoundCap && !hasDraftRound` for **enabled** state only.

### 10.3 Files

```
frontend/src/components/admin/AdminPageShell.tsx
frontend/src/app/admin/settings/**/page.tsx          # showSetupLockBanner
frontend/src/app/admin/rounds/page.tsx             # false
frontend/src/app/admin/results/page.tsx              # false
frontend/src/lib/admin/deriveAdminUiMode.ts
frontend/src/components/admin/RoundManagementPanel.tsx
frontend/src/components/admin/RoundPhasePanel.tsx    # NEW (optional split)
frontend/src/components/admin/RoundLeaderboardPreview.tsx  # NEW §9.5
frontend/src/components/admin/RoundBuilderForm.tsx   # initialValues §9.2
```

---

## 11. Scope — files to touch

```
src/services/round_service.py              # F2 deadline helpers + set_deadline
src/services/leaderboard_service.py        # §9.9.2 PUBLISHED-only public
src/api/v1/admin_rounds.py                 # F2 create + F4 patch guards
src/api/v1/contest_ops.py                  # F2 create + F4 patch guards + LB role
frontend/src/lib/admin/deadlineRule.ts     # F2
frontend/src/lib/admin/deadlineRule.test.ts
frontend/src/lib/admin/deriveAdminUiMode.ts # F2 + F3
frontend/src/lib/admin/deriveAdminUiMode.test.ts
frontend/src/lib/admin/format.ts           # F1 hints
frontend/src/lib/contest/roundPublicVisibility.ts  # §9.9.1
frontend/src/components/admin/RoundStatusSidebar.tsx  # F1 hints
frontend/src/components/admin/RoundManagementPanel.tsx # F3 hints + confirm + §9–10
frontend/src/components/admin/RoundPhasePanel.tsx    # §9 (or inline branches)
frontend/src/components/admin/RoundLeaderboardPreview.tsx
frontend/src/components/admin/RoundBuilderForm.tsx   # initialValues
frontend/src/components/admin/AdminPageShell.tsx    # §10.1
frontend/src/app/admin/settings/**/page.tsx
frontend/src/app/admin/rounds/page.tsx
frontend/src/app/admin/results/page.tsx
tests/unit/test_services_1_2.py
tests/integration/test_deadline_batch_1_2.py
tests/api/test_operational_gaps_1_4.py
frontend/e2e/supervisor_24h_rule.spec.ts
frontend/e2e/supervisor_active_round.spec.ts   # update if behaviour changes
agent_docs/contracts/contest_lifecycle_flow.md
agent_docs/contracts/api_v1.yaml
agent_docs/contracts/frontend_api_integration.md
agent_docs/reports/BLOCKED.md              # only if new blocker found
```

---

## 12. Execution order

```bash
# 1. Backend + unit/integration tests
uv run pytest tests/unit/test_services_1_2.py tests/integration/test_deadline_batch_1_2.py -v
uv run pytest tests/api/test_operational_gaps_1_4.py -v -k 24h

# 2. Frontend unit
cd frontend && npm run test:unit

# 3. Lint
cd frontend && npm run lint && npm run type-check && npm run format:check
uv run ruff check src/
uv run mypy src/

# 4. Targeted E2E (backend up)
cd frontend && npx playwright test supervisor_24h_rule.spec.ts supervisor_active_round.spec.ts
uv run python src/scripts/dev_setup.py --check-ports   # tester_2.1 §2.5
```

---

## 13. Acceptance criteria

- [ ] Supervisor sees hint per round status (§2.2); no confusion between contest `DRAFT` and round `DRAFT`
- [ ] **CLOSED** labelled **«Дедлайн»**; panel ≠ PUBLISHED (§9.4)
- [ ] **Public** pages: non-`PUBLISHED` rounds show «Будет доступно после проверки организатором»; no LB fetch (§9.9)
- [ ] **Backend** public GET LB/results: `PUBLISHED` only; SUPERVISOR+ may preview `CALCULATED` (§9.9.2)
- [ ] **DRAFT** «Редактировать» opens pre-filled `RoundBuilderForm` (§9.2)
- [ ] **PUBLISHED** «Отменить» → stub modal (§9.6)
- [ ] `LockBanner` only on settings; **«+ Создать тур»** always beside selector (§10)
- [ ] Create disabled at `total_rounds` cap with tooltip (§10.2)
- [ ] Can create tour with first match in ~2h and deadline before kickoff
- [ ] Cannot PATCH deadline when &lt;24h before **current** deadline (`DEADLINE_CHANGE_CLOSED`)
- [ ] ACTIVE tour before prediction deadline: team picks enabled in UI; API allows team PATCH
- [ ] ACTIVE tour after prediction deadline: team picks disabled; API rejects team PATCH
- [ ] Contracts + api_v1.yaml reflect new deadline semantics
- [ ] Existing Stage 2.3 unit tests updated; no regression on close → calculate → publish pipeline

---

## 14. Handoff

On `READY_FOR_TEST`:

1. Append progress entry to `agent_docs/progress/stage_2.md`
2. Summarize policy change in report for @Tester (old E2E assumptions invalid)
3. If add/remove match on ACTIVE deferred → note **F3b** in `BLOCKED.md` or report, not silent skip

**Verdict tags for tester report:**

| ID | Description |
|----|-------------|
| `[UNIT-DEADLINE-PLACEMENT]` | deadline &lt; first match, match ≥ now |
| `[UNIT-DEADLINE-LOCKOUT]` | change blocked &lt;24h before current deadline |
| `[UNIT-UI-MODE-PRE-DEADLINE]` | ACTIVE structure edit before deadline |
| `[E2E-SUPERVISOR-24H]` | updated lockout scenario |
| `[E2E-SUPERVISOR-ACTIVE-ROUND]` | pre-deadline edit path |
| `[UI-ROUND-CLOSED]` | Дедлайн panel + stub buttons |
| `[UI-ROUND-CALCULATED]` | admin preview table + publish (not on public pages) |
| `[UI-PUBLIC-LB-GATE]` | stub until PUBLISHED |
| `[API-LB-PUBLISHED-ONLY]` | public GET rejects CALCULATED |
| `[UI-CREATE-TOUR-CTA]` | button visible; cap tooltip |
| `[UI-LOCK-BANNER-SCOPE]` | absent on rounds/results |

---

## 15. Pending instructions — how 1.14 and 2.3.1 relate

| Instruction | Scope | Status |
|-------------|-------|--------|
| **`coder_1.14_data_fix.md`** | **Data / bootstrap only:** rounds 1–9 `PUBLISHED` + `scores`, 10 `CALCULATED`, 11 `CLOSED` in dev DB | **implemented** — `finalize_dev_fixture.py`; round **11** for CLOSED results-entry demo |
| **`coder_2.3.1_fix.md`** | **Product + UI + API:** 24h rule, per-status admin panels, create-tour CTA, **public LB gate** (§9.9), `LockBanner` scope | `INSTRUCTIONS_READY` — **not implemented** |

**Recommended order:**

1. **`coder_1.14`** first — so manual QA has realistic statuses in DB (especially round 10 `CALCULATED`, 11 `CLOSED`).
2. **`coder_2.3.1`** second — UI/backend behaviour; can start in parallel on branches, but E2E/manual checks need 1.14 data for full matrix.

**Not in this queue:** `coder_1.13_supervisor_rename.md` (`/admin` → `/supervisor`) — separate sub-stage.

**Overlap:** both reference `manuals/STATUS_REFERENCE.md`; 2.3.1 owns visibility policy (§9.9), 1.14 owns fixture script only.
