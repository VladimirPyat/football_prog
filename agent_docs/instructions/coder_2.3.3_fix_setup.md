# Coder Instructions — Stage 2.3.3 Fix: Contest Setup UX (Supervisor)

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 2.3.2 shipped; manual QA feedback 2026-06-28 (`manuals/SUPERVISOR_TESTING_SCENARIOS.md`).
> **Backend dependency:** `agent_docs/instructions/backend/coder_1.15_fix_setup.md` — **required** for S1.12 (explicit contest start) and S0.6 (supervisor delete on DRAFT). Frontend may stub until backend lands.
> **Follow-up tester:** `agent_docs/instructions/tester_2.3.3_fix_setup.md`
> **Reference screens:** `docs/screens/supervisor_settings.jpg`, `supervisor_settings2.jpg`, `supervisor_settings3.jpg`
> **Language policy:** UI copy Russian; code comments English; API `detail` shown as-is.

---

## 1. Objective

Fix supervisor **contest creation and setup** flow reported during manual QA. Reduce duplication, add missing copy, wire **explicit contest start**, and expose **delete / restore** for supervisor (with admin restore window).

| ID | QA ref | Area | Problem (reported) | Target |
|----|--------|------|-------------------|--------|
| **S0.6** | S0.6* | Delete / restore | Supervisor cannot delete a contest; admin cannot restore within window from UI | Delete action in admin shell; restore visible to ADMIN when snapshot exists |
| **S1.1** | S1.1 | «+ Новый конкурс» modal | Duplicates teams/matches/rounds/round-robin already on Parameters page; slug unexplained | Modal: **name + slug only**; structure on `/admin/settings/parameters` |
| **S1.2** | S1.2 | `/admin/settings/parameters` | Values feel like non-editable stubs; «Произвольное количество» unclear | Editable on DRAFT; round-robin auto-fill; help text (§4) |
| **S1.4** | S1.4 | Locked parameters | Could not verify — contest could not be started | Unblocked by **S1.12** + backend start API |
| **S1.11** | S1.11 | Participants + dev script | No QA scenario for bulk confirm via `dev_invite_setup.py` | Update `manuals/SUPERVISOR_TESTING_SCENARIOS.md` (§8) |
| **S1.12** | S1.12 | Parameters CTA | «Перейти к турам для запуска» — wrong workflow | **«Запустить конкурс»** on Parameters; tours filled later |

\* QA checklist row S0.6 currently describes pause/finished banner — **repurpose** to delete/restore per this table; move pause/finished banner to a new row (e.g. S0.7) in the scenarios doc.

**Non-goals:**

- `/admin` → `/supervisor` rename (`coder_1.13_supervisor_rename.md`)
- Newsletter UI (Stage 3)
- Changing round activation semantics beyond decoupling contest lock (backend §3 in `coder_1.15_fix_setup.md`)

---

## 2. Root-cause summary (verified in code)

### 2.1 Create modal duplicates Parameters page

`CreateContestForm.tsx` collects `total_teams`, `matches_per_round`, `total_rounds`, `is_round_robin` and sends them in `POST /contests`. The same fields exist on `ContestParametersForm.tsx` with save via `PATCH /contests/{id}`.

Backend `create_contest()` already applies defaults from `contest_defaults_path` when optional fields omitted (`contest_setup_service.py`).

### 2.2 Parameters «stub» feel

On **DRAFT + `!is_locked`**, fields are editable (`setupReadonly = false`). E2E `[E2E-ADMIN-SETUP]` confirms PATCH works.

Likely QA pain points:

1. **Wrong contest context** — default picker stays on fixture `id=1` (`RUNNING`, locked) → all fields disabled.
2. **Inverted checkbox** — label «Произвольное количество» binds `checked={!isRoundRobin}`; when unchecked, round-robin validation requires `matches = teams/2`, `rounds = (teams−1)×2`; changing only «Команд» fails save without visible coupling.
3. **No inline help** — user does not see formulas or slug meaning.

### 2.3 No explicit contest start

`ContestLifecycleActions.tsx` for `status === "DRAFT"` renders link **«Перейти к турам для запуска»** → `/admin/rounds`.

