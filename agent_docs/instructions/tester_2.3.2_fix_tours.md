# Tester Instructions — Stage 2.3.2 Fix: Tours & Results Tab UX

> **Status gate:** @Coder `READY_FOR_TEST` for 2.3.2 tours/results fix.
> **Coder spec:** `agent_docs/instructions/coder_2.3.2_fix_tours.md`
> **Prerequisite:** Stage **2.3.1** at `TEST_PASS` (`tester_2.3.1_fix_rounds.md`); **1.14** fixture recommended (`tester_1.14_data_fix.md`).
> **Report:** `agent_docs/reports/test_2.3.2_fix_tours.md` (NEW — Russian summary + PASS/FAIL table)
> **Backend edit on CALCULATED:** **OUT OF SCOPE** — see `coder_2.3.2_backend_calculated_edit.md` + future `tester_2.3.2_backend_calculated_edit.md`.
> **Strategy:** Vitest unit + targeted Playwright + manual lifecycle checklist. **Do not modify** `src/` unless new blocker.

---

## 1. Objective

Verify Stage **2.3.2 frontend** aligns **Туры** and **Результаты** with supervisor workflow: kickoff-gated score entry, display-only **«Идёт»**, no participant LB on Туры, human validation, lifecycle hints, staff LB preview on Результаты.

| ID | Coder | Area | Summary |
|----|-------|------|---------|
| **T1** | §4.1 | New tour form | Empty match date → «Укажите дату и время для каждого матча» |
| **T2** | §4.2 | `ACTIVE` tour | Single «Сохранить изменения» button |
| **T3** | §4.3 | Туры `CALCULATED` | Match table only; **no** `RoundLeaderboardPreview`; CTA «Перейти к результатам» |
| **T4** | §4.3 | Туры `PUBLISHED` | Match table + «Перейти к результатам»; no «Отменить» on Туры |
| **T5** | §4.3 | Туры `CLOSED` | Read-only table; `matchPhaseLabel` «Идёт»; CTA «Перейти к результатам» |
| **T6** | §5.1 | Результаты copy | «Результаты участников» (not «Проверить публичные результаты») |
| **T7** | §3 | Kickoff gating | Pre-kickoff rows disabled; post-kickoff editable on `CLOSED` |
| **T8** | §5.2 | Score re-edit | Re-edit on **`CLOSED` only**; `CALCULATED` readonly + VOID hint |
| **T9** | §5.3 | Staff preview | «Результаты участников» opens LB modal on `CALCULATED` |
| **T10** | §5.4 | Publish flow | «Опубликовать» only on `CALCULATED`; «Рассчитать» only on `CLOSED` |
| **T11** | §4.4 | Lifecycle hints | Updated `roundStatusHint` for `CLOSED`; inline pipeline copy |
| **T12** | §7 | Fixture reset | `--finalize-fixture-only` restores rounds 10/11 matrix |

**Non-goals:**

- `PUT …/result` on `CALCULATED` → `coder_2.3.2_backend_calculated_edit.md`
- Kickoff guard on API
- Full predictions matrix on `PUBLISHED` → **2.4**
- `/admin` → `/supervisor` rename → **1.13**
- 2.3.1 regression re-run (spot-check only unless regressions found)

---

## 2. Test environment

### 2.0 E2E prerequisites (READ FIRST) [UPDATED]

Playwright **сам поднимает UI** (`npm run dev` на `:3000` через `webServer` в `playwright.config.ts`).  
**API на `:8000` нужно запустить вручную** (или одной командой через `dev_setup --run-only`).

**Минимальный запуск для E2E:**

```bash
# Terminal 1 — API (обязательно до npm run test:e2e)
cd /work/football_prog
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2 — тесты (UI Playwright поднимет сам)
cd frontend
npm run test:e2e -- --reporter=line    # line = более читаемый вывод
```

**Или оба сервера одной командой:**

```bash
uv run python src/scripts/dev_setup.py --run-only   # API :8000 + UI :3000
cd frontend && npm run test:e2e
```

**Обязательно в корневом `.env`:**

```bash
SEED_SUPERVISOR_PASSWORD=…   # без этого globalSetup падает сразу
SEED_ADMIN_PASSWORD=…        # нужен adminApi ensureContestRunning
```

**Типичные ошибки:**

