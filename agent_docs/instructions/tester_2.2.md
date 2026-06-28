# Tester Instructions — Stage 2.2: Predictions & Privacy

> **Status gate:** @Coder `READY_FOR_TEST` for 2.2 in `agent_docs/progress/stage_2.md`.
> **Prerequisites:** Sub-stages **2.1**, **2.1.1**, and **2.3** at `TEST_PASS`. Backend predictions API Stage 1.3+ (`test_1.3.md` / `test_operational_gaps_1_4.py`).
> **Dev note:** Test user `user/user` comes from `bootstrap_users.py` (2.1.1) until invite UI removes demo seed — see `agent_docs/reports/todo.md`.
> **Reference:** `instructions/coder_2.2.md`, `docs/03_user_scenarios.md` §3–§4 (E2E §), `docs/06_front_tests.md`, `agent_docs/contracts/frontend_api_integration.md`, `agent_docs/contracts/admin_ui_status_matrix.md` (§10–11).
> **Strategy:** Unit (Vitest) + E2E (Playwright) — **agent runs**; visual/mobile UX — **human** (agent reminds in report).

---

## 1. Objective

Verify Stage **2.2** frontend deliverables:

1. **Unit tests** — score range, batch schema, privacy helper, deadline warning (`npm run test:unit`).
2. **E2E (Playwright)** — batch gating, validation, privacy pre/post deadline, deadline block, user flow smoke.
3. **Lint & build** — ESLint, `type-check`, `format:check`, `build`.
4. **Docs** — Coder updated living UI specs (§8 of `coder_2.2.md`).

**Non-goals (later sub-stages):**

- Full leaderboard / results tab matrices → **2.4**
- Supervisor admin flows → **2.3**
- Visual pixel-perfect match to `user_predict.jpg` → **manual human**

---

## 2. Test environment

### 2.0 E2E prerequisites (READ FIRST) [UPDATED]

Playwright **starts UI automatically** (`npm run dev` on `:3000` via `webServer` in `playwright.config.ts`).  
**API on `:8000` must be running before** `npm run test:e2e` (Playwright does **not** start the backend).

**Minimal E2E run:**

```bash
# Terminal 1 — API (required before test:e2e)
cd /work/football_prog
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2 — tests (Playwright starts UI on :3000)
cd frontend
npm run test:e2e -- --reporter=line    # line = clearer progress output
```

**Or both servers in one command** (then run E2E in another terminal):

```bash
uv run python src/scripts/dev_setup.py --run-only   # API :8000 + UI :3000
cd frontend && npm run test:e2e
```

**Required in root `.env`** (even for user-only specs — `playwright.global-setup.ts` provisions an E2E user):

```bash
SEED_SUPERVISOR_PASSWORD=…   # globalSetup fails immediately if missing
SEED_ADMIN_PASSWORD=…        # optional for 2.2; needed if supervisor API helpers used
```

**Common failures (look like “hang” or silent exit):**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `API not reachable at …/health` | Backend not started | Terminal 1: `uvicorn` (see above) |
| `Login failed … PASSWORD_SETUP_REQUIRED` | Outdated `playwright.global-setup.ts` | Use repo version: `complete-setup` via `setup_url` from invite (works with default `enforce_password_setup=true` from `settings.py`) |
| No output 1–2 min at start | `globalSetup` provisioning user + Next.js first compile | Normal; use `--reporter=line` or `DEBUG=pw:webserver` |
| Supervisor specs “freeze” ~60–120 s | `beforeAll` → `reloadLoadedContestFixture()` (`load_test_data --reset`) | Normal; console shows `[E2E] reloadLoadedContestFixture…` |
| `SEED_SUPERVISOR_PASSWORD missing` | Empty `.env` | Copy from `.env.example` and set passwords |

**Debug a single spec:**

```bash
DEBUG=pw:webserver npx playwright test e2e/prediction_batch.spec.ts --reporter=line
```

**After tests — stop backend (mandatory):** Playwright does **not** stop API. `Ctrl+C` in the uvicorn terminal, or `pkill -f "uvicorn main:app"`. Then `dev_setup.py --check-ports` → exit 0. Details: `tester_2.1.md` §2.5.

See also: `tester_2.3.2_fix_tours.md` §2.0 (same Playwright stack).

### 2.1 Backend (Terminal 1)

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/load_test_data.py --reset   # contest id=1; see fixture table below
# Prediction E2E needs ACTIVE round 10 — full loader leaves round 10 CALCULATED (coder_1.14):
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

