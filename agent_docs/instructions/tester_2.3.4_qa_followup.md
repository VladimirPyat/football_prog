# Tester Instructions — Stage 2.3.4 QA Follow-up (Supervisor chat fixes)

> **Status gate:** @Coder `READY_FOR_TEST` for 2.3.4 QA follow-up (+ backend `coder_1.15_qa_followup.md` for **T8–T11**).
> **Coder spec:** `agent_docs/instructions/coder_2.3.4_qa_followup.md`
> **Backend spec:** `agent_docs/instructions/backend/coder_1.15_qa_followup.md` (required for **T8–T11**)
> **Prerequisite:** Stage **2.3.3** at `TEST_PASS` (`tester_2.3.3_fix_setup.md`); migrations `f7a8b9c0d1e2`, `g8h9i0j1k2l3` applied.
> **Report:** `agent_docs/reports/test_2.3.4_qa_followup.md` (NEW — Russian summary + PASS/FAIL table)
> **Manual checklist:** `manuals/SUPERVISOR_TESTING_SCENARIOS.md` — rows **S1.2**, **S1.12**, **S2.23**; dev workflow **S1.11** (`list-pending`)
> **Strategy:** Vitest unit + backend pytest (1.15 QA follow-up) + Playwright E2E + manual setup/tours walkthrough. **Do not modify** `src/` unless new blocker → `BLOCKED.md`.

---

## 1. Objective

Verify Stage **2.3.4** chat-driven fixes: **rules persistence**, **start readiness UI**, **ДопТур labels**, **`bonuses_pending` notes**, **contest context refresh** — on top of 2.3.3 baseline.

| ID | Coder | QA ref | Area | Summary |
|----|-------|--------|------|---------|
| **T1** | §2 | S1.2 | Contest context | Fresh DRAFT editable after create/switch; **no** debug bar `contestId=…` |
| **T2** | §3 | S1.2 | Rules editor | Structured rules on Parameters; PATCH `rules_json`; persist on save |
| **T3** | §3.3 | S1.12 | Auto-save before start | Unsaved rules/params flushed → then `POST /start` |
| **T4** | §4 | S1.12 | Start readiness UI | Panel «Команды X из Y» + «Принятые N»; button disabled until ready |
| **T5** | §7 | S1.12 | Setup refresh | Adding team/participant updates readiness without reload |
| **T6** | §8 | S1.2 / S1.4 | Rules after start | Rules section readonly structured view (not empty stub) |
| **T7** | §5 | S2.23 | ДопТур labels | UI shows **ДопТурN (из тура X)** not generic «Тур N» |
| **T8** | §6 | Scoring UX | Bonuses pending note | Callout on results/LB when API `bonuses_pending=true` |
| **T9** | 1.15 QA §3 | S1.12 | API start guards | 422 when teams incomplete or &lt;2 ACCEPTED |
| **T10** | 1.15 QA §4 | S1.11 | `list-pending` | Dev script lists pending invites; env password works |
| **T11** | 1.15 QA §6 | S2.23 | Supplementary API | `kind`, `supplementary_index`, `source_round_numbers` on rounds |
| **T12** | 1.15 QA §7 | Scoring | `bonuses_pending` API | Leaderboard returns flag + Russian message when postponed pending |

**Non-goals:**

- Full 2.3.3 regression re-run (spot-check `[E2E-ADMIN-START]` only if touched)
- Scoring engine deferred bonus2/3 recalc (contract only — API flag + UI note)
- `/admin` → `/supervisor` rename
- Hard purge cron (`purge_deleted_contests.py`) — ops smoke optional

---

## 2. Test environment

### 2.0 E2E prerequisites (READ FIRST)

Same as `tester_2.3.3_fix_setup.md` §2.0. **Additionally:**

```bash
cd /work/football_prog
uv run alembic upgrade head   # f7 soft-delete, g8 supplementary rounds
uv run python src/scripts/dev_setup.py --run-only
```

| Симптом | Причина | Решение |
|---------|---------|---------|
| Start 422 «команды» / «участники» | Readiness guard (expected) | `fulfillStartPrerequisites()` in E2E or manual setup |
| Start button disabled, no panel | Frontend 2.3.4 not deployed | `coder_2.3.4_qa_followup.md` |
| Rounds without `kind` / `source_round_numbers` | Migration g8 not applied | `alembic upgrade head` |
| `list-pending` empty | No PENDING invites | Invite via UI first |
| Parameters still locked on new contest | Stale ContestProvider cache | T1 — file bug if reproduces after fix |