| Симптом | Причина | Решение |
|---------|---------|---------|
| `API not reachable at …/health` | Бэк не запущен | Terminal 1: uvicorn |
| `Login failed … PASSWORD_SETUP_REQUIRED` | Старый globalSetup + `ENFORCE_PASSWORD_SETUP=true` | Обновить `playwright.global-setup.ts` (complete-setup) или `ENFORCE_PASSWORD_SETUP=false` на API |
| «Висит» 1–2 мин без вывода | `beforeAll` → `reloadLoadedContestFixture()` (полный `--reset` loader) | Нормально; теперь пишет `[E2E] reloadLoadedContestFixture…` в консоль |
| `SEED_SUPERVISOR_PASSWORD missing` | Пустой `.env` | Заполнить пароли из `.env.example` |

**Диагностика одного spec:**

```bash
DEBUG=pw:webserver npx playwright test e2e/supervisor_tours_phase_panels.spec.ts --reporter=line
```

**После тестов — остановить бэкенд (обязательно):** Playwright **не** гасит API. `Ctrl+C` в терминале с uvicorn, или `pkill -f "uvicorn main:app"`. Затем `dev_setup.py --check-ports` → exit 0. Подробнее: `tester_2.1.md` §2.5.

### 2.1 Manual dev profile (status matrix)

Requires **1.14 finalize** on contest `id=1`:

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

| Round | Status | Use for |
|-------|--------|---------|
| 1–9 | `PUBLISHED` | T4 — Туры panel |
| 10 | `CALCULATED` | T3, T9 — preview on Результаты |
| 11 | `CLOSED`, `SCHEDULED` matches | T5, T7, T8 — kickoff + score entry |

**After mutating rounds 10/11 during tests:**

```bash
uv run python src/scripts/dev_setup.py --finalize-fixture-only
```

Document in report whether finalize was run before manual §8.

### 2.2 Fresh DRAFT profile (T1, T2, full pipeline)

E2E `beforeEach` via `adminApi.ts` — for:

- `[E2E-TOUR-DATE-VALIDATION]` (T1)
- `[E2E-ACTIVE-SINGLE-SAVE]` (T2)
- `[E2E-RESULTS-KICKOFF-GATE]` (T7) — control match `date_time` via API
- `[E2E-RESULTS-PIPELINE]` (T8, T10) — close → scores → calculate → publish

### 2.3 Frontend env

`frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
E2E_SUPERVISOR_PASSWORD=<matches SEED_SUPERVISOR_PASSWORD>
```

### 2.4 Credentials