Product intent (QA 2026-06-28): supervisor **starts contest from Parameters**; **tours are composed later**. Today `RUNNING` + `is_locked` happen only on **first round activation** (`ensure_running_on_first_activation`, `round_service.transition_round` → `is_locked=True`). **No** `POST /contests/{id}/start` exists → backend work in `coder_1.15_fix_setup.md`.

### 2.4 Supervisor delete (UPDATED — post 1.15 soft-delete)

- `DELETE /contests/{id}`: SUPERVISOR+ without `supervisor_training_mode`; DRAFT instant; PAUSED after grace.
- Soft-delete: `deleted_at` set; contest hidden from `GET /contests`.
- `POST …/restore`: **ADMIN only**; UI on `/admin/lifecycle` (deleted contests list).
- UI: **«Удалить конкурс»** on Parameters (`ContestLifecycleActions.tsx`) for DRAFT (unlocked) and PAUSED — **no** `NEXT_PUBLIC_SUPERVISOR_TRAINING_MODE` gate.

---

## 3. S1.1 — Simplify «Новый конкурс» modal (LOCKED)

### 3.1 Fields

| Keep | Remove from modal |
|------|-------------------|
| **Название** (required) | Команд / Матчей в туре / Туров |
| **Slug** (optional) + help (§3.2) | «Круговая система» checkbox |

### 3.2 Slug help copy (LOCKED)

Under slug input:

```text
Короткое имя для ссылки (латиница, цифры, дефисы). Необязательно — если пусто, в адресе будет только номер конкурса.
```

Label: **«Короткое имя (slug)»** — avoid bare English «Slug» without explanation.

### 3.3 API payload

```ts
await apiPost(contests.create(), { name, slug: slug || undefined });
```

Remove structural fields from `CreateContestFormProps`, `AdminTopNav.handleCreateContest`, and trim `createContestSchema` to name + optional slug only.

### 3.4 Post-create UX

After success (existing flow in `AdminTopNav`):

1. `setContestId(created.id, true)`
2. Toast «Конкурс создан»
3. User lands on Parameters (already on settings tab) — show one-line hint above form:

```text
Задайте число команд, туров и матчей в туре, затем добавьте команды и участников. Запуск конкурса — кнопка внизу страницы.
```

---

## 4. S1.2 — Parameters page: editability + round-robin UX (LOCKED)

### 4.1 Round-robin vs произвольное количество

| `is_round_robin` | Checkbox «Произвольное количество» | Behaviour |
|------------------|-------------------------------------|-----------|
| `true` | **unchecked** | **Круговая (дома/в гости):** `matches_per_round = total_teams / 2`, `total_rounds = (total_teams − 1) × 2` — auto-calculated, fields **read-only** |
| `false` | **checked** | Supervisor sets `matches_per_round` and `total_rounds` freely |

On change of `total_teams` while round-robin mode: recompute derived fields in state before save.

Help block below checkbox (LOCKED):

```text
По умолчанию (галочка снята): круговая система — каждая пара играет дома и в гости.
  • матчей в туре = число команд ÷ 2
  • число туров = (число команд − 1) × 2
Если нужен другой формат (кубок, неполный круг) — включите «Произвольное количество» и задайте значения вручную.
```

### 4.2 Validation UX

Keep `contestParametersSchema` superRefine for round-robin. When save fails, show field errors **and** toast «Проверьте параметры структуры».

### 4.3 DRAFT context guard

If `setupReadonly` and `contest.status === "DRAFT"` is impossible, but when user opens Parameters on locked contest, ensure `LockBanner` is visible (already on settings pages). Optional: subtle note near disabled fields on locked contest: «Выберите другой конкурс в шапке или создайте новый».

### 4.4 Files

- `frontend/src/components/admin/ContestParametersForm.tsx` — auto-sync, help, readonly derived fields in round-robin mode
- `frontend/src/lib/validation/admin.ts` — keep schema; optional extract `deriveRoundRobinStructure(totalTeams)` helper
- Unit test: changing teams 8→10 in round-robin mode updates matches=5, rounds=18

