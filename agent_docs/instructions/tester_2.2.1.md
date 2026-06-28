# Tester Instructions — Stage 2.2.1 Patch: Visitor Public Predictions

> **Status gate:** @Coder `READY_FOR_TEST` for **1.16 public predictions** + **2.2.1** in `agent_docs/progress/stage_2.md`
> **Type:** Patch on **2.2** — do **not** require edits to `tester_2.2.md`; use this doc + `tester_2.2.1.md` for delta only
> **Prerequisites:** `backend/coder_1.16_fix_public_predictions.md` + `coder_2.2.1.md` implemented
> **Reference:** `docs/03_user_scenarios.md` §4, `coder_2.2.1.md`, `tester_2.2.md` (env §2 — same stack)
> **Strategy:** API pytest delta + frontend unit + E2E + lint/build; report `agent_docs/reports/test_2.2.1.md`

---

## 1. Objective

Verify alignment with product spec: **Visitor sees full predictions table after deadline without registration**; **pre-deadline stub unchanged**.

| Area | What changed |
|------|----------------|
| API | Anonymous GET post-deadline → 200; pre-deadline → 403 |
| UI | Remove login prompt on Прогнозы post-deadline; public matrix |
| Regression | Authenticated privacy pre-deadline; POST still auth-required |

**Non-goals:** Re-run full 2.3 admin suite; visual QA of matrix layout (covered in 2.2).

---

## 2. Test environment

Same as `tester_2.2.md` §2:

```bash
# API
cd /work/football_prog
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Frontend tests
cd frontend && npm run test:unit && npm run test:e2e
```

| Round | Use |
|-------|-----|
| **10** | ACTIVE, deadline **future** — visitor **stub** |
| **9** | `PUBLISHED`, deadline **passed** — visitor **full matrix** |

---

## 3. Backend API (pytest)

Run:

```bash
uv run pytest tests/api/test_predictions_flow_1_3.py tests/api/test_predictions_public_1_16.py -v
```

(Adjust file name if Coder merged into single file.)

| ID | Case | Expected |
|----|------|----------|
| `[API-PRED-VISITOR-PRE]` | GET `/api/v1/contests/1/rounds/{10}/predictions` no `Authorization` | **403**, `code=PREDICTIONS_NOT_PUBLIC` |
| `[API-PRED-VISITOR-POST]` | GET same for round **9** | **200**, `deadline_passed=true`, scores visible in `entries` |
| `[API-PRED-VISITOR-POST-SHIM]` | Legacy `GET /api/v1/rounds/{9}/predictions` | **200** |
| `[API-PRED-USER-PRE]` | Existing USER privacy test | PASS (no regression) |
| `[API-PRED-POST-401]` | POST predictions no token | **401** |

Manual curl (optional):

```bash
curl -s "http://127.0.0.1:8000/api/v1/contests/1/rounds/9/predictions" | jq '.deadline_passed, .entries[0].predictions'
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/v1/contests/1/rounds/10/predictions"
# expect 200 with data / 403 respectively
```

---

## 4. Frontend unit (Vitest)

| ID | Spec | Expected |
|----|------|----------|
| `[UNIT-PRIVACY-VISITOR-POST]` | `shouldShowScore.test.ts` | PASS |
| All existing 2.2 unit tests | `npm run test:unit` | PASS (no regressions) |

---

## 5. E2E (Playwright)

### 5.1 Keep — `[E2E-VISITOR-PRED-STUB]`

File: `frontend/e2e/visitor_predictions_stub.spec.ts`

Unchanged intent:

- Guest on contest 1, round **10** (ACTIVE)
- Text **«Будет доступно после дедлайна»**
- `predictions-matrix` **not** visible

**Stability:** `beforeAll` → `ensureE2eActiveRound(1)`; select round 10 in `#round-select`.

### 5.2 NEW — `[E2E-VISITOR-PRED-PUBLIC]`

File: `frontend/e2e/visitor_predictions_public.spec.ts` (NEW)

