# Tester Instructions — Stage 2.3.3 Fix: Contest Setup UX (Supervisor)

> **Status gate:** @Coder `READY_FOR_TEST` for 2.3.3 setup fix (+ backend 1.15 if S1.12/S0.6 in scope).
> **Coder spec:** `agent_docs/instructions/coder_2.3.3_fix_setup.md`
> **Backend spec:** `agent_docs/instructions/backend/coder_1.15_fix_setup.md` (required for **T5–T8**, **T12–T14**)
> **Prerequisite:** Stage **2.3.2** at `TEST_PASS` (`tester_2.3.2_fix_tours.md`); existing `[E2E-ADMIN-SETUP]` / `[E2E-ADMIN-LOCK]` green.
> **Report:** `agent_docs/reports/test_2.3.3_fix_setup.md` (NEW — Russian summary + PASS/FAIL table)
> **Manual checklist:** `manuals/SUPERVISOR_TESTING_SCENARIOS.md` — rows S0.6, S1.1, S1.2, S1.4, S1.11, S1.12
> **Strategy:** Vitest unit + backend pytest (1.15) + Playwright E2E + manual setup walkthrough. **Do not modify** `src/` unless new blocker → `BLOCKED.md`.

---

## 1. Objective

Verify Stage **2.3.3** fixes supervisor **contest creation, parameters, start, delete/restore** flow from manual QA 2026-06-28.

| ID | Coder | QA ref | Area | Summary |
|----|-------|--------|------|---------|
| **T1** | §3 | S1.1 | Create modal | Name + explained slug only; no teams/tours/round-robin |
| **T2** | §3.4 | S1.1 | Post-create hint | Hint above Parameters form after create |
| **T3** | §4 | S1.2 | Parameters edit | Editable on fresh DRAFT; save persists |
| **T4** | §4 | S1.2 | Round-robin UX | Auto `matches = N/2`, `rounds = (N−1)×2`; help text |
| **T5** | §5 | S1.12 | Start CTA | «Запустить конкурс» on Parameters (not link to Tours) |
| **T6** | §5.1 | S1.12 | Start confirm | Dialog warns lock + PENDING purge + tours later |
| **T7** | §8 | S1.4 | Locked after start | LockBanner; fields readonly; no save button |
| **T8** | §5.4 | S1.12 | Activate copy | Activate modal does not say «конкурс будет заблокирован» if already locked |
| **T9** | §6 | S0.6 | Supervisor delete | Delete from Parameters (DRAFT / PAUSED); без training mode |
| **T10** | §6 | S0.6 | Admin restore | ADMIN restore on `/admin/lifecycle` within snapshot window |
| **T11** | §7 | S1.11 | Dev confirm script | `dev_invite_setup.py confirm-all` → «Принято» in UI |
| **T12** | 1.15 §2 | S1.12 | API start | `POST /contests/{id}/start` |
| **T13** | 1.15 §4 | S0.6 | API delete DRAFT | DELETE on DRAFT as SUPERVISOR (без training mode) |
| **T14** | 1.15 §2 | S1.12 | Purge on start | PENDING removed; ACCEPTED kept |

**Non-goals:**

- Full 2.3.2 / 2.3.1 regression re-run (spot-check only unless failures)
- `/admin` → `/supervisor` rename → **1.13**
- Newsletter UI → Stage 3
- Screenshot pixel diff vs `docs/screens/supervisor_settings*.jpg`

---

## 2. Test environment

### 2.0 E2E prerequisites (READ FIRST)

Playwright поднимает UI (`:3000`). **API `:8000` — вручную** или через `dev_setup --run-only`.

```bash
# Terminal 1 — API
cd /work/football_prog
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2 — тесты
cd frontend
npm run test:e2e -- e2e/admin_setup.spec.ts e2e/admin_setup_locked.spec.ts --reporter=line
```

**Или:**

```bash
uv run python src/scripts/dev_setup.py --run-only
cd frontend && npm run test:e2e
```

**Корневой `.env` (секреты):**

```bash
SEED_SUPERVISOR_PASSWORD=…
SEED_ADMIN_PASSWORD=…
```