See `agent_docs/instructions/backend/coder_1.14_data_fix.md` if round 10 is not ACTIVE after bootstrap.

Health: `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`.

> **E2E:** DB bootstrap below is **one-time** (or when resetting fixture). For re-runs, only **API** must stay up — see [§2.0](#20-e2e-prerequisites-read-first-updated).

**Key fixture facts** (after `coder_1.14` full profile + `--e2e` restore):

| Item | Value |
|------|-------|
| Contest id | `1` (RUNNING, locked) |
| Open predictions round | **10** — must be **`ACTIVE`**, deadline in future — use `--ensure-running-only --e2e` (not default after `--reset` alone) |
| Post-deadline privacy round | **9** — **`PUBLISHED`**, deadline passed (`deadline_passed === true` on GET predictions) |
| Other history | Rounds **1–8** also `PUBLISHED` (public LB includes them; not used in default 2.2 specs) |
| Round 10 without `--e2e` | **`CALCULATED`** after full finalize — good for LB stub tests (not published), **bad** for predict POST until restored ACTIVE |
| Round 11 | **`CLOSED`** — no scores in public LB |
| `matches_per_round` | 8 (from contest defaults) |
| `maxScore` | from `rules_json.constraints.score_validation_range[1]` — verify via `GET /contests/1`, do not assume 20 |
| Test user | `user` / `user` (bootstrap demo user, 2.1.1) |
| Second user | `shutov` / `user` or another loader login for privacy cross-check |

### 2.2 Frontend env

`frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Optional for deadline E2E: `E2E_SUPERVISOR_PASSWORD` in gitignored env if API helper needed to rewind deadline (prefer API `request` fixture over DB). Root `SEED_SUPERVISOR_PASSWORD` in `.env` is still required for Playwright `globalSetup`.

### 2.3 Playwright

See [§2.0 E2E prerequisites](#20-e2e-prerequisites-read-first-updated): **API `:8000` manual**, **UI `:3000` auto** via `webServer`. Do **not** start `npm run dev` separately unless debugging UI outside Playwright.

**Mandatory after E2E:** `tester_2.1.md` §2.5 — **stop API** (`Ctrl+C` or `pkill -f "uvicorn main:app"`), then `dev_setup.py --check-ports`; kill orphan `next dev` / headless Chromium if Playwright did not exit cleanly.

---

## 3. Scope — files you may create/modify

```
frontend/e2e/fixtures/
  auth.ts                         # extend from 2.1
  predictionsApi.ts               # NEW — login, getRoundId, setRoundDeadline, getMaxScore
frontend/e2e/
  prediction_validation.spec.ts   # NEW
  prediction_batch.spec.ts        # NEW — 7/8 vs 8/8, score 0
  prediction_privacy.spec.ts      # NEW — pre/post deadline
  prediction_deadline_warning.spec.ts  # NEW — <24h banner
  deadline_block.spec.ts          # NEW — readonly after deadline
  user_predict_flow.spec.ts       # NEW — profile → predict → save → edit
  visitor_predictions_stub.spec.ts     # NEW — visitor stub pre-deadline
  contest_predictions_tab.spec.ts      # NEW — Прогнозы tab on /contest/1
agent_docs/reports/test_2.2.md    # NEW — verdict report
```

**Do NOT modify:** `docs/`, Python `src/` (backend bugs → `BLOCKED.md`).

---

## 4. E2E fixtures — `predictionsApi.ts` (recommended)

```ts
const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';

export async function getContestMaxScore(contestId = 1): Promise<number> {
  const r = await fetch(`${API}/api/v1/contests/${contestId}`);
  const j = await r.json();
  return j.rules_json.constraints.score_validation_range[1];
}

export async function getRoundIdByNumber(contestId: number, number: number, token?: string) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const r = await fetch(`${API}/api/v1/contests/${contestId}/rounds`, { headers });
  const rounds = await r.json();
  return rounds.find((x: { number: number }) => x.number === number)?.id;
}

// For deadline_block: supervisor PATCH round deadline to past (if UI test needs API setup)
// Note: backend 1.16 auto-closes round on GET …/predictions when deadline passed.
// Supervisor 24h rule (2.3.1) limits deadline *changes* — prefer round 9 (already past) for post-deadline matrix tests.