---

## 5. S1.12 — «Запустить конкурс» on Parameters (LOCKED)

Replace DRAFT branch in `ContestLifecycleActions.tsx`:

| Before | After |
|--------|-------|
| Link «Перейти к турам для запуска» | Primary button **«Запустить конкурс»** |

### 5.1 Flow

1. Supervisor on DRAFT, `!is_locked`, Parameters saved (optional: allow start without save if defaults OK — **allow**).
2. Click **«Запустить конкурс»** → `ConfirmDialog`:

```text
Заголовок: Запустить конкурс?
Текст: После запуска нельзя менять число команд, туров, состав участников и правила очков.
      Неподтверждённые приглашения (статус «Ожидает») будут удалены.
      Туры можно создать и активировать позже на вкладке «Туры».
Кнопка: Запустить
```

3. `POST /api/v1/contests/{id}/start` (new — see backend instruction).
4. On success: `refetch()` contest → `is_locked=true`, `status=RUNNING`; toast «Конкурс запущен»; `LockBanner` appears; save button hidden.

### 5.2 Frontend wiring

- Add `contests.start(id)` → `POST /contests/${id}/start` in `endpoints.ts`
- `ContestLifecycleActions` accepts `onStart?: () => Promise<void>` or calls API directly
- `parameters/page.tsx` passes refetch on success

### 5.3 Until backend ready

Gate button with env flag or hide behind feature check; **do not** keep misleading «Перейти к турам» link as final state. If implementing frontend first, show disabled button + title «Требуется обновление API» only in dev — remove before merge.

### 5.4 Activate modal copy (follow-up)

When first **tour** is activated after contest already RUNNING, update activate confirmation in `RoundManagementPanel.tsx` — **remove** «конкурс будет заблокирован» (already locked). Keep «участники смогут делать прогнозы после активации тура».

---

## 6. S0.6 — Supervisor delete + admin restore (LOCKED)

### 6.1 Product rules (QA 2026-06-28)

| Actor | Action |
|-------|--------|
| **SUPERVISOR** | Delete contest (DRAFT instant; PAUSED after grace); contest hidden from lists |
| **ADMIN** | Restore from snapshot on `/admin/lifecycle`; hard purge via ops script |

Backend: `coder_1.15_fix_setup.md` + soft-delete (`deleted_at`). **No** root `.env` flags required — defaults in `config/settings.py`.

### 6.2 UI placement

**Option A (preferred):** secondary button **«Удалить конкурс»** on Parameters page footer (left or below lifecycle CTA), visible when:

- User is SUPERVISOR or ADMIN
- `canDeleteContest(contest)` — DRAFT unlocked or PAUSED; not FINISHED/RUNNING
- Contest not `FINISHED`

Reuse `ConfirmDialog` pattern from `LifecyclePanel` (type `confirm: "DELETE"` in body).

After delete:

- Toast: «Конкурс удалён. Администратор может восстановить…»; refresh contest picker (`contest-list-changed` event)

**Option B:** expose delete on `/admin/lifecycle` for SUPERVISOR without redirect block when training mode — still add Parameters entry for discoverability.

### 6.3 Restore for ADMIN

On `/admin/lifecycle` (and optionally Parameters when `restoreAvailable`):

- Fetch restore eligibility: either `GET /contests/{id}` extended field or try restore preview — **minimal v1:** show «Восстановить» after successful delete in-session (existing `LifecyclePanel` pattern); ADMIN opens lifecycle page.

Improve lifecycle page access: SUPERVISOR may open **read-only** lifecycle view for pause/resume/delete when permitted (not only training mode for pause/resume — already supervisor API).

### 6.4 Files

- `ContestLifecycleActions.tsx` or new `ContestDeleteButton.tsx`
- `LifecyclePanel.tsx` — update delete message for DRAFT instant delete (remove «только после паузы» when backend allows DRAFT)
- `frontend/src/app/admin/lifecycle/page.tsx` — relax redirect if supervisor gains delete on Parameters only

---

## 7. S1.11 — Testing scenarios doc update