Дополнительные флаги (`SUPERVISOR_TRAINING_MODE`, `CONTEST_*`) **не** кладут в `.env` — дефолты в `config/settings.py`. Для pytest — `monkeypatch` в фикстурах; для ручного API — shell prefix (см. `manuals/CONFIG.md`).

**Frontend env** (`frontend/.env.local`):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
E2E_SUPERVISOR_PASSWORD=<matches SEED_SUPERVISOR_PASSWORD>
E2E_ADMIN_PASSWORD=<matches SEED_ADMIN_PASSWORD>
```

| Симптом | Причина | Решение |
|---------|---------|---------|
| Поля Parameters disabled на новом конкурсе | Выбран `id=1` (RUNNING) | Переключить contest picker или создать новый |
| DELETE 403 для supervisor | Конкурс RUNNING (не PAUSED) или FINISHED | Сначала пауза; для DRAFT — должен быть 200 |
| Restore 403 для supervisor | Restore только ADMIN | Войти как admin → `/admin/lifecycle` |
| Start button 404 | Backend 1.15 не вмержен | Сначала `coder_1.15_fix_setup.md` |
| `SEED_SUPERVISOR_PASSWORD missing` | Пустой `.env` | `.env.example` |

**После E2E:** остановить uvicorn (`Ctrl+C` или `pkill -f "uvicorn main:app"`).

### 2.1 Profiles

| Profile | Use for |
|---------|---------|
| **Fresh DRAFT** | T1–T7, T9, T11–T14 — `createDraftContest` in `adminApi.ts` |
| **Loaded `id=1` RUNNING** | T7 regression vs `[E2E-ADMIN-LOCK]`; T8 after start on fresh contest |
| **Soft delete** | T9–T10 — deleted contest hidden from picker; ADMIN restore list |

Fresh DRAFT — **не** мутировать contest `id=1` для setup-тестов.

### 2.2 Credentials

| Role | Login | Password |
|------|-------|----------|
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` |

---

## 3. Scope — files you may create/modify

```
frontend/src/lib/validation/admin.test.ts              # NEW/extend — round-robin derive (T4)
frontend/e2e/admin_setup.spec.ts                       # UPDATE — T1–T7, [E2E-ADMIN-START]
frontend/e2e/admin_setup_locked.spec.ts                # regression T7 vs id=1
frontend/e2e/admin_contest_start.spec.ts               # NEW optional — T5–T7 UI start
frontend/e2e/admin_contest_delete_restore.spec.ts      # NEW optional — T9–T10
frontend/e2e/fixtures/adminApi.ts                      # startContest(), deleteContest helpers
tests/api/test_contest_start_1_15.py                   # if Coder added — run only; else write blocker
agent_docs/reports/test_2.3.3_fix_setup.md             # NEW
manuals/SUPERVISOR_TESTING_SCENARIOS.md                # verify S1.11 row exists (Coder §7)
```

**Do NOT modify:** `docs/`, `src/` (bugs → `agent_docs/reports/BLOCKED.md`).

---

## 4. Unit tests (Vitest) — mandatory

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

### 4.1 `[UNIT-CREATE-SCHEMA]` — `createContestSchema` (T1)

| Case | Assert |
|------|--------|
| `{ name: "Test" }` | Valid |
| `{ name: "", slug: "x" }` | Error on name |
| `{ name: "X", total_teams: 8 }` | **Invalid** — extra fields stripped or schema rejects unknown (Coder choice) |
| No structural fields required | Valid with name only |

### 4.2 `[UNIT-ROUND-ROBIN-DERIVE]` — helper / `ContestParametersForm` logic (T4)

| `total_teams` | Expected `matches_per_round` | Expected `total_rounds` |
|---------------|------------------------------|-------------------------|
| 8 | 4 | 14 |
| 10 | 5 | 18 |
| 16 | 8 | 30 |

When «Произвольное количество» checked (`is_round_robin=false`): changing teams does **not** overwrite manual matches/rounds.

### 4.3 `[UNIT-PARAMS-SCHEMA]` — `contestParametersSchema` (T3, T4)

| Case | Assert |
|------|--------|
| Round-robin: teams=8, matches=4, rounds=14 | Valid |
| Round-robin: teams=8, matches=3 | Error «Должно быть = команды / 2» |
| Arbitrary: teams=8, matches=3, rounds=5 | Valid |