**Корневой `.env`:**

```bash
SEED_SUPERVISOR_PASSWORD=…
SEED_ADMIN_PASSWORD=…
```

**Frontend** (`frontend/.env.local`): `NEXT_PUBLIC_API_URL`, `E2E_SUPERVISOR_PASSWORD` — match root `.env`.

### 2.1 Profiles

| Profile | Use for |
|---------|---------|
| **Fresh DRAFT** | T1–T6, T9 — `createDraftContest` + `fulfillStartPrerequisites` |
| **Loaded `id=1` RUNNING** | T7–T8, T11–T12 — rounds 10+, postponed matches, supplementary tours |
| **DRAFT incomplete** | T4, T9 — deliberately skip teams/participants |

Do **not** mutate contest `id=1` for setup-only tests (T1–T6).

### 2.2 Credentials

| Role | Login | Password |
|------|-------|----------|
| SUPERVISOR | `supervisor` | `SEED_SUPERVISOR_PASSWORD` |
| ADMIN | `admin` | `SEED_ADMIN_PASSWORD` |

---

## 3. Scope — files you may create/modify

```
frontend/src/lib/admin/rulesEditor.test.ts              # extend if gaps (T2)
frontend/src/lib/admin/contestStartReadiness.test.ts    # run (T4)
frontend/src/lib/admin/roundLabel.test.ts               # run (T7)
frontend/src/lib/admin/roundScoringPending.test.ts      # run (T8)
frontend/e2e/admin_setup.spec.ts                        # readiness + prerequisites (T3–T4)
frontend/e2e/supervisor_free_tour.spec.ts               # extend — ДопТур label (T7)
frontend/e2e/fixtures/adminApi.ts                       # fulfillStartPrerequisites helpers
agent_docs/reports/test_2.3.4_qa_followup.md            # NEW
manuals/SUPERVISOR_TESTING_SCENARIOS.md                 # verify S1.2 / S2.23 status column
```

**Do NOT modify:** `docs/`, `src/` (bugs → `agent_docs/reports/BLOCKED.md`).

---

## 4. Unit tests (Vitest) — mandatory

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Focus files (must be green):

```bash
cd frontend && npm run test:unit -- \
  src/lib/admin/rulesEditor.test.ts \
  src/lib/admin/contestStartReadiness.test.ts \
  src/lib/admin/roundLabel.test.ts \
  src/lib/admin/roundScoringPending.test.ts
```

### 4.1 `[UNIT-RULES-EDITOR]` — T2

| Case | Assert |
|------|--------|
| Default form state | `buildRulesJsonPatch` returns valid partial `rules_json` |
| Changed bonus fields | Patch includes only changed keys |
| Round-trip | Parsed values match form after load |

### 4.2 `[UNIT-START-READINESS]` — T4

| teams | required | accepted | `canStart` |
|-------|----------|----------|------------|
| 0 | 8 | 0 | `false` |
| 8 | 8 | 0 | `false` |
| 8 | 8 | 1 | `false` |
| 8 | 8 | 2 | `true` |
| 6 | 8 | 2 | `false` |

`blockers` array non-empty when `!canStart`; messages in Russian.

### 4.3 `[UNIT-ROUND-LABEL]` — T7

| `kind` | `number` | `supplementary_index` | `source_round_numbers` | Expected title fragment |
|--------|----------|----------------------|------------------------|-------------------------|
| `REGULAR` | 3 | — | — | `Тур 3` |
| `SUPPLEMENTARY` | 12 | 1 | `[2]` | `ДопТур1` + `из тура 2` |

`formatRoundOptionLabel` includes status suffix (e.g. «Черновик»).

### 4.4 `[UNIT-BONUSES-PENDING-UI]` — T8

| Case | Assert |
|------|--------|
| `roundHasVisiblePostponements` with POSTPONED | `true` |
| Only FINISHED + CANCELED | `false` |

(API-driven callout text — manual or E2E on fixture contest.)

### 4.5 Regression