export async function ensureRound10Active(/* … */) {
  // Optional: call dev_setup --e2e or admin activate path — see coder_1.14_data_fix.md §6
}
```

Use **round 10** (ACTIVE after `--e2e`) for open predictions; **round 9** (`PUBLISHED`, deadline passed) for post-deadline matrix tests.

---

## 5. Unit tests (Vitest) — mandatory

Run from `frontend/`:

```bash
npm run test:unit
```

### 5.1 Required coverage

| ID | Target | Assert |
|----|--------|--------|
| `[UNIT-SCORE-RANGE]` | `lib/validation/score.ts` | `0` valid; `max` valid; `max+1` invalid; non-int invalid |
| `[UNIT-BATCH-SCHEMA]` | `lib/validation/prediction.ts` | `matchCount=8`: 7 items fail; 8 pass; respects dynamic `maxScore` |
| `[UNIT-PRIVACY-SHOW]` | `lib/privacy/shouldShowScore.ts` | Pre-deadline: own yes, other no, ADMIN yes; post-deadline: all with data |
| `[UNIT-DEADLINE-WARN]` | `deadlineWarning` helper | `secondsLeft=3600` → true; `86401` → false; `0` → false |

**Pass:** all green.

---

## 6. E2E tests (Playwright) — mandatory

**API `:8000` running before `npm run test:e2e`.** UI started by Playwright. See [§2.0](#20-e2e-prerequisites-read-first-updated).

Real API for happy paths. Russian selectors (`getByRole`, visible text).

### 6.1 `[E2E-PRED-BATCH]` — `prediction_batch.spec.ts`

**Setup:** login `user/user`; navigate `/contest/1/predict/{round10Id}`.

1. Fill **7 of 8** match score pairs → **Сохранить прогноз** **disabled**.
2. Fill 8th match → button **enabled**.
3. Set one match to **`0 : 0`** → still enabled (0 is valid).
4. Save → success toast or readonly state; reload → values persisted.

Maps to: batch-only, score 0 valid.

### 6.2 `[E2E-PRED-VALIDATION]` — `prediction_validation.spec.ts`

**Setup:** read `maxScore` from API helper.

1. Type letters in score field → not accepted or inline error; submit stays disabled.
2. Type `maxScore + 1` → error / disabled submit.
3. Fill all with valid scores including `0` → save succeeds.

Source: `docs/03` E2E § `prediction_validation.spec.ts`.

### 6.3 `[E2E-PRED-PRIVACY-PRE]` — `prediction_privacy.spec.ts`

**Setup:** two users — `shutov` saves 8/8 on round 10; `volchenko` views Прогнозы tab or predict page matrix.

1. As `volchenko` on `/contest/1` tab **Прогнозы** (round 10, before deadline):
   - Own row: scores or empty if not submitted.
   - Row for `shutov`: cells show **«Прогноз сделан»** (not `2:1` or actual scores).
2. As `shutov`: own row shows entered scores.

Cross-check: `GET …/predictions` → other entries have `predictions: null`.

Maps to: **UC-8**, pre-deadline privacy.

### 6.4 `[E2E-PRED-PRIVACY-POST]` — `prediction_privacy.spec.ts` (same file, second test)

**Setup:** round **9** (deadline passed in loader) OR API set round 10 deadline to past **after** users submitted.

1. Login as `volchenko` → `/contest/1` → **Прогнозы** → select round 9 (or post-deadline round).
2. Assert **full scores visible** for submitted participants (not «Прогноз сделан»).
3. API: `deadline_passed === true`; entries with `submitted` have non-null `predictions`.

**Note:** Visitor without login still gets 401 on GET — expect **login prompt**, not full matrix. Post-deadline full table test uses **authenticated** user per backend contract.

Maps to: **UC-9**, post-deadline matrix.

### 6.5 `[E2E-PRED-DEADLINE-WARN]` — `prediction_deadline_warning.spec.ts`

**Setup:** fresh round or API PATCH round 10 deadline to **now + 12 hours** (if supervisor token available); else skip with manual note.

1. Open predict page before deadline.
2. Assert **`DeadlineWarningBanner`** visible (text contains «24 час» or «скоро» / «менее»).
3. When deadline &gt; 24h away (loader default) → banner **absent** (negative case optional).

Maps to: deadline warning requirement.

### 6.6 `[E2E-DEADLINE-BLOCK]` — `deadline_block.spec.ts`

**Setup:** save valid 8/8 as `user`; then API set round deadline to **past** (supervisor `PATCH …/admin/rounds/{id}` or test helper).

1. Reload predict page → inputs **readonly**; **Сохранить** / **Редактировать** disabled.
2. Countdown shows **«Дедлайн прошёл»**.
3. Optional: force submit via UI if any enabled → toast with 403 / `DEADLINE_PASSED`.

Source: `docs/03` E2E § `deadline_block.spec.ts`.

### 6.7 `[E2E-USER-PREDICT-FLOW]` — `user_predict_flow.spec.ts`

1. Login `user/user` → `/profile`.
2. Click **Сделать прогноз** → lands on `/contest/1/predict/{roundId}`.
3. Fill 8/8 → **Сохранить** → **Редактировать** appears.
4. Click **Редактировать** → change one score → **Сохранить** → persisted after reload.

Source: `docs/03` partial `user_full_flow` (full flow with logout → 2.4).

### 6.8 `[E2E-VISITOR-PRED-STUB]` — `visitor_predictions_stub.spec.ts`

1. Clear storage; visit `/contest/1` → tab **Прогнозы** (current round 10).
2. Assert stub **«Будет доступно после дедлайна»** (or equivalent).
3. Assert **no** participant score matrix with real numbers.

### 6.9 `[E2E-CONTEST-PRED-TAB]` — `contest_predictions_tab.spec.ts`

1. Login as `user/user` → `/contest/1`.
2. `RoundSelector` visible; switch round 9 vs 10.
3. Tab **Прогнозы** renders `PredictionsMatrix` (table/grid with match headers).
4. Tab switch does not crash; refetch on round change.

### 6.10 `[E2E-LB-STUB-NOT-PUBLISHED]` — optional `contest_leaderboard_stub.spec.ts`

**Setup:** round **10** in **`CALCULATED`** state (default after full loader without `--e2e`) OR select any non-`PUBLISHED` round on **Лидерборд** tab.

1. Visit `/contest/1` → tab **Лидерборд** → select round 10 (if listed).
2. Assert stub **«Будет доступно после проверки организатором»** (or `ROUND_NOT_PUBLISHED_COPY`).
3. Assert **no** standings table with participant ranks (no successful public LB render for unpublished round).

Maps to: 2.3.1 F12 / `admin_ui_status_matrix.md` §10. **Skip** if Coder deferred all LB tab work to 2.4 — document SKIP in report.

---

## 7. TypeScript lint & build (mandatory)

Re-run full lint gate (scripts from Coder 2.1):

```bash
cd frontend
npm run lint
npm run type-check
npm run format:check
npm run build
```

| ID | Command | Pass criteria |
|----|---------|---------------|
| `[LINT-ESLINT]` | `npm run lint` | exit 0; errors = FAIL |
| `[LINT-TSC]` | `npm run type-check` | exit 0 |
| `[LINT-PRETTIER]` | `npm run format:check` | exit 0 |
| `[BUILD]` | `npm run build` | exit 0 |

---

## 8. Documentation audit (read-only)

| ID | Pass criteria |
|----|---------------|
| `[DOC-UI-COMPONENTS]` | `components.md` — PredictionForm, PredictionsMatrix, ScoreInput, Deadline* marked **Implemented (2.2)** |
| `[DOC-UI-PAGES]` | `pages.md` — `/contest/[id]/predict/[rid]`, Прогнозы tab; **PUBLISHED-only** LB/Results stubs (2.3.1) |
| `[DOC-FORMS]` | `forms_validation.md` — prediction schema paths |
| `[DOC-INTEGRATION]` | `frontend_api_integration.md` — predictions matrix, visitor 401 note; client `PUBLISHED` gate documented or cross-ref `admin_ui_status_matrix.md` §10 |
| `[DOC-CODER-HANDOFF]` | `stage_2.md` Coder 2.2 `READY_FOR_TEST` |

---

## 9. Blocker verification — `BLOCKED.md`

After tests:

1. Verify **Stage 2.2 readiness checklist** (§10 below) against results.
2. No backend blockers expected for 2.2 (predictions API exists since 1.3).
3. If anonymous post-deadline viewing required by product but API returns 401 → document in report; do **not** fail 2.2 if Coder implemented login prompt per `coder_2.2.md` §5.4 (by design).

---

## 10. Manual checklist — human developer (agent reminds)

Include in `test_2.2.md`:

> Разработчик должен вручную проверить перед релизом 2.2:
> - [ ] Layout формы vs `user_predict.jpg` (матчи, поля счёта, кнопки)
> - [ ] Подпись «0–N» соответствует правилам конкурса
> - [ ] `DeadlineWarningBanner` заметен (цвет/иконка)
> - [ ] «Прогноз сделан» читаемо; нет утечки чужих счётов до дедлайна
> - [ ] Пустое поле ≠ 0: cleared cell не отправляет 0
> - [ ] Мобильная ширина ~375px — форма и матрица с horizontal scroll

---

## 11. Execution order

```bash
# Terminal 1 — keep API running (see §2.0)
cd /work/football_prog && uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend && npm run test:unit
npm run lint && npm run type-check && npm run format:check
npm run test:e2e -- --reporter=line
# Stop API in Terminal 1 (Ctrl+C), then:
uv run python src/scripts/dev_setup.py --check-ports   # §2.5 / tester_2.1 §2.5
npm run build
```

Suggested E2E order: **batch → validation → privacy → deadline_warn → deadline_block → user_flow → visitor_stub → contest_tab**.

---

## 12. Report template — `agent_docs/reports/test_2.2.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-SCORE-RANGE]` | PASS/FAIL | |
| `[UNIT-BATCH-SCHEMA]` | PASS/FAIL | |
| `[UNIT-PRIVACY-SHOW]` | PASS/FAIL | |
| `[UNIT-DEADLINE-WARN]` | PASS/FAIL | |
| `[E2E-PRED-BATCH]` | PASS/FAIL | |
| `[E2E-PRED-VALIDATION]` | PASS/FAIL | maxScore=N |
| `[E2E-PRED-PRIVACY-PRE]` | PASS/FAIL | |
| `[E2E-PRED-PRIVACY-POST]` | PASS/FAIL | |
| `[E2E-PRED-DEADLINE-WARN]` | PASS/FAIL/SKIP | |
| `[E2E-DEADLINE-BLOCK]` | PASS/FAIL | |
| `[E2E-USER-PREDICT-FLOW]` | PASS/FAIL | |
| `[E2E-VISITOR-PRED-STUB]` | PASS/FAIL | |
| `[E2E-CONTEST-PRED-TAB]` | PASS/FAIL | |
| `[E2E-LB-STUB-NOT-PUBLISHED]` | PASS/FAIL/SKIP | 2.3.1 F12 |
| `[E2E-TEARDOWN]` | PASS/FAIL | `--check-ports` exit 0; API stopped (tester_2.1 §2.5) |
| `[LINT-ESLINT]` | PASS/FAIL | |
| `[LINT-TSC]` | PASS/FAIL | |
| `[LINT-PRETTIER]` | PASS/FAIL | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Manual checklist | REMINDER | §10 |

**Verdict:** `TEST_PASS` / `TEST_FAIL`.

On **TEST_PASS:** ready for **2.4** (leaderboard & integration). Dependency graph: `2.1 → 2.1.1 → 2.3 → 2.2 → 2.4`.

---

## 13. Acceptance mapping (Coder §9 + plan checklist)

| Criterion | Test ID |
|-----------|---------|
| 7/8 → submit disabled | `[E2E-PRED-BATCH]`, `[UNIT-BATCH-SCHEMA]` |
| 8/8 → save → reload | `[E2E-PRED-BATCH]`, `[E2E-USER-PREDICT-FLOW]` |
| Score 0 valid | `[E2E-PRED-BATCH]` |
| Invalid chars / out of range | `[E2E-PRED-VALIDATION]`, `[UNIT-SCORE-RANGE]` |
| maxScore from rules | `[E2E-PRED-VALIDATION]` (read from API) |
| Pre-deadline: others masked | `[E2E-PRED-PRIVACY-PRE]` |
| Post-deadline: full matrix (auth) | `[E2E-PRED-PRIVACY-POST]` (round 9 PUBLISHED) |
| LB/Results stub non-PUBLISHED | `[E2E-LB-STUB-NOT-PUBLISHED]` (optional) |
| Visitor pre-deadline stub | `[E2E-VISITOR-PRED-STUB]` |
| Deadline warning &lt;24h | `[E2E-PRED-DEADLINE-WARN]`, `[UNIT-DEADLINE-WARN]` |
| After deadline readonly | `[E2E-DEADLINE-BLOCK]` |
| Edit flow | `[E2E-USER-PREDICT-FLOW]` |
| `npm run test:unit` / lint / `build` | `[UNIT-*]`, `[LINT-*]`, `[BUILD]` |

---

## 14. Progress update

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.2)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.2.md
- Unit: N passed; E2E: M passed (K skipped)
- Build: OK
- Next: instructions/coder_2.4.md
```

---

## 15. Explicitly OUT OF SCOPE

- `[E2E-LEADERBOARD-*]`, results matrix → **2.4**
- `[E2E-ADMIN-*]`, supervisor flows → **2.3**
- `[E2E-USER-FULL-FLOW]` with leaderboard + logout polish → **2.4**
- Backend `[API-PRED-*]` regression (Stage 1.3 tests)
- ADMIN pre-deadline sees all — optional smoke; not blocking USER privacy path