### 4.4 Regression

Existing `deriveAdminUiMode.test.ts`: `setupReadonly === true` when `is_locked`; `false` on DRAFT unlocked.

---

## 5. Backend pytest — mandatory when 1.15 merged

```bash
cd /work/football_prog
uv run pytest tests/api/test_contest_start_1_15.py -v
uv run pytest tests/api/test_contest_restore.py -v -k "draft or DRAFT or restore"
```

If files missing → **BLOCKER** for T12–T14; mark `TEST_FAIL` with note «backend 1.15 not shipped».

### 5.1 `[API-START-DRAFT]` — T12

| Step | Expected |
|------|----------|
| Create DRAFT contest via API | 201/200 |
| `POST /contests/{id}/start` as SUPERVISOR | 200, `status=RUNNING`, `is_locked=true` |
| `PATCH /contests/{id}` `{ total_teams: 10 }` | 403 CONTEST_LOCKED |
| Second `POST …/start` | 200 idempotent |

### 5.2 `[API-START-PURGE]` — T14

| Step | Expected |
|------|----------|
| Invite participant A → PENDING | status PENDING |
| Confirm participant B → ACCEPTED | status ACCEPTED |
| `POST …/start` | 200 |
| List participants | A gone; B ACCEPTED |

Use `dev_invite_setup.py confirm-all` or `complete-setup` for B.

### 5.3 `[API-DELETE-DRAFT]` — T13

| Step | Expected |
|------|----------|
| DRAFT + teams (defaults, training mode off) | — |
| `DELETE /contests/{id}` `{ confirm: "DELETE" }` as SUPERVISOR | 200, `status: "DELETED"` |
| `GET /contests` | id absent from list |
| Snapshot row exists | ADMIN restore possible |

### 5.4 `[API-RESTORE-WINDOW]` — T10

| Step | Expected |
|------|----------|
| After delete with snapshot | — |
| `POST /contests/{id}/restore` as ADMIN | 200, teams back |
| Second restore | 404/410 |

---

## 6. E2E tests (Playwright) — mandatory

**API `:8000` running.** Prefer UI path for T5–T7 once backend ready.

### 6.1 `[E2E-CREATE-MODAL]` — T1, T2

**Setup:** supervisor session, any admin page.

| Step | Expected |
|------|----------|
| Click «+ Новый конкурс» | Modal opens |
| Assert **no** inputs «Команд», «Матчей/тур», «Туров», «Круговая система» | Absent |
| Label slug explained (not bare «Slug») | «Короткое имя (slug)» + help text |
| Submit name only | Toast «Конкурс создан»; picker switches to new id |
| On Parameters | Hint about structure + start button at bottom (T2) |

### 6.2 `[E2E-ADMIN-SETUP]` — T3 regression

Extend / keep existing spec in `admin_setup.spec.ts`:

| Step | Expected |
|------|----------|
| Fresh DRAFT, Parameters | No LockBanner |
| Change «Команд» → 6, save | Toast «Параметры сохранены»; reload persists |

### 6.3 `[E2E-PARAMS-ROUND-ROBIN]` — T4

**Setup:** fresh DRAFT, round-robin mode (checkbox **unchecked**).

| Step | Expected |
|------|----------|
| Set «Команд» = 10 | «Матчей в туре» = 5, «Туров» = 18 (readonly or auto) |
| Help block visible | Formulas for ÷2 and (N−1)×2 |
| Enable «Произвольное количество» | Matches/rounds editable independently |
| Save arbitrary values | 200 + toast |

### 6.4 `[E2E-ADMIN-START]` — T5, T6, T7

**Setup:** fresh DRAFT; optional: invite one PENDING + one ACCEPTED for purge check.

| Step | Expected |
|------|----------|
| Parameters bottom | Button «Запустить конкурс» (**not** «Перейти к турам для запуска») |
| Click → confirm dialog | Text mentions lock, PENDING purge, tours later |
| Confirm | Toast «Конкурс запущен» |
| LockBanner visible | «Редактирование параметров недоступно» |
| Save button | Hidden |
| Inputs | disabled |
| `/admin/settings/teams` | Add team disabled / hidden |
| `/admin/rounds` | Can still «+ Создать тур» (contest RUNNING, not locked for rounds) |

