# Tester Instructions — Stage 2.3.1 Fix: Round Statuses, 24h Rule, Public LB Gate

> **Status gate:** @Coder `READY_FOR_TEST` for 2.3.1 rounds/status fix.
> **Coder spec:** `agent_docs/instructions/coder_2.3.1_fix.md`
> **Prerequisite:** Stage 2.3 admin UI shipped; `tester_2.3.md` or `tester_2.3.1_fix.md` E2E infra green.
> **Recommended:** `tester_1.14_data_fix.md` → **TEST_PASS** for full manual matrix (round 10 `CALCULATED`, round 11 `CLOSED` on contest `id=1`).
> **Report:** `agent_docs/reports/test_2.3.1_fix_rounds.md` (NEW — Russian summary + PASS/FAIL table)
> **Note:** `tester_2.3.1_fix.md` covers **E2E infra repair only** — do not overwrite; this file covers **F1–F12 product fix**.
> **Strategy:** Vitest unit + backend pytest + targeted Playwright + manual status checklist. **Do not modify** `src/` unless new blocker.

---

## 1. Objective

Verify Stage **2.3.1 fix** closes supervisor confusion around round statuses, corrects **24h deadline rule**, restores **pre-deadline match editing**, and gates **public leaderboard** to `PUBLISHED` only.

| ID | Coder | Area | Summary |
|----|-------|------|---------|
| **F1** | §2 | Status glossary | Hints per round status; `CLOSED` → «Дедлайн» |
| **F2** | §3 | 24h rule | Placement: `deadline < first_match`; lockout: change only while `now ≤ deadline − Nh` |
| **F3** | §4 | Match edit | ACTIVE + before deadline → structure editable |
| **F4** | §4.3 | Backend PATCH | Team swap blocked after deadline on ACTIVE |
| **F5** | §4.2 | Activate modal | Copy: editable until deadline |
| **F6** | §9.4 | CLOSED panel | Distinct UI ≠ PUBLISHED/CALCULATED |
| **F7** | §9.3–9.5 | CALCULATED | Admin preview + «Опубликовать»; not public |
| **F8** | §10.1 | LockBanner | **Only** on `/admin/settings/*` |
| **F9** | §10.2 | Create tour CTA | «+ Создать тур» always beside selector |
| **F10** | §9.2 | DRAFT edit | «Редактировать» → pre-filled `RoundBuilderForm` |
| **F11** | §9.6 | PUBLISHED | «Отменить» → stub modal |
| **F12** | §9.9 | Public LB | `PUBLISHED` only for visitors/users; stub copy |

**Non-goals:**

- E2E fixture/bootstrap repair → `tester_2.3.1_fix.md`
- `/admin` → `/supervisor` rename → `tester_1.13_supervisor_rename.md`
- Full public tabbed leaderboard polish → `tester_2.4.md`
- Real newsletter send → Stage 3

---

## 2. Test environment

### 2.1 Manual dev profile (full status matrix)

Requires **1.14 finalize** on contest `id=1`:

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

| Round | Status | Use for manual §8 |
|-------|--------|-------------------|
| 1–9 | `PUBLISHED` | `[UI-ROUND-PUBLISHED]` |
| 10 | `CALCULATED` | `[UI-ROUND-CALCULATED]`, `[API-LB-PUBLISHED-ONLY]` |
| 11 | `CLOSED` | `[UI-ROUND-CLOSED]` |

If 1.14 not merged: use **fresh DRAFT contest** via API for CLOSED/CALCULATED/PUBLISHED pipeline (slower); note limitation in report.

### 2.2 Fresh DRAFT profile (24h, ACTIVE edit, create tour)

E2E `beforeEach` via `adminApi.ts` — avoids mutating loaded contest `id=1`. Used for:

- `[E2E-SUPERVISOR-24H]` (updated lockout semantics)
- `[E2E-SUPERVISOR-ACTIVE-PRE-DEADLINE]` (structure edit before deadline)
- `[E2E-SUPERVISOR-CREATE-ROUND]` (create tour CTA)

### 2.3 E2E loaded profile (`--e2e`)

For specs still expecting round 10 **ACTIVE**:

```bash
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
```

Do **not** use for CALCULATED/CLOSED manual checks on round 10/11.

### 2.4 Frontend env

`frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
E2E_SUPERVISOR_PASSWORD=<matches SEED_SUPERVISOR_PASSWORD>
E2E_ADMIN_PASSWORD=<matches SEED_ADMIN_PASSWORD>
```

