# Test Report — Stage 2.2.1 (Visitor public predictions)

## Verdict: PASS (2.2.1 scope)

Stage 2.2.1 acceptance gates passed. Full backend pytest suite reports 15 failures unrelated to predictions public access (contacts, me/contests, tiebreak, pre-existing).

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
| All 2.2 unit tests | PASS — 151/151 |

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
| `uv run ruff check` (touched files) | PASS |

## Regression (full suites)

| Suite | Result |
|-------|--------|
| Backend full pytest | 368 passed, **15 failed** (pre-existing: contacts, me/contests, tiebreak, auth temp password, etc.) |
| Frontend unit | 151 passed |

## Docs

| ID | Result |
|----|--------|
| [DOC-INTEGRATION] | PASS — §5.4 public post-deadline |
| [DOC-LIFECYCLE] | PASS — §3.3 anonymous 403/200 |
| [DOC-UI-PAGES] | PASS — visitor matrix post-deadline |
| [DOC-NO-LOGIN-PROMPT] | PASS — component moved to `.trash/` |

## Notes

- **Backend 1.16:** GET predictions uses `OptionalUser`; anonymous pre-deadline → 403 `PREDICTIONS_NOT_PUBLIC`; post-deadline → 200 full table.
- **Frontend 2.2.1:** Visitor post-deadline shows `PredictionsMatrix` without login; `PredictionsLoginPrompt` removed; deadline gate uses `isDeadlinePassedNow`.
- **Extra fix:** `apiFetch` no longer dispatches `fp:unauthorized` on 401 when no Bearer token was sent — prevented guest redirect to home when `fetchContestDetails` probed staff-only endpoints.