`deriveAdminUiMode.test.ts`, `admin.test.ts` schema tests — no regressions vs 2.3.3.

---

## 5. Backend pytest — mandatory when 1.15 QA follow-up merged

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run pytest tests/api/test_contest_start_1_15.py -v -k "TEAMS or PARTICIPANTS or READY or rules"
uv run pytest tests/api/test_contest_soft_delete.py -v
uv run pytest tests/api/test_dev_invite_setup.py -v
uv run pytest tests/api/test_free_tour_1_4.py -v
uv run pytest tests/services/test_round_scoring_pending.py -v
```

If readiness tests missing → **BLOCKER** for T9; mark `TEST_FAIL` with note «backend 1.15 QA follow-up not shipped».

### 5.1 `[API-START-TEAMS]` — T9

| Step | Expected |
|------|----------|
| DRAFT contest, `total_teams=8`, create 0 teams | — |
| `POST /contests/{id}/start` | **422**, detail mentions «команды» / «создано 0 из 8» |
| Add 8 teams, 0 participants | `POST …/start` → **422** «минимум 2 принятых участника» |
| `fulfill_start_prerequisites` helper | 200 start |

### 5.2 `[API-LIST-PENDING]` — T10

| Step | Expected |
|------|----------|
| Invite 1 participant → PENDING | — |
| `uv run python src/scripts/dev_invite_setup.py list-pending --contest-id {id}` | stdout shows contest id + pending row |
| `confirm-all --contest-id {id}` **without** `--password` | Uses `SEED_SUPERVISOR_PASSWORD` from `.env` |

### 5.3 `[API-SUPPLEMENTARY-META]` — T11

| Step | Expected |
|------|----------|
| POSTPONED match in round N → `POST …/free-tour` | 201 |
| `GET /contests/{id}/rounds` | New round: `kind=SUPPLEMENTARY`, `supplementary_index>=1` |
| Same response | `source_round_numbers` contains origin round number |

### 5.4 `[API-BONUSES-PENDING]` — T12

| Step | Expected |
|------|----------|
| Origin round with FINISHED main matches + POSTPONED (or match in ДопТур) | — |
| `GET …/rounds/{origin_id}/leaderboard` (or contracted LB endpoint) | `bonuses_pending=true`, `bonuses_pending_message` non-null Russian |
| All logical-tour matches FINISHED | `bonuses_pending=false` |

See `tests/services/test_round_scoring_pending.py` for matrix.

---

## 6. E2E tests (Playwright) — mandatory

**API `:8000` running.** Migrations applied.

```bash
cd frontend
npm run test:e2e -- e2e/admin_setup.spec.ts e2e/supervisor_free_tour.spec.ts --reporter=line
```

### 6.1 `[E2E-CONTEST-CONTEXT]` — T1

**Setup:** supervisor session.

| Step | Expected |
|------|----------|
| Create new contest via modal | Picker switches to new id |
| `/admin/settings/parameters` | Fields **editable** (not locked like `id=1`) |
| Page source / UI | **No** debug strip with `contestId=` |
| Switch picker back to `id=1` | LockBanner + disabled fields |

### 6.2 `[E2E-RULES-SAVE]` — T2

**Setup:** fresh DRAFT, unlocked.

| Step | Expected |
|------|----------|
| Parameters → rules section | Structured fields visible (not one-line stub) |
| Change a bonus field → «Сохранить параметры» | Toast success |
| Reload page | Value persisted |

### 6.3 `[E2E-START-READINESS]` — T4, T5

**Setup:** fresh DRAFT, **without** `fulfillStartPrerequisites`.

| Step | Expected |
|------|----------|
| Parameters bottom | Readiness panel: teams/participants counts |
| «Запустить конкурс» | **disabled** |
| Add teams via API or UI until full | Panel updates (T5 — no full reload) |
| Invite + confirm 2 participants | Panel shows «Принято» ≥2; button **enabled** |

### 6.4 `[E2E-ADMIN-START]` — T3, T6 (extend 2.3.3)

**Setup:** fresh DRAFT; call `fulfillStartPrerequisites(token, contestId)` before UI start (as in current `admin_setup.spec.ts`).

| Step | Expected |
|------|----------|
| Change rules without explicit save | Click start → auto-save then start succeeds |
| After start | Rules readonly; structural fields locked (S1.4) |

### 6.5 `[E2E-FREE-TOUR-LABEL]` — T7

**Setup:** loaded contest `id=1`, round 10 ACTIVE, one match POSTPONED (see `supervisor_free_tour.spec.ts`).

| Step | Expected |
|------|----------|
| Create free tour from postponed match | Success |
| Round selector / tours page | New entry shows **ДопТур1** (or N), not only «Тур 11» |
| Label includes source | «из тура 10» (or actual origin number) |

Extend existing spec if label assertion missing.

### 6.6 `[E2E-BONUSES-PENDING-NOTE]` — T8

**Setup:** fixture contest with postponed logical tour (manual prep or extend free-tour flow).

| Step | Expected |
|------|----------|
| `/admin/results` select origin round | Info note about deferred bonuses (when API flag set) |
| Round LB preview (if visible) | Same or similar message |

**SKIP** with note if fixture cannot produce `bonuses_pending=true` without heavy setup — cover via **T12** API + manual.

---

## 7. Manual checklist — `SUPERVISOR_TESTING_SCENARIOS.md`

Route A extension (~20 min after 2.3.3):

| ID | Steps | Pass criteria |
|----|-------|---------------|
| **S1.2** | Parameters: edit rules + structure; save; create new contest → editable | Rules not stub; no stale lock |
| **S1.11** | `list-pending` → `confirm-all` (no `--password` if `.env` set) | Script output + «Принято» in UI |
| **S1.12** | Try start with incomplete teams → blocked; complete → start | Panel + disabled button; then success |
| **S2.23** | Postpone match → free tour → check labels on Tours + Results | **ДопТурN (из тура X)** |

Update **Статус** column with date + `test_2.3.4_qa_followup.md` link.

### 7.1 S1.11 — `list-pending` workflow (LOCKED)

```bash
# 1. UI: invite 2 participants on DRAFT → «Ожидает»
uv run python src/scripts/dev_invite_setup.py list-pending --contest-id <ID>