### 2.5 Credentials

| Role | Login | Password |
|------|-------|----------|
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` |
| USER | `user` | `user` |

---

## 3. Scope — files you may create/modify

```
frontend/src/lib/admin/deadlineRule.test.ts              # extend if Coder gaps
frontend/src/lib/admin/deriveAdminUiMode.test.ts         # extend
frontend/src/lib/contest/roundPublicVisibility.test.ts   # NEW if Coder adds helper
tests/api/test_leaderboard_published_only_2_3_1.py     # NEW — public vs supervisor CALCULATED
frontend/e2e/supervisor_round_status_panels.spec.ts      # NEW
frontend/e2e/supervisor_public_lb_gate.spec.ts           # NEW
frontend/e2e/supervisor_24h_rule.spec.ts                 # UPDATE — lockout semantics
frontend/e2e/supervisor_active_round.spec.ts             # UPDATE — pre-deadline edit
frontend/e2e/supervisor_create_round.spec.ts             # UPDATE — create tour CTA
frontend/e2e/admin_setup_locked.spec.ts                  # UPDATE — LockBanner scope
agent_docs/reports/test_2.3.1_fix_rounds.md              # NEW
```

**Do NOT modify:** `docs/`, `src/` (bugs → `BLOCKED.md`).

---

## 4. Unit tests (Vitest) — mandatory

```bash
cd frontend && npm run test:unit
```

### 4.1 `[UNIT-DEADLINE-PLACEMENT]` — `deadlineRule.ts`

| Case | Assert |
|------|--------|
| First match in 2h, deadline in 1h | **Valid** (`isDeadlineValid` true) |
| Deadline after first match | **Invalid** — «Дедлайн должен быть раньше первого матча тура» |
| Deadline in the past | **Invalid** |
| First match in 5d, deadline in 2d | **Valid** — **no** requirement that first match ≥ 24h away |

### 4.2 `[UNIT-DEADLINE-LOCKOUT]` — `canChangeDeadline`

| Case | Assert |
|------|--------|
| `now` = deadline − 30h, rule 24h | **Can change** |
| `now` = deadline − 10h, rule 24h | **Cannot change** — lockout message |
| DRAFT round | Change allowed (no current deadline lockout) |

Maps to Coder §3.2 — 24h applies to **editing** deadline, not kickoff placement.

### 4.3 `[UNIT-UI-MODE-PRE-DEADLINE]` — `deriveAdminUiMode.ts`

| State | Assert |
|-------|--------|
| `ACTIVE` + `now < deadline` | `canEditRoundStructure === true` |
| `ACTIVE` + deadline passed | `canEditRoundStructure === false`, `canEditMatchStatusAndDate === true` |
| `DRAFT` | Full structure edit |
| `PAUSED` contest | `disableAllMutations` |

### 4.4 `[UNIT-UI-MODE-LOCK-BANNER]` — settings vs rounds

| Page context | `showSetupLockBanner` |
|--------------|----------------------|
| Settings parameters | `true` when `is_locked` |
| Rounds / Results | `false` |

### 4.5 `[UNIT-ROUND-PUBLIC-VISIBILITY]` — `roundPublicVisibility.ts`

```ts
isRoundPubliclyVisible("PUBLISHED") === true
isRoundPubliclyVisible("CALCULATED") === false
isRoundPubliclyVisible("CLOSED") === false
isRoundPubliclyVisible("ACTIVE") === false
```

### 4.6 `[UNIT-UI-MODE-CLOSED-CALC-PUBLISHED]` — read-only modes

| Status | Results entry on rounds page | Structure edit |
|--------|------------------------------|----------------|
| `CLOSED` | Stub / link buttons | false |
| `CALCULATED` | Preview + publish CTA | false |
| `PUBLISHED` | Read-only + «Отменить» stub | false |

---

## 5. Backend pytest — mandatory

```bash
cd /work/football_prog
uv run pytest tests/unit/test_services_1_2.py -v -k "24H or DL"
uv run pytest tests/integration/test_deadline_batch_1_2.py -v
uv run pytest tests/api/test_operational_gaps_1_4.py -v -k "24h or OP-24H"
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
uv run pytest tests/api/test_leaderboard_published_only_2_3_1.py -v   # NEW
```

### 5.1 `[API-DL-24H-PLACEMENT]` — updated `DL-24H-*` tags

In `test_services_1_2.py` / `test_deadline_batch_1_2.py`:

| Scenario | Expected |
|----------|----------|
| Create round: first match in 2h, deadline in 1h | **Accepted** |
| Deadline ≥ earliest match | **Rejected** |
| Old test: deadline == first_match − 24h as **placement** rule | **Removed or inverted** — placement only needs `deadline < earliest` |

Document which `DL-24H-*` tags Coder updated in report.

### 5.2 `[API-DL-24H-LOCKOUT]` — `DEADLINE_CHANGE_CLOSED`

PATCH deadline on ACTIVE round when `now > current_deadline − 24h` → **400**, `code == "DEADLINE_CHANGE_CLOSED"`.

PATCH when `now ≤ current_deadline − 24h` → **200**.

### 5.3 `[API-OP-24H-RULE]` — `test_operational_gaps_1_4.py`

`[OP-24H-RULE]` reflects new semantics (lockout, not placement).

### 5.4 `[API-PATCH-ACTIVE-TEAMS]` — F4

On ACTIVE round:

| `now` vs deadline | PATCH `team1_id` | Expected |
|-------------------|------------------|----------|
| Before deadline | swap teams | **200** |
| After deadline | swap teams | **400** ValidationError |
| After deadline | PATCH `date_time` / `status` only | **200** |

### 5.5 `[API-LB-PUBLISHED-ONLY]` — F12 (NEW tests)

| Endpoint | Auth | Round status | Expected |
|----------|------|--------------|----------|
| `GET …/rounds/{id}/leaderboard` | none / USER | `CALCULATED` | **403** `RESULTS_NOT_AVAILABLE` |
| Same | SUPERVISOR | `CALCULATED` | **200** (preview) |
| Same | none / USER | `PUBLISHED` | **200** |
| `GET …/leaderboard` (global) | public | mix 1–9 PUBLISHED, 10 CALCULATED | Totals **exclude** round 10 |
| `GET …/rounds/{id}/results` | USER | `CALCULATED` | **403** or stub per contract |
| After `POST …/publish` on round 10 | public | `PUBLISHED` | **200** |

Suggested file: `tests/api/test_leaderboard_published_only_2_3_1.py`.

### 5.6 Regression

```bash
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
uv run ruff check src/ tests/
uv run mypy src/
```

Close → calculate → publish pipeline must remain green.

---

## 6. E2E tests (Playwright) — mandatory

Real API. Both `:8000` and `:3000` up. Prefer fresh contest for mutating tests.

### 6.1 `[E2E-SUPERVISOR-24H]` — `supervisor_24h_rule.spec.ts` (UPDATE)

**Setup:** fresh DRAFT contest, teams, round with first match in **+2 hours**.

| Step | Expected |
|------|----------|
| Set deadline to **+1 hour** (before first match) | **Save enabled** — create/activate succeeds (placement OK) |
| Activate round | Round ACTIVE |
| With deadline in **+30 hours**, try move deadline to **+10 hours** from now | **Blocked** — inline error / disabled Save (lockout <24h before **current** deadline) |
| With deadline in **+48 hours**, move to **+36 hours** | **Succeeds** |
| After successful deadline PATCH | `NewsletterPromptModal` opens; dismiss — no newsletter API call |

**Invalid scenario is NO LONGER** «deadline within 24h of first match kickoff» for create — only lockout on **change**.

### 6.2 `[E2E-SUPERVISOR-ACTIVE-PRE-DEADLINE]` — `supervisor_active_round.spec.ts` (UPDATE/SPLIT)

**Setup:** ACTIVE round, `now < deadline` (fresh contest or E2E profile round 10).

| Step | Expected |
|------|----------|
| Team1/team2 selectors | **Enabled** |
| **+ Добавить матч** | Enabled (if under `matches_per_round` cap) |
| Change teams → Save | **Succeeds** |
| After deadline passed (API PATCH times) | Team selectors **disabled**; status/date still editable |

Tag supersedes old «structure frozen immediately on ACTIVE» assumption.

### 6.3 `[E2E-UI-ROUND-STATUS-PANELS]` — `supervisor_round_status_panels.spec.ts` (NEW)

**Setup:** loaded contest `id=1` with 1.14 fixture (or API-built states).

Login supervisor → `/admin/rounds`:

| Round | Tag | Assert |
|-------|-----|--------|
| 11 `CLOSED` | `[UI-ROUND-CLOSED]` | Badge «Дедлайн»; hint about ввод счетов; stub buttons «Просмотр прогнозов» / «Ввод результатов»; **no** «Применено» / CALCULATED preview |
| 10 `CALCULATED` | `[UI-ROUND-CALCULATED]` | Hint about проверка очков; preview table with «Предпросмотр» badge; **«Опубликовать»** visible |
| 9 `PUBLISHED` | `[UI-ROUND-PUBLISHED]` | «Применено»; **«Отменить»** opens stub «Будет реализовано…» |
| Any `DRAFT` | `[UI-ROUND-DRAFT]` | **«Редактировать»** opens pre-filled form (F10) |

### 6.4 `[E2E-UI-CREATE-TOUR-CTA]` — `supervisor_create_round.spec.ts` (UPDATE)

On `/admin/rounds` with existing tour selected:

1. **«+ Создать тур»** visible **beside** tour `<select>` (not hidden when draft exists elsewhere).
2. When `hasDraft` → button **disabled** + tooltip «Сначала активируйте…».
3. When at `total_rounds` cap → disabled + cap tooltip.
4. When enabled → focuses/opens `RoundBuilderForm`.

### 6.5 `[E2E-UI-LOCK-BANNER-SCOPE]` — `admin_setup_locked.spec.ts` (UPDATE)

| Route | `LockBanner` |
|-------|--------------|
| `/admin/settings/parameters` | **Visible** when `is_locked` |
| `/admin/rounds` | **Absent** |
| `/admin/results` | **Absent** |

Contest pause banner may still appear — distinct from setup LockBanner.

### 6.6 `[E2E-UI-PUBLIC-LB-GATE]` — `supervisor_public_lb_gate.spec.ts` (NEW)

**Setup:** contest `id=1`, round 10 `CALCULATED` (1.14).

| Audience | Page | Round 10 | Expected |
|----------|------|----------|----------|
| Visitor / USER | Public leaderboard or results stub | 10 | Text «Будет доступно после проверки организатором»; **no** standings table for tour 10 |
| Same | Global LB | — | Points reflect tours 1–9 only (no tour 10 totals) |
| After publish round 10 via API/UI | Public | 10 | Standings appear |

Optional: network assert — no `GET …/leaderboard` for non-PUBLISHED round on public pages.

### 6.7 `[E2E-ACTIVATE-MODAL-COPY]` — F5

Activate confirm dialog contains «До дедлайна можно менять состав матчей» (or Coder's exact copy) — **not** «структура запрещена навсегда».

---

## 7. Manual checklist — `/admin/rounds` per status

Human developer verification (agent **reminds** in report; not required for automated `TEST_PASS`):

> Разработчик должен вручную проверить на contest `id=1` (после 1.14):

- [ ] **DRAFT** — «Редактировать», «Активировать»; sidebar hint
- [ ] **ACTIVE** — editor + deadline; hint «участники делают прогнозы»; before deadline: teams editable
- [ ] **CLOSED** (тур 11) — «Дедлайн» label; match list read-only; «Идёт» for live SCHEDULED; stub buttons
- [ ] **CALCULATED** (тур 10) — preview table; «Опубликовать»; public pages **do not** show tour 10
- [ ] **PUBLISHED** (тур 9) — «Применено»; «Отменить» stub
- [ ] **«+ Создать тур»** always visible; disabled states + tooltips
- [ ] **LockBanner** only on settings tabs
- [ ] **F1** — no confusion between contest `DRAFT` and round `DRAFT` in copy

Tag in report: `Manual checklist | REMINDER`.

---

## 8. Documentation audit (read-only)

| ID | Check |
|----|-------|
| `[DOC-CONTRACT-LIFECYCLE]` | `agent_docs/contracts/contest_lifecycle_flow.md` — §3.5 deadline rules + §3.3 public LB |
| `[DOC-API-YAML]` | `agent_docs/contracts/api_v1.yaml` — `DEADLINE_CHANGE_CLOSED`, public LB |
| `[DOC-FRONT-INTEGRATION]` | `agent_docs/contracts/frontend_api_integration.md` — deadline UX, LB gate |
| `[DOC-STATUS-REF]` | `manuals/STATUS_REFERENCE.md` — `CLOSED` → «Дедлайн»; visibility table |

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

> **User requirement.** Reference: `tester_2.1.md` §2.5.

After **EVERY** E2E run (pass or fail), before manual dev stack, `dev_setup --run-only`, or handoff:

### 10.1 Execution steps

1. Confirm `npm run test:e2e` / `playwright test` process **fully exited** — no background workers.
2. Run port check:

```bash
cd /work/football_prog
uv run python src/scripts/dev_setup.py --check-ports
```

→ **Must exit 0.** Both `:8000` and `:3000` free.

3. If ports busy:

```bash
ss -lntp | grep -E ':3000|:8000'
pkill -f "next dev" 2>/dev/null || true
pkill -f "chromium.*headless" 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
uv run python src/scripts/dev_setup.py --check-ports
```

4. Re-run until exit 0.
5. **Do not** run `dev_setup --run-only` while Playwright owns `:3000` or stray `uvicorn` holds `:8000`.

### 10.2 Local vs CI

| Environment | Note |
|-------------|------|
| **CI** | `CI=1` → `reuseExistingServer: false`; webServer stops on clean exit |
| **Local** | `reuseExistingServer: !process.env.CI` — **still** run §10.1 after E2E if process killed abruptly |

### 10.3 Optional improvements (document in report)

- `playwright.config.ts` `globalTeardown` hook calling `--check-ports`
- `frontend/e2e/README.md` teardown section

### 10.4 Report tag

| Tag | Pass criteria |
|-----|---------------|
| `[E2E-TEARDOWN]` | `--check-ports` exit 0; no orphan `next dev` / headless Chromium on `:3000` |

**Execution order:** E2E → `check-ports` → kill orphans if needed → **only then** handoff.

---

## 11. Execution order

```bash
# 1. Backend unit/integration (24h)
uv run pytest tests/unit/test_services_1_2.py tests/integration/test_deadline_batch_1_2.py -v -k "24H or DL"
uv run pytest tests/api/test_operational_gaps_1_4.py -v -k "24h or OP-24H"