Append to `manuals/SUPERVISOR_TESTING_SCENARIOS.md` §1 (Настройка конкурса):

| ID | Сценарий | Маршрут / API | Ожидание | Авто | Статус | Замечания |
|----|----------|---------------|----------|------|--------|-----------|
| S1.11 | Подтверждение участника (dev script) | invite → `dev_invite_setup.py confirm-all` | После скрипта статус «Принято» (`ACCEPTED`) в таблице участников | manual | — | [DEV_SETUP.md](../manuals/DEV_SETUP.md) Workflow B |

Steps for tester (include in scenario «Замечания» or sub-bullet):

1. DRAFT contest, invite 2+ participants → статус «Ожидает»
2. `uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id {id} --password '…'`
3. Reload `/admin/settings/participants` → все «Принято»
4. **Before** S1.12 start: confirm participants survive start; PENDING removed on start (cross-check S1.12 dialog)

Also update §8 UC table: S1.11 references participant accept.

---

## 8. S1.4 — Locked parameters verification

After S1.12 + backend start:

**Manual / E2E path:**

1. Fresh DRAFT → set parameters → **Запустить конкурс**
2. `/admin/settings/parameters` → all structural fields disabled; no «Сохранить параметры»; `LockBanner` visible
3. Matches `admin_setup_locked.spec.ts` behaviour on fixture `id=1`

Add E2E test `[E2E-ADMIN-START]` in `frontend/e2e/admin_setup.spec.ts`:

- Create DRAFT → start via API or UI → assert lock banner + disabled inputs (prefer UI once backend ready)

---

## 9. File checklist

| File | Change |
|------|--------|
| `CreateContestForm.tsx` | Name + slug only; help text |
| `AdminTopNav.tsx` | Slim create payload |
| `lib/validation/admin.ts` | Slim `createContestSchema` |
| `ContestParametersForm.tsx` | Round-robin auto-sync, help, derived readonly |
| `ContestLifecycleActions.tsx` | Start button + delete entry |
| `lib/api/endpoints.ts` | `contests.start` |
| `parameters/page.tsx` | Wire start/delete callbacks |
| `RoundManagementPanel.tsx` | Softer activate modal when already locked |
| `manuals/SUPERVISOR_TESTING_SCENARIOS.md` | S1.11, S0.6 repurpose, S0.7 banner |
| `e2e/admin_setup.spec.ts` | Start + lock test |
| `e2e/fixtures/adminApi.ts` | `startContest()` helper if API added |

---

## 10. Acceptance criteria

- [ ] New contest modal: only name + explained slug; no structure fields
- [ ] Parameters on DRAFT: editable; round-robin auto-fills matches/rounds; help text visible
- [ ] DRAFT Parameters: **«Запустить конкурс»** starts contest without visiting Tours first (with backend)
- [ ] After start: parameters readonly (S1.4 verifiable)
- [ ] Supervisor can delete contest from admin UI; ADMIN can restore within window (with backend + training mode)
- [ ] `manuals/SUPERVISOR_TESTING_SCENARIOS.md` includes S1.11
- [ ] `npm run lint`, `npm run type-check`, `npm run test:unit` pass
- [ ] E2E: existing `[E2E-ADMIN-SETUP]` green; new start/lock test when API ready

---

## 11. Execution order

```text
1. backend/coder_1.15_fix_setup.md  (POST /start, delete policy)  ← blocker for S1.12, S0.6
2. coder_2.3.3_fix_setup.md (this doc) — frontend
3. tester_2.3.3_fix_setup.md
```

Frontend-only items (**S1.1**, **S1.2** copy/sync, **S1.11** doc) may ship before backend; **S1.12** and **S0.6** require backend first.

---

## 12. Contract sync (after impl)

Update via `/docs-git-sync` or manual polish:

- `agent_docs/contracts/contest_lifecycle_flow.md` — DRAFT → RUNNING via `POST /start` (not only round activate)
- `agent_docs/contracts/frontend_api_integration.md` — new endpoint
- `manuals/API_GUIDE.md` — start + delete matrix for supervisor
