# Test Report — Stage 2.2.1 (Visitor public predictions)

## Verdict: PASS (2.2.1 scope)

Re-verified 2026-07-08 as part of tester_2.2 full run. All 2.2.1 gates green.

## API

| ID | Result |
|----|--------|
| [API-PRED-VISITOR-PRE] | PASS — 403 `PREDICTIONS_NOT_PUBLIC` round 10, no token |
| [API-PRED-VISITOR-POST] | PASS — 200 full table round 9, no token |
| [API-PRED-VISITOR-POST-SHIM] | PASS — legacy GET `/api/v1/rounds/9/predictions` 200 |
| [API-PRED-USER-PRE] | PASS — `test_pred_privacy_before_and_after_deadline` no regression |
| [API-PRED-POST-AUTH] | PASS — POST without token → 401 |

Command: `uv run pytest tests/api/test_predictions_flow_1_3.py tests/api/test_predictions_public_1_16.py -v` → **9 passed**

## Frontend unit

| ID | Result |
|----|--------|
| [UNIT-PRIVACY-VISITOR-POST] | PASS |
| All 2.2 unit tests | PASS — 153/153 |

## E2E

| ID | Result |
|----|--------|
| [E2E-VISITOR-PRED-STUB] | PASS |
| [E2E-VISITOR-PRED-PUBLIC] | PASS |
| [E2E-PRED-PRIVACY-PRE] | PASS |
| [E2E-PRED-PRIVACY-POST] | PASS |
| [E2E-PRED-BATCH] | PASS |
| [E2E-USER-PREDICT-FLOW] | PASS |

## Lint & build

| Check | Result |
|-------|--------|
| `npm run lint` | PASS |
| `npm run type-check` | PASS |
| `npm run format:check` | PASS |
| `npm run build` | PASS |

## Docs

| ID | Result |
|----|--------|
| [DOC-INTEGRATION] | PASS — §5.4 public post-deadline |
| [DOC-LIFECYCLE] | PASS — §3.3 anonymous 403/200 |
| [DOC-UI-PAGES] | PASS — visitor matrix post-deadline |
| [DOC-NO-LOGIN-PROMPT] | PASS — `PredictionsLoginPrompt` absent |

## Notes

- **Backend 1.16:** GET predictions uses `OptionalUser`; anonymous pre-deadline → 403; post-deadline → 200 full table.
- **Frontend 2.2.1:** Visitor post-deadline shows `PredictionsMatrix` without login; deadline gate uses `isDeadlinePassedNow`.
- **Auth fixture fix (2026-07-08):** E2E login assertion uses `header-user-login` test id (header UX change since initial 2.2.1 report).