# 2. API LB gate + regression
uv run pytest tests/api/test_leaderboard_published_only_2_3_1.py \
  tests/api/test_calculate_leaderboard_1_4.py -v

# 3. Python lint
uv run ruff check src/ tests/
uv run mypy src/

# 4. Frontend unit
cd frontend && npm run test:unit

# 5. Frontend lint
npm run lint && npm run type-check && npm run format:check

# 6. Bootstrap manual profile (1.14) + backend
cd /work/football_prog
uv run python src/scripts/load_test_data.py --reset
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/dev_setup.py --ensure-running-only
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# 7. E2E (frontend dir, :3000 via webServer)
cd frontend
npm run test:e2e -- supervisor_24h_rule.spec.ts supervisor_active_round.spec.ts \
  supervisor_round_status_panels.spec.ts supervisor_public_lb_gate.spec.ts \
  supervisor_create_round.spec.ts admin_setup_locked.spec.ts

# 8. TEARDOWN — mandatory (§10)
cd /work/football_prog
uv run python src/scripts/dev_setup.py --check-ports

# 9. Build
cd frontend && npm run build

# 10. Doc audit §8 (read-only)
```

Prefer E2E order: **create_round → 24h → active_pre_deadline → status_panels → public_lb_gate → lock_banner**.

---

## 12. Report template — `agent_docs/reports/test_2.3.1_fix_rounds.md`

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-DEADLINE-PLACEMENT]` | PASS/FAIL | |
| `[UNIT-DEADLINE-LOCKOUT]` | PASS/FAIL | |
| `[UNIT-UI-MODE-PRE-DEADLINE]` | PASS/FAIL | |
| `[UNIT-UI-MODE-LOCK-BANNER]` | PASS/FAIL | |
| `[UNIT-ROUND-PUBLIC-VISIBILITY]` | PASS/FAIL | |
| `[API-DL-24H-PLACEMENT]` | PASS/FAIL | |
| `[API-DL-24H-LOCKOUT]` | PASS/FAIL | |
| `[API-OP-24H-RULE]` | PASS/FAIL | |
| `[API-PATCH-ACTIVE-TEAMS]` | PASS/FAIL | |
| `[API-LB-PUBLISHED-ONLY]` | PASS/FAIL | |
| `[E2E-SUPERVISOR-24H]` | PASS/FAIL | lockout scenario |
| `[E2E-SUPERVISOR-ACTIVE-PRE-DEADLINE]` | PASS/FAIL | |
| `[UI-ROUND-CLOSED]` | PASS/FAIL | round 11 |
| `[UI-ROUND-CALCULATED]` | PASS/FAIL | round 10 |
| `[UI-ROUND-PUBLISHED]` | PASS/FAIL | round 9 |
| `[UI-ROUND-DRAFT]` | PASS/FAIL | |
| `[UI-CREATE-TOUR-CTA]` | PASS/FAIL | |
| `[UI-LOCK-BANNER-SCOPE]` | PASS/FAIL | |
| `[UI-PUBLIC-LB-GATE]` | PASS/FAIL | stub copy |
| `[E2E-ACTIVATE-MODAL-COPY]` | PASS/FAIL | |
| `[E2E-TEARDOWN]` | PASS/FAIL | §10 — **mandatory** |
| `[LINT-ESLINT]` | PASS/FAIL | |
| `[LINT-TSC]` | PASS/FAIL | |
| `[LINT-PRETTIER]` | PASS/FAIL | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Manual checklist | REMINDER | §7 |
| 1.14 fixture used | Y/N | |
| BLOCKED.md | OK / NEW | F3b if add-match deferred |