# 2. Bulk confirm (password from .env):
uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id <ID>

# 3. Reload participants → «Принято»; readiness panel shows ≥2
```

### 7.2 Dev setup cheatsheet (smoke)

After `dev_setup.py` (full or `--run-only`), terminal prints QA cheatsheet with invite commands and migration hint — **visual smoke** only.

---

## 8. Lint & build

```bash
cd frontend && npm run lint && npm run type-check && npm run format:check
cd frontend && npm run build
```

Backend (if QA follow-up touched):

```bash
uv run ruff check src/services/contest_lifecycle_service.py src/services/round_scoring_pending.py src/services/round_serialization.py
uv run pytest tests/test_linting.py -q
```

---

## 9. Documentation verification

| ID | File | Check |
|----|------|-------|
| `[DOC-SCENARIOS]` | `manuals/SUPERVISOR_TESTING_SCENARIOS.md` | S1.2 rules; S2.23 ДопТур; S1.11 `list-pending` |
| `[DOC-DEV]` | `manuals/DEV_SETUP.md` | Workflow B + cheatsheet mention |
| `[DOC-SCORING]` | `agent_docs/contracts/scoring_flow.md` §6 | Logical tour + deferred bonuses |
| `[DOC-API]` | `agent_docs/contracts/api_v1.yaml` | `bonuses_pending` on leaderboard schema |

---

## 10. Report template

Create `agent_docs/reports/test_2.3.4_qa_followup.md`:

```markdown
# Test Report — Stage 2.3.4 QA Follow-up

**Date:** YYYY-MM-DD
**Coder:** coder_2.3.4_qa_followup.md (+ backend/coder_1.15_qa_followup.md)
**Tester instruction:** tester_2.3.4_qa_followup.md
**Environment:** API :8000, UI :3000; `alembic upgrade head` applied

## Summary
(2–4 предложения на русском)

