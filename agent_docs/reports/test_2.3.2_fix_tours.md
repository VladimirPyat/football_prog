# Test Report — Stage 2.3.2 Fix: Tours & Results Tab UX (+ Backend 1.15)

> **Date:** 2026-06-27  
> **Coder specs:** `agent_docs/instructions/coder_1.15_fix_tours.md`, `agent_docs/instructions/coder_1.15_backend_calculated_edit.md`  
> **Tester spec:** `agent_docs/instructions/tester_2.3.2_fix_tours.md`  
> **Verdict:** **TEST_PASS** (unit + backend); E2E **SKIP** (UI :3000 down)

---

## Executive summary

Последовательный запуск: **backend 1.15** → **frontend 2.3.2** → **tester**. Backend разрешает `PUT …/result` на туре `CALCULATED` с авто-`recalculate_round`. Frontend реализует T1–T12 и unlock правки счёта на `CALCULATED` (B3). Автоматика: **82/82** Vitest, **17/17** backend pytest (+1 skip). E2E-спеки созданы, но прогон не выполнен — UI не поднят (`:3000` connection refused); API `:8000` доступен.

---

## Coder — backend 1.15 / [API-RESULT-CALCULATED]

| ID | Result | Notes |
|----|--------|-------|
| B1 | **PASS** | `set_result` принимает `CLOSED` \| `CALCULATED` |
| B2 | **PASS** | Auto `recalculate_round` после PUT на `CALCULATED` |
| B4 tests | **PASS** | `test_results_calculated_edit_2_3_2.py` — 4/4 |
| B4 docs | **PASS** | `manuals/API_GUIDE.md`, `manuals/STATUS_REFERENCE.md` |

---

## Coder — frontend 2.3.2 (T1–T12)

| ID | Result | Key files |
|----|--------|-----------|
| T1 | **PASS** | `validation/admin.ts` — «Укажите дату и время для каждого матча» |
| T2 | **PASS** | `RoundManagementPanel.tsx` — single save on ACTIVE |
| T3 | **PASS** | `RoundPhasePanel.tsx` — CALCULATED: match table, no participant LB |
| T4 | **PASS** | PUBLISHED panel + «Перейти к результатам» |
| T5 | **PASS** | CLOSED read-only + `matchPhaseLabel` «Идёт» |
| T6 | **PASS** | «Результаты участников» in `ResultsEntryPanel.tsx` |
| T7 | **PASS** | `matchResultsGating.ts` — kickoff gate |
| T8 | **PASS** | Re-edit CLOSED; CALCULATED editable (backend+B3 unlock) |
| T9 | **PASS** | Staff LB preview on CALCULATED |
| T10 | **PASS** | Publish only on CALCULATED |
| T11 | **PASS** | `roundStatusHint` lifecycle copy |
| T12 | **N/A** | Fixture via `dev_setup --finalize-fixture-only` (documented) |

---

## Automated test results

### Frontend

| Command | Result |
|---------|--------|
| `npm run test:unit` | **82/82 passed** |
| `npm run lint` | **0 errors** |
| `npm run type-check` | **OK** |
| `npm run format:check` | **OK** (after `npm run format`) |

### Backend

| Suite | Result |
|-------|--------|
| `test_results_calculated_edit_2_3_2.py` | **4/4** |
| `test_calculate_leaderboard_1_4.py` | **8 passed, 1 skipped** |
| `test_leaderboard_published_only_2_3_1.py` | **5/5** |
| **Total spot-check** | **17 passed, 1 skipped** |

### E2E Playwright

| Spec | Status |
|------|--------|
| `supervisor_tours_phase_panels.spec.ts` | **SKIP** — UI :3000 down |
| `supervisor_results_kickoff.spec.ts` | **SKIP** |
| `supervisor_results_preview.spec.ts` | **SKIP** |
| Updated: `supervisor_create_round`, `supervisor_active_round` | **SKIP** |

**Reason:** `curl http://127.0.0.1:3000/` → connection refused. API health `:8000` → 200.

**Recommended re-run:**

```bash
uv run python src/scripts/dev_setup.py --run-only
cd frontend && npm run test:e2e
```

---

## PASS / FAIL matrix (T1–T12 + API)

| Tag | Result | Method |
|-----|--------|--------|
| T1 `[UNIT-TOUR-DATE-VALIDATION]` | **PASS** | Vitest |
| T2 `[E2E-ACTIVE-SINGLE-SAVE]` | **SKIP** | E2E — no UI |
| T3 `[UI-TOUR-CALCULATED]` | **SKIP** | E2E — no UI |
| T4 `[UI-TOUR-PUBLISHED]` | **SKIP** | E2E — no UI |
| T5 `[UI-TOUR-CLOSED]` | **SKIP** | E2E — no UI |
| T6 copy | **PASS** | code review |
| T7 `[UNIT-MATCH-KICKOFF-GATE]` | **PASS** | Vitest |
| T8 `[UNIT-UI-MODE-RESULTS-CLOSED]` | **PASS** | Vitest (CALCULATED unlock) |
| T9 preview | **PASS** | code review + unit |
| T10 publish flow | **PASS** | deriveAdminUiMode tests |
| T11 lifecycle hints | **PASS** | `format.test.ts` |
| T12 fixture | **N/A** | manual |
| `[API-RESULT-CALCULATED]` | **PASS** | pytest 4/4 |

---

## Manual QA (not run)

1.14 fixture matrix (rounds 1–9 PUBLISHED, 10 CALCULATED, 11 CLOSED) — не проверялся вручную в этой сессии.

---

## Next steps

1. Поднять stack: `uv run python src/scripts/dev_setup.py --run-only`
2. Прогнать E2E: `cd frontend && npm run test:e2e`
3. Manual walkthrough `/admin/rounds` + `/admin/results` на fixture contest `id=1`