| Role | Login | Password |
|------|-------|----------|
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` |

---

## 3. Scope — files you may create/modify

```
frontend/src/lib/admin/matchResultsGating.test.ts       # NEW — extend if Coder gaps
frontend/src/lib/admin/deriveAdminUiMode.test.ts        # extend T8
frontend/src/lib/validation/admin.test.ts                 # NEW/extend T1 if present
frontend/e2e/supervisor_tours_phase_panels.spec.ts        # NEW — T3–T5
frontend/e2e/supervisor_results_kickoff.spec.ts           # NEW — T7, T8
frontend/e2e/supervisor_results_preview.spec.ts           # NEW — T6, T9, T10
frontend/e2e/supervisor_create_round.spec.ts              # UPDATE — T1 date validation
frontend/e2e/supervisor_active_round.spec.ts              # UPDATE — T2 single save
frontend/e2e/supervisor_results.spec.ts                   # UPDATE — button labels, publish flow
agent_docs/reports/test_2.3.2_fix_tours.md                # NEW
```

**Do NOT modify:** `docs/`, `src/` (bugs → `BLOCKED.md`).

---

## 4. Unit tests (Vitest) — mandatory

```bash
cd frontend && npm run test:unit
```

### 4.1 `[UNIT-MATCH-KICKOFF-GATE]` — `matchResultsGating.ts` (T7)

| Case | Assert |
|------|--------|
| `CLOSED` + kickoff in past + `SCHEDULED` | `canEnterMatchResult === true` |
| `CLOSED` + kickoff in future + `SCHEDULED` | `false` |
| `CLOSED` + `VOID` / `CANCELED` | `false` |
| `CALCULATED` + any match | `false` (readonly until backend stage) |
| `PUBLISHED` | `false` |
| `ACTIVE` / `DRAFT` | `false` |
| `roundHasStartedMatches` — one past kickoff | `true` |
| `roundHasStartedMatches` — all future | `false` |

### 4.2 `[UNIT-UI-MODE-RESULTS-CLOSED]` — `deriveAdminUiMode.ts` (T8, T10)

| State | Assert |
|-------|--------|
| `CLOSED` + terminal matches incomplete | `canEnterResults`, `canCalculate === false` (until all terminal) |
| `CLOSED` + all terminal | `canCalculate === true`, `canPublish === false` |
| `CALCULATED` | `canEnterResults === false`, `resultsReadonly === true`, `canPublish === true` |
| `PUBLISHED` | `resultsReadonly === true`, `canCalculate === false`, `canPublish === false` |
| `PAUSED` contest | `disableAllMutations` overrides all |

### 4.3 `[UNIT-TOUR-DATE-VALIDATION]` — `admin.ts` / `roundBuilderSchema` (T1)

| Case | Assert |
|------|--------|
| Match with empty `date_time` | Error «Укажите дату и время для каждого матча» |
| All matches valid | No date error; `earliest` computed from valid dates only |
| Invalid date string | Same human message (not Zod default) |

### 4.4 `[UNIT-MATCH-PHASE-LABEL]` — `format.ts` (T5, T11)

| Case | Assert |
|------|--------|
| `CLOSED` + `SCHEDULED` + kickoff passed | `matchPhaseLabel` → «Идёт» |
| `CLOSED` + `SCHEDULED` + kickoff future | «Запланирован» |
| `CLOSED` + `FINISHED` | «Завершён» |
| `CALCULATED` round | delegates to `matchStatusLabel` (not «Идёт») |

### 4.5 `[UNIT-LIFECYCLE-HINTS]` — `roundStatusHint` (T11)

| Status | Assert hint mentions |
|--------|---------------------|
| `CLOSED` | kickoff / вкладка «Результаты» / «Рассчитать» (Coder exact copy) |
| `CALCULATED` | проверка очков / «Опубликовать» |

---

## 5. Backend pytest — regression only

**No new API tests in 2.3.2 frontend stage.** Confirm existing pipeline still green:

```bash
cd /work/football_prog
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
uv run pytest tests/api/test_leaderboard_published_only_2_3_1.py -v
```

### 5.1 `[API-REGRESSION-CALC-PUBLISH]`

| Step | Expected |
|------|----------|
| `PUT result` on `CLOSED` | **200** |
| `POST …/calculate` when all terminal | **200**, round → `CALCULATED` |
| `POST …/publish` on `CALCULATED` | **200**, round → `PUBLISHED` |
| `PUT result` on `CALCULATED` | **403** `ROUND_NOT_CLOSED` — **expected until backend stage** |

Tag `[API-CALCULATED-PUT-BLOCKED]` as **EXPECTED_FAIL / N/A** in report — not a 2.3.2 frontend blocker.

---

## 6. E2E tests (Playwright) — mandatory

**API `:8000` must be running before `npm run test:e2e`.** UI `:3000` is started by Playwright (`webServer`). See [§2.0 E2E prerequisites](#20-e2e-prerequisites-read-first-updated).

Real API. Both endpoints reachable (API manual, UI auto).

### 6.1 `[E2E-TOUR-DATE-VALIDATION]` — T1

**Setup:** fresh DRAFT contest, open `RoundBuilderForm`.

| Step | Expected |
|------|----------|
| Add match, leave date empty, submit | Inline «Укажите дату и время для каждого матча» |
| Fill all dates, submit | Proceeds (no date error) |

Extend `supervisor_create_round.spec.ts` or dedicated spec.

### 6.2 `[E2E-ACTIVE-SINGLE-SAVE]` — T2

**Setup:** ACTIVE round on fresh or loaded contest.

| Step | Expected |
|------|----------|
| Open `/admin/rounds`, select ACTIVE tour | Exactly **one** «Сохранить изменения» button visible |
| Change team or match field → save | Single save succeeds |

### 6.3 `[E2E-UI-TOUR-PHASE-PANELS]` — T3–T5

**Setup:** loaded contest `id=1` (1.14). Login supervisor → `/admin/rounds`.

| Round | Tag | Assert |
|-------|-----|--------|
| 11 `CLOSED` | `[UI-TOUR-CLOSED]` | Match table read-only; status «Идёт» or «Запланирован» via kickoff; **«Перейти к результатам»**; **no** participant LB table; **no** «Опубликовать» on Туры |
| 10 `CALCULATED` | `[UI-TOUR-CALCULATED]` | Scores visible; **no** `RoundLeaderboardPreview`; **«Перейти к результатам»** only |
| 9 `PUBLISHED` | `[UI-TOUR-PUBLISHED]` | Match table; **«Перейти к результатам»**; **no** «Отменить» on Туры |

**Negative:** page must **not** contain «Проверить публичные результаты» on `/admin/rounds`.

Suggested file: `supervisor_tours_phase_panels.spec.ts`.

### 6.4 `[E2E-UI-RESULTS-KICKOFF-GATE]` — T7

**Setup:** fresh contest — create `CLOSED` round with two matches:

- Match A: kickoff **−1 hour** (past)
- Match B: kickoff **+2 hours** (future)

Navigate `/admin/results`, select tour.

| Step | Expected |
|------|----------|
| Match A row | Score inputs **enabled** (or «Применить» available) |
| Match B row | Inputs **disabled**; hint «Матч ещё не начался» (or kickoff time) |
| Optional banner | «Счёт можно вносить после времени начала каждого матча» on `CLOSED` |

Suggested file: `supervisor_results_kickoff.spec.ts`.

### 6.5 `[E2E-UI-RESULTS-REEDIT-CLOSED]` — T8

**Setup:** `CLOSED` round, post-kickoff match with score saved (`FINISHED`).

| Step | Expected |
|------|----------|
| Change score1/score2, «Применить» | **200**; row stays editable |
| «Рассчитать» → `CALCULATED` | Score inputs **readonly**; «Применить» hidden |
| Hint on `CALCULATED` | Mentions VOID or backend 2.3.2-backend (Coder copy) |
| Attempt edit via UI on `CALCULATED` | No PUT triggered (readonly) |

**Do not** expect PUT on `CALCULATED` to succeed — API still 403.

### 6.6 `[E2E-UI-RESULTS-PREVIEW-CALC]` — T6, T9

**Setup:** round 10 `CALCULATED` on loaded contest (or API-built).

| Step | Expected |
|------|----------|
| `/admin/results` — button label | **«Результаты участников»** (not «Проверить публичные…») |
| On `CLOSED` round | Button **disabled**, `title` ≈ «Сначала рассчитайте тур» |
| On `CALCULATED` | Button **enabled** → modal/drawer with LB preview (staff table) |
| On `PUBLISHED` | Enabled — stub or public link per Coder §5.3 |

Suggested file: `supervisor_results_preview.spec.ts`.

### 6.7 `[E2E-UI-RESULTS-PIPELINE]` — T10

**Setup:** fresh DRAFT — full lifecycle or mutate round 11 if reset available.

| Step | Expected |
|------|----------|
| `CLOSED` + all terminal | «Рассчитать» visible; «Опубликовать» hidden |
| After calculate | «Опубликовать» visible; «Рассчитать» hidden |
| After publish | Both hidden or disabled; scores readonly |

Update `supervisor_results.spec.ts` if labels/actions changed.

### 6.8 `[E2E-UI-MATCH-PHASE-RESULTS-TAB]` — T5 extension

On `/admin/results` for round 11 `CLOSED`:

| Assert |
|--------|
| Status column uses `matchPhaseLabel` — «Идёт» for past-kickoff `SCHEDULED` |
| Same labels consistent with `/admin/rounds` for same matches |

---

## 7. Manual checklist — supervisor walkthrough

Human verification on contest `id=1` (after `--finalize-fixture-only` if tests mutated data):

> Разработчик вручную проходит сценарий QA 2026-06-27:

### 7.1 Туры (`/admin/rounds`)

- [ ] **T1** — создать тур без даты матча → понятная ошибка
- [ ] **T2** — ACTIVE: одна кнопка «Сохранить изменения»
- [ ] **T5** — тур 11: таблица матчей, «Идёт», нет LB участников, «Перейти к результатам»
- [ ] **T3** — тур 10: счета, нет LB, только CTA на Результаты
- [ ] **T4** — тур 9 PUBLISHED: таблица, CTA, нет «Отменить» на Туры
- [ ] **T11** — hint для CLOSED упоминает Результаты и Рассчитать

### 7.2 Результаты (`/admin/results`)

- [ ] **T7** — тур 11: до kickoff строка disabled; после — ввод счёта
- [ ] **T8** — правка счёта на CLOSED; после «Рассчитать» — readonly
- [ ] **T6/T9** — «Результаты участников»; preview на CALCULATED
- [ ] **T10** — «Рассчитать» / «Опубликовать» в правильных фазах
- [ ] **T5** — колонка статуса «Идёт» на CLOSED

### 7.3 Fixture

- [ ] **T12** — `--finalize-fixture-only` восстанавливает туры 10/11

Tag in report: `Manual checklist | REMINDER` or `PASS` if human confirmed.

---

## 8. Documentation audit (read-only)

| ID | Check |
|----|-------|
| `[DOC-STATUS-REF]` | `manuals/STATUS_REFERENCE.md` — lifecycle §2.3; CALCULATED edit deferred to backend doc |
| `[DOC-DEV-SETUP]` | `manuals/DEV_SETUP.md` — `--finalize-fixture-only` QA reset (T12) |
| `[DOC-FRONT-INTEGRATION]` | `agent_docs/contracts/frontend_api_integration.md` — kickoff UI gate note if Coder updated |

**Do not** expect `API_GUIDE.md` CALCULATED PUT changes in frontend-only stage.

---

## 9. Lint & build — mandatory

```bash
cd frontend
npm run lint
npm run type-check
npm run format:check
npm run build
```

| ID | Pass |
|----|------|
| `[LINT-ESLINT]` | exit 0 |
| `[LINT-TSC]` | exit 0 |
| `[LINT-PRETTIER]` | exit 0 |
| `[BUILD]` | exit 0 |

---

## 10. Playwright teardown — MANDATORY

Same as `tester_2.3.1_fix_rounds.md` §10 / `tester_2.1.md` §2.5:

1. Confirm Playwright process fully exited.
2. **Stop API** — `Ctrl+C` in uvicorn / `dev_setup --run-only` terminal, or `pkill -f "uvicorn main:app"`.
3. `uv run python src/scripts/dev_setup.py --check-ports` → exit 0.
4. Kill orphans on `:3000` / `:8000` if needed (`next dev`, headless Chromium).
5. **Then** run `--finalize-fixture-only` or handoff.

| Tag | Pass criteria |
|-----|---------------|
| `[E2E-TEARDOWN]` | `--check-ports` exit 0; **API stopped** (no uvicorn on `:8000`) |

---

## 11. Execution order

```bash
# 1. API regression (no new tests)
uv run pytest tests/api/test_calculate_leaderboard_1_4.py \
  tests/api/test_leaderboard_published_only_2_3_1.py -v