```ts
test.describe("[E2E-VISITOR-PRED-PUBLIC]", () => {
  test("visitor sees full matrix after deadline without login", async ({ page }) => {
    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible();

    // Round 9 — PUBLISHED, deadline passed (fixture)
    await page.locator("#round-select").selectOption(/* round 9 id — resolve via API helper or constant from getRoundId(9) */);

    await expect(page.getByTestId("predictions-matrix")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Войдите, чтобы просмотреть прогнозы")).not.toBeVisible();
    // At least one numeric score cell visible (not only «Прогноз сделан» masks)
    await expect(page.locator("[data-testid='prediction-score']").first()).toBeVisible();
  });
});
```

**Implementation notes for Coder/Tester:**

- Add `getRoundIdByNumber(contestId, 9)` to `e2e/fixtures/predictionsApi.ts` if missing (mirror `getActiveRoundId`).
- Ensure `PredictionsMatrix` exposes `data-testid="prediction-score"` on visible score cells **or** assert on score pattern `\d+:\d+` in matrix — pick one stable selector; document in spec.

### 5.3 Regression spot-checks (subset)

From `tester_2.2.md` — run these after 2.2.1:

| ID | File | Why |
|----|------|-----|
| `[E2E-PRED-PRIVACY]` | `prediction_privacy.spec.ts` | USER pre-deadline mask |
| `[E2E-PRED-PRIVACY-POST]` | same | USER post-deadline full |
| `[E2E-USER-PREDICT]` | `user_predict_flow.spec.ts` | POST flow |

### 5.4 Full prediction E2E order

```bash
npm run test:e2e -- e2e/visitor_predictions_stub.spec.ts e2e/visitor_predictions_public.spec.ts e2e/prediction_privacy.spec.ts e2e/prediction_batch.spec.ts --reporter=line
```

Then full 2.2 suite if time permits.

**Suite pollution:** run `ensureE2eActiveRound` in `visitor_predictions_stub` `beforeAll` only; `visitor_predictions_public` uses round 9 — no conflict.

---

## 6. Lint & build

```bash
cd frontend
npm run lint && npm run type-check && npm run format:check && npm run build
```

Backend (touched files):

```bash
uv run ruff check src/
uv run mypy src/
```

---

## 7. Docs verification

| ID | Check |
|----|-------|
| `[DOC-INTEGRATION]` | `frontend_api_integration.md` §5.4 — visitor post-deadline **public GET**, no login prompt |
| `[DOC-LIFECYCLE]` | `contest_lifecycle_flow.md` §3.3 — anonymous 403/200 |
| `[DOC-UI-PAGES]` | `ui/pages.md` — visitor matrix post-deadline |
| `[DOC-NO-LOGIN-PROMPT]` | `PredictionsLoginPrompt.tsx` absent from `frontend/` (moved to `.trash/`); grep zero hits |

---

## 8. Report template

Create `agent_docs/reports/test_2.2.1.md`:

```markdown
# Test Report — Stage 2.2.1 (Visitor public predictions)

## Verdict: PASS | FAIL | BLOCKED

## API
| ID | Result |
|----|--------|
| [API-PRED-VISITOR-PRE] | |
| [API-PRED-VISITOR-POST] | |

## E2E
| ID | Result |
|----|--------|
| [E2E-VISITOR-PRED-STUB] | |
| [E2E-VISITOR-PRED-PUBLIC] | |

## Regression
- prediction_privacy: 
- user_predict_flow:

## Notes
```

Append to `agent_docs/progress/stage_2.md`:

```text
## YYYY-MM-DD — Tester (2.2.1)
- STATUS: TEST_PASS | TEST_FAIL
- Report: agent_docs/reports/test_2.2.1.md
```

---

## 9. Acceptance gates

| Gate | Command | Pass |
|------|---------|------|
| API visitor | pytest §3 | All green |
| Unit | `npm run test:unit` | Green |
| E2E stub + public | §5.1–5.2 | Both PASS |
| Privacy regression | §5.3 | PASS |
| Lint/build | §6 | PASS |
| Ports cleanup | `dev_setup.py --check-ports` | 0 |

---

## 10. Known issues (do not fail 2.2.1)

| ID | Note |
|----|------|
| `[ENV-LOADER-AUTH]` | `shutov/user` login still broken — unrelated |
| Demo `user/user` | Dev bootstrap only — not production |
| Sparse matrix on round 10 | Only users with prediction rows appear — OK |

---

## 11. Execution order

```text
1. Coder: backend/coder_1.16_fix_public_predictions.md
2. Coder: coder_2.2.1.md
3. Tester: tester_2.2.1.md (this)
```