### 6.5 `[E2E-ADMIN-LOCK]` — T7 regression

Keep `admin_setup_locked.spec.ts` on contest `id=1` — behaviour must match post-start fresh contest.

### 6.6 `[E2E-ACTIVATE-COPY]` — T8

**Setup:** contest already started (T7), create DRAFT round, activate.

| Step | Expected |
|------|----------|
| Activate confirm modal | **No** phrase «конкурс будет заблокирован» / «структура запрещена навсегда» |
| Still warns about predictions opening | Present |

### 6.7 `[E2E-DELETE-RESTORE]` — T9, T10

**Setup:** fresh DRAFT with 1 team (defaults; no extra env flags).

| Step | Expected |
|------|----------|
| Supervisor: «Удалить конкурс» on Parameters | Confirm → success toast; contest leaves picker |
| Contest soft-deleted | not in supervisor list |
| Login ADMIN → `/admin/lifecycle` | deleted contest in list; «Восстановить» |
| Restore | Teams back; contest visible in picker |

---

## 7. Manual checklist — `SUPERVISOR_TESTING_SCENARIOS.md`

Run **Route A (partial)** — setup phase only (~15 min):

| ID | Steps | Pass criteria |
|----|-------|---------------|
| **S1.1** | «+ Новый конкурс» → only name/slug | ✅ |
| **S1.2** | Parameters: edit, round-robin help, save | ✅ |
| **S1.11** | Invite 2 users → `confirm-all` → reload participants | All «Принято» |
| **S1.12** | «Запустить конкурс» without creating tour | RUNNING + lock |
| **S1.4** | After S1.12: parameters readonly | Matches `supervisor_settings*.jpg` |
| **S0.6** | Supervisor delete test contest; admin restore | ✅ within 24h |

Update **Статус** column in scenarios doc with date + `test_2.3.3_fix_setup.md` link.

### 7.1 S1.11 manual steps (LOCKED)

```bash
# 1. UI: invite 2 participants on DRAFT contest → «Ожидает»
# 2. Bulk confirm:
uv run python src/scripts/dev_invite_setup.py confirm-all \
  --contest-id <ID> \
  --password 'DevPass123!'

# 3. Reload /admin/settings/participants → «Принято»
# 4. Optional: invite third as PENDING, run S1.12 start → third gone, first two ACCEPTED remain
```

---

## 8. Lint & build

```bash
cd frontend && npm run lint && npm run type-check && npm run format:check
cd frontend && npm run build
```

Backend (if 1.15 touched):

```bash
uv run ruff check src/
uv run mypy src/
uv run bandit -r src/ -ll
uv run pytest tests/test_linting.py -q
```

---

## 9. Documentation verification

| ID | File | Check |
|----|------|-------|
| `[DOC-SCENARIOS]` | `manuals/SUPERVISOR_TESTING_SCENARIOS.md` | S1.11 row; S0.6 = delete/restore; S0.7 = pause banner (if Coder split) |
| `[DOC-API]` | `manuals/API_GUIDE.md` | `POST …/start` documented (after 1.15) |
| `[DOC-LIFECYCLE]` | `agent_docs/contracts/contest_lifecycle_flow.md` | Start transition |

---

## 10. Report template

Create `agent_docs/reports/test_2.3.3_fix_setup.md`:

```markdown
# Test Report — Stage 2.3.3 Fix Setup

**Date:** YYYY-MM-DD
**Coder:** coder_2.3.3_fix_setup.md (+ coder_1.15_fix_setup.md)
**Tester instruction:** tester_2.3.3_fix_setup.md
**Environment:** API :8000, UI :3000; root `.env` secrets only (see §2.0)

## Summary
(2–4 предложения на русском)

## Results

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-CREATE-SCHEMA]` | PASS/FAIL | |
| `[UNIT-ROUND-ROBIN-DERIVE]` | PASS/FAIL | |
| `[UNIT-PARAMS-SCHEMA]` | PASS/FAIL | |
| `[API-START-DRAFT]` | PASS/FAIL/SKIP | |
| `[API-START-PURGE]` | PASS/FAIL/SKIP | |
| `[API-DELETE-DRAFT]` | PASS/FAIL/SKIP | |
| `[API-RESTORE-WINDOW]` | PASS/FAIL/SKIP | |
| `[E2E-CREATE-MODAL]` | PASS/FAIL | |
| `[E2E-ADMIN-SETUP]` | PASS/FAIL | |
| `[E2E-PARAMS-ROUND-ROBIN]` | PASS/FAIL | |
| `[E2E-ADMIN-START]` | PASS/FAIL | |
| `[E2E-ADMIN-LOCK]` | PASS/FAIL | |
| `[E2E-ACTIVATE-COPY]` | PASS/FAIL | |
| `[E2E-DELETE-RESTORE]` | PASS/FAIL/SKIP | |
| `[LINT-*]` / `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Manual S1.1–S1.4, S0.6, S1.11 | PASS/FAIL | |
| BLOCKED.md | OK / NEW | |

**Verdict:** TEST_PASS / TEST_FAIL
```

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3.3 fix setup)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.3.3_fix_setup.md
- Unit: N passed; API: M passed; E2E: K passed
- Contest start from Parameters + lock verified (S1.12, S1.4)
- Delete/restore: [OK / training mode only]
- Next: …
```

---

## 11. Acceptance mapping (Coder §10)

| Criterion | Test ID |
|-----------|---------|
| Modal name + slug only | T1 → `[E2E-CREATE-MODAL]`, `[UNIT-CREATE-SCHEMA]` |
| Post-create hint | T2 → `[E2E-CREATE-MODAL]` |
| Parameters editable DRAFT | T3 → `[E2E-ADMIN-SETUP]` |
| Round-robin auto + help | T4 → `[UNIT-ROUND-ROBIN-DERIVE]`, `[E2E-PARAMS-ROUND-ROBIN]` |
| Start button + API | T5, T12 → `[E2E-ADMIN-START]`, `[API-START-DRAFT]` |
| Start confirm copy | T6 → `[E2E-ADMIN-START]` |
| Locked parameters | T7 → `[E2E-ADMIN-START]`, `[E2E-ADMIN-LOCK]` |
| Activate modal copy | T8 → `[E2E-ACTIVATE-COPY]` |
| Supervisor delete | T9, T13 → `[E2E-DELETE-RESTORE]`, `[API-DELETE-DRAFT]` |
| Admin restore | T10 → `[E2E-DELETE-RESTORE]`, `[API-RESTORE-WINDOW]` |
| Dev confirm script | T11 → Manual §7.1 |
| Scenarios doc S1.11 | `[DOC-SCENARIOS]` |

---

## 12. Execution order (full pipeline)

Run **in this order** when implementing from scratch:

```text
1. backend/coder_1.15_fix_setup.md     → Coder (src/)
2. coder_2.3.3_fix_setup.md            → Coder (frontend/)
3. tester_2.3.3_fix_setup.md (this)    → §4 lint/unit → §5 pytest → §6 E2E → §7 manual → §10 report
```

**Partial test** (frontend-only landed first):

- Run §4 + `[E2E-CREATE-MODAL]`, `[E2E-ADMIN-SETUP]`, `[E2E-PARAMS-ROUND-ROBIN]`
- Mark T5–T14, S1.12, S0.6 as **SKIP — blocked on 1.15**
- Verdict: `TEST_FAIL` or `PARTIAL` with explicit blocker list

---

## 13. Relationship to other instructions

| File | Scope |
|------|-------|
| `coder_1.15_fix_setup.md` | Backend blocker for start/delete |
| `coder_2.3.3_fix_setup.md` | Frontend spec |
| `tester_2.3.2_fix_tours.md` | Prerequisite |
| `manuals/SUPERVISOR_TESTING_SCENARIOS.md` | Manual IDs S0.6, S1.x |
| `manuals/DEV_SETUP.md` | S1.11 Workflow B |

---

## 14. Explicitly OUT OF SCOPE

- Full tours/results regression (`tester_2.3.2_fix_tours.md`)
- Pause/resume/finish policy changes in production
- Real SMTP invite delivery
- Delete RUNNING contest without pause (must still fail)