# 2. Frontend unit
cd frontend && npm run test:unit

# 3. Frontend lint
npm run lint && npm run type-check && npm run format:check

# 4. Bootstrap manual profile
cd /work/football_prog
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# 5. E2E (frontend dir)
cd frontend
npm run test:e2e -- supervisor_tours_phase_panels.spec.ts \
  supervisor_results_kickoff.spec.ts supervisor_results_preview.spec.ts \
  supervisor_create_round.spec.ts supervisor_active_round.spec.ts \
  supervisor_results.spec.ts

# 6. TEARDOWN + fixture restore
cd /work/football_prog
uv run python src/scripts/dev_setup.py --check-ports
uv run python src/scripts/dev_setup.py --finalize-fixture-only

# 7. Build
cd frontend && npm run build

# 8. Doc audit §8 (read-only)
```

Prefer E2E order: **date_validation → active_save → tour_panels → kickoff → reedit → preview → pipeline**.

---

## 12. Report template — `agent_docs/reports/test_2.3.2_fix_tours.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-MATCH-KICKOFF-GATE]` | PASS/FAIL | |
| `[UNIT-UI-MODE-RESULTS-CLOSED]` | PASS/FAIL | |
| `[UNIT-TOUR-DATE-VALIDATION]` | PASS/FAIL | |
| `[UNIT-MATCH-PHASE-LABEL]` | PASS/FAIL | |
| `[UNIT-LIFECYCLE-HINTS]` | PASS/FAIL | |
| `[API-REGRESSION-CALC-PUBLISH]` | PASS/FAIL | |
| `[API-CALCULATED-PUT-BLOCKED]` | EXPECTED | 403 until backend stage |
| `[E2E-TOUR-DATE-VALIDATION]` | PASS/FAIL | T1 |
| `[E2E-ACTIVE-SINGLE-SAVE]` | PASS/FAIL | T2 |
| `[UI-TOUR-CLOSED]` | PASS/FAIL | round 11 |
| `[UI-TOUR-CALCULATED]` | PASS/FAIL | round 10 |
| `[UI-TOUR-PUBLISHED]` | PASS/FAIL | round 9 |
| `[E2E-UI-RESULTS-KICKOFF-GATE]` | PASS/FAIL | T7 |
| `[E2E-UI-RESULTS-REEDIT-CLOSED]` | PASS/FAIL | T8 |
| `[E2E-UI-RESULTS-PREVIEW-CALC]` | PASS/FAIL | T6, T9 |
| `[E2E-UI-RESULTS-PIPELINE]` | PASS/FAIL | T10 |
| `[E2E-UI-MATCH-PHASE-RESULTS-TAB]` | PASS/FAIL | |
| `[E2E-TEARDOWN]` | PASS/FAIL | §10 |
| `[LINT-ESLINT]` | PASS/FAIL | |
| `[LINT-TSC]` | PASS/FAIL | |
| `[LINT-PRETTIER]` | PASS/FAIL | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| `[FIXTURE-RESET]` | PASS/FAIL | T12 |
| Manual checklist | REMINDER/PASS | §7 |
| 1.14 fixture used | Y/N | |
| BLOCKED.md | OK / NEW | |

**Verdict:** `TEST_PASS` / `TEST_FAIL` with blockers for @Coder.

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3.2 fix tours)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.3.2_fix_tours.md
- Unit: N passed; API regression: M passed; E2E: K passed
- Kickoff gating + «Идёт» on Туры/Результаты verified
- CALCULATED score edit: readonly (backend stage pending)
- E2E teardown: [E2E-TEARDOWN] PASS
- Next: coder_2.3.2_backend_calculated_edit.md / tester backend
```