**Verdict:** `TEST_PASS` / `TEST_FAIL` with blockers for @Coder.

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3.1 fix rounds)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.3.1_fix_rounds.md
- Unit: N passed; API: M passed; E2E: K passed
- 24h rule: placement vs lockout verified
- Public LB: PUBLISHED-only confirmed
- E2E teardown: [E2E-TEARDOWN] PASS
- Next: coder_2.4.md / tester_2.4.md
```

---

## 13. Acceptance mapping (Coder §13 + §14)

| Criterion | Test ID |
|-----------|---------|
| F1 — hints per status; contest vs round DRAFT | `[UI-ROUND-*]`, manual §7 |
| F2 — create with match in ~2h; lockout on change | `[UNIT-DEADLINE-*]`, `[API-DL-24H-*]`, `[E2E-SUPERVISOR-24H]` |
| F3 — ACTIVE structure edit before deadline | `[UNIT-UI-MODE-PRE-DEADLINE]`, `[E2E-SUPERVISOR-ACTIVE-PRE-DEADLINE]` |
| F4 — API blocks team PATCH after deadline | `[API-PATCH-ACTIVE-TEAMS]` |
| F5 — activate modal copy | `[E2E-ACTIVATE-MODAL-COPY]` |
| F6 — CLOSED panel distinct | `[UI-ROUND-CLOSED]` |
| F7 — CALCULATED preview + publish | `[UI-ROUND-CALCULATED]` |
| F8 — LockBanner settings only | `[UI-LOCK-BANNER-SCOPE]`, `[UNIT-UI-MODE-LOCK-BANNER]` |
| F9 — create tour CTA always visible | `[UI-CREATE-TOUR-CTA]` |
| F10 — DRAFT «Редактировать» | `[UI-ROUND-DRAFT]` |
| F11 — PUBLISHED «Отменить» stub | `[UI-ROUND-PUBLISHED]` |
| F12 — public LB PUBLISHED only | `[API-LB-PUBLISHED-ONLY]`, `[UI-PUBLIC-LB-GATE]`, `[UNIT-ROUND-PUBLIC-VISIBILITY]` |
| Contracts updated | `[DOC-*]` |
| No regression close→calculate→publish | `[API-LB-PUBLISHED-ONLY]` + `test_calculate_leaderboard_1_4.py` |
| E2E teardown | `[E2E-TEARDOWN]` |

---

## 14. Relationship to other instructions

| File | Scope |
|------|-------|
| `tester_2.3.1_fix.md` | E2E infra (T1–T9) — **do not merge into this file** |
| `tester_1.14_data_fix.md` | Dev fixture — **recommended TEST_PASS** before §6.3 manual matrix |
| `tester_2.3.md` | Parent 2.3 matrix — retest after both 2.3.1 fixes green |

**Recommended order:** `tester_1.14_data_fix` → `coder_2.3.1` → `tester_2.3.1_fix_rounds` (this file).

---

## 15. Explicitly OUT OF SCOPE

- E2E bootstrap/password fixes → `tester_2.3.1_fix.md`
- Dev fixture SQL → `tester_1.14_data_fix.md`
- Full 2.3 E2E re-run (17 specs) unless regressions found — spot-check + new specs sufficient if infra already green
- `toHaveScreenshot()` vs `docs/screens/`
- Add/remove match on ACTIVE (F3b) — if deferred, note in `BLOCKED.md`, not silent skip