## Results

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-RULES-EDITOR]` | PASS/FAIL | |
| `[UNIT-START-READINESS]` | PASS/FAIL | |
| `[UNIT-ROUND-LABEL]` | PASS/FAIL | |
| `[UNIT-BONUSES-PENDING-UI]` | PASS/FAIL | |
| `[API-START-TEAMS]` | PASS/FAIL/SKIP | |
| `[API-LIST-PENDING]` | PASS/FAIL/SKIP | |
| `[API-SUPPLEMENTARY-META]` | PASS/FAIL/SKIP | |
| `[API-BONUSES-PENDING]` | PASS/FAIL/SKIP | |
| `[E2E-CONTEST-CONTEXT]` | PASS/FAIL | |
| `[E2E-RULES-SAVE]` | PASS/FAIL | |
| `[E2E-START-READINESS]` | PASS/FAIL | |
| `[E2E-ADMIN-START]` | PASS/FAIL | |
| `[E2E-FREE-TOUR-LABEL]` | PASS/FAIL/SKIP | |
| `[E2E-BONUSES-PENDING-NOTE]` | PASS/FAIL/SKIP | |
| `[LINT-*]` / `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Manual S1.2, S1.11, S1.12, S2.23 | PASS/FAIL | |
| BLOCKED.md | OK / NEW | |

**Verdict:** TEST_PASS / TEST_FAIL
```

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.3.4 QA follow-up)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.3.4_qa_followup.md
- Unit: N passed; API: M passed; E2E: K passed
- Start readiness + rules persist verified (S1.2, S1.12)
- ДопТур labels + bonuses_pending: [OK / partial — note]
- Next: …
```

---

## 11. Acceptance mapping (Coder §10)

| Criterion | Test ID |
|-----------|---------|
| Fresh DRAFT editable; no debug bar | T1 → `[E2E-CONTEST-CONTEXT]` |
| Rules save + persist | T2 → `[UNIT-RULES-EDITOR]`, `[E2E-RULES-SAVE]` |
| Auto-save before start | T3 → `[E2E-ADMIN-START]` |
| Readiness panel + disabled start | T4 → `[UNIT-START-READINESS]`, `[E2E-START-READINESS]` |
| Setup change refreshes panel | T5 → `[E2E-START-READINESS]` |
| Rules readonly after start | T6 → `[E2E-ADMIN-START]` |
| ДопТур labels | T7 → `[UNIT-ROUND-LABEL]`, `[E2E-FREE-TOUR-LABEL]` |
| Bonuses pending UI | T8 → `[UNIT-BONUSES-PENDING-UI]`, `[E2E-BONUSES-PENDING-NOTE]`, `[API-BONUSES-PENDING]` |
| API start guards | T9 → `[API-START-TEAMS]` |
| `list-pending` + env password | T10 → `[API-LIST-PENDING]`, Manual §7.1 |
| Supplementary API metadata | T11 → `[API-SUPPLEMENTARY-META]` |

---

## 12. Execution order (full pipeline)

```text
1. backend/coder_1.15_qa_followup.md     → Coder (src/)
2. coder_2.3.4_qa_followup.md            → Coder (frontend/)
3. tester_2.3.4_qa_followup.md (this)    → §4 unit → §5 pytest → §6 E2E → §7 manual → §10 report
```

**Partial test** (frontend landed, backend QA follow-up pending):

- Run §4 + `[E2E-CONTEST-CONTEXT]`, `[E2E-RULES-SAVE]`, `[E2E-START-READINESS]` (UI only)
- Mark T9–T12, `[API-*]` as **SKIP — blocked on 1.15 QA follow-up**
- Verdict: `TEST_FAIL` or `PARTIAL` with blocker list

---

## 13. Relationship to other instructions

| File | Scope |
|------|-------|
| `coder_1.15_qa_followup.md` | Backend: readiness, supplementary, bonuses_pending, dev scripts |
| `coder_2.3.4_qa_followup.md` | Frontend spec |
| `tester_2.3.3_fix_setup.md` | Prerequisite (2.3.3 baseline) |
| `tester_2.3.2_fix_tours.md` | Tours/results regression (spot-check only) |
| `manuals/SUPERVISOR_TESTING_SCENARIOS.md` | Manual IDs |
| `manuals/DEV_SETUP.md` | S1.11, cheatsheet |

---

## 14. Explicitly OUT OF SCOPE

- Full 2.3.3 delete/restore/create-modal regression (already `TEST_PASS`)
- Scoring engine implementing deferred bonus2/3 on `calculate`
- Production SMTP invite delivery
- `purge_deleted_contests.py` scheduled job in CI
- Removing unused `RulesDisplayPanel.tsx` (optional Coder cleanup)