---

## 13. Acceptance mapping (Coder §10)

| Criterion | Test ID |
|-----------|---------|
| T1 — human date validation | `[UNIT-TOUR-DATE-VALIDATION]`, `[E2E-TOUR-DATE-VALIDATION]` |
| T2 — single save on ACTIVE | `[E2E-ACTIVE-SINGLE-SAVE]` |
| T3–T5 — Туры phase panels | `[UI-TOUR-*]`, `[E2E-UI-TOUR-PHASE-PANELS]` |
| T6 — button rename | `[E2E-UI-RESULTS-PREVIEW-CALC]` |
| T7 — kickoff gating | `[UNIT-MATCH-KICKOFF-GATE]`, `[E2E-UI-RESULTS-KICKOFF-GATE]` |
| T8 — re-edit CLOSED only | `[UNIT-UI-MODE-RESULTS-CLOSED]`, `[E2E-UI-RESULTS-REEDIT-CLOSED]` |
| T9 — staff LB preview | `[E2E-UI-RESULTS-PREVIEW-CALC]` |
| T10 — calculate/publish buttons | `[E2E-UI-RESULTS-PIPELINE]` |
| T11 — lifecycle hints | `[UNIT-LIFECYCLE-HINTS]`, manual §7 |
| T12 — fixture reset | `[FIXTURE-RESET]`, `[DOC-DEV-SETUP]` |
| No `src/` changes | git diff scope check in report |
| «Идёт» display-only | `[UNIT-MATCH-PHASE-LABEL]`, `[E2E-UI-MATCH-PHASE-RESULTS-TAB]` |
| E2E teardown | `[E2E-TEARDOWN]` |

---

## 14. Relationship to other instructions

| File | Scope |
|------|-------|
| `tester_2.3.1_fix_rounds.md` | Prerequisite — 24h, LB gate, phase panels baseline |
| `tester_1.14_data_fix.md` | Fixture rounds 10/11 — **recommended TEST_PASS** |
| `coder_2.3.2_backend_calculated_edit.md` | **Next** — PUT on CALCULATED + UI unlock |
| `tester_2.4.md` | Full «Результаты участников» matrix on PUBLISHED |

**Recommended order:** `tester_2.3.1` → `coder_2.3.2_fix_tours` → `tester_2.3.2_fix_tours` (this file) → backend stage.

---

## 15. Explicitly OUT OF SCOPE

- `PUT result` on `CALCULATED` success path → backend instruction
- API kickoff enforcement
- Full 2.3.1 / full 2.3 E2E re-run (17 specs) unless regressions
- `toHaveScreenshot()` vs `docs/screens/supervisor_*.jpg`
- Public predictions matrix polish → **2.4**
