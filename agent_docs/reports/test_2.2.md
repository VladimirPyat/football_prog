# Test Report — Stage 2.2 (Predictions & Privacy)

## Verdict: TEST_PASS

Stage 2.2 acceptance gates passed (2026-07-08). Includes 2.2.1 visitor public predictions regression (E2E + API).

## Unit tests (Vitest)

Command: `npm run test:unit` → **153/153 passed**

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-SCORE-RANGE]` | PASS | score.test.ts |
| `[UNIT-BATCH-SCHEMA]` | PASS | prediction.test.ts |
| `[UNIT-PRIVACY-SHOW]` | PASS | shouldShowScore.test.ts |
| `[UNIT-DEADLINE-WARN]` | PASS | deadlineWarning.test.ts |

## E2E (Playwright)

Command: `npm run test:e2e -- e2e/prediction_*.spec.ts e2e/deadline_block.spec.ts e2e/user_predict_flow.spec.ts e2e/visitor_predictions_*.spec.ts e2e/contest_predictions_tab.spec.ts e2e/contest_leaderboard_stub.spec.ts` → **11/11 passed**

| ID | Result | Notes |
|----|--------|-------|
| `[E2E-PRED-BATCH]` | PASS | 7/8 disabled, 0 valid, persist |
| `[E2E-PRED-VALIDATION]` | PASS | maxScore from API helper |
| `[E2E-PRED-PRIVACY-PRE]` | PASS | stub before deadline |
| `[E2E-PRED-PRIVACY-POST]` | PASS | round 9 full matrix |
| `[E2E-PRED-DEADLINE-WARN]` | PASS | banner within 24h |
| `[E2E-DEADLINE-BLOCK]` | PASS | readonly after deadline |
| `[E2E-USER-PREDICT-FLOW]` | PASS | profile → predict → edit |
| `[E2E-VISITOR-PRED-STUB]` | PASS | round 10 stub |
| `[E2E-VISITOR-PRED-PUBLIC]` | PASS | round 9 guest matrix (2.2.1) |
| `[E2E-CONTEST-PRED-TAB]` | PASS | round selector + tab switch |
| `[E2E-LB-STUB-NOT-PUBLISHED]` | SKIP→PASS | Spec renamed `[E2E-LB-MOCK-DISPLAY]` — mock LB table (deferred to 2.4 scope) |
| `[E2E-TEARDOWN]` | PASS | API stopped; `--check-ports` exit 0 |

## Lint & build

| ID | Result | Notes |
|----|--------|-------|
| `[LINT-ESLINT]` | PASS | |
| `[LINT-TSC]` | PASS | |
| `[LINT-PRETTIER]` | PASS | Fixed 7 pre-existing drift files |
| `[BUILD]` | PASS | `next build` exit 0 |

## API (2.2.1 regression)

Command: `uv run pytest tests/api/test_predictions_flow_1_3.py tests/api/test_predictions_public_1_16.py -v` → **9/9 passed**

## Documentation audit

| ID | Result | Notes |
|----|--------|-------|
| `[DOC-UI-COMPONENTS]` | PASS | components.md — PredictionForm, PredictionsMatrix, etc. marked 2.2 |
| `[DOC-UI-PAGES]` | PASS | pages.md — predict page, Прогнозы tab |
| `[DOC-FORMS]` | PASS | forms_validation.md — prediction schema |
| `[DOC-INTEGRATION]` | PASS | frontend_api_integration.md §5.4 visitor public GET |
| `[DOC-CODER-HANDOFF]` | PASS | stage_2.md Coder 2.2 READY_FOR_TEST |

## Manual checklist (human before release)

> Разработчик должен вручную проверить перед релизом 2.2:
> - [ ] Layout формы vs `user_predict.jpg` (матчи, поля счёта, кнопки)
> - [ ] Подпись «0–N» соответствует правилам конкурса
> - [ ] `DeadlineWarningBanner` заметен (цвет/иконка)
> - [ ] «Прогноз сделан» читаемо; нет утечки чужих счётов до дедлайна
> - [ ] Пустое поле ≠ 0: cleared cell не отправляет 0
> - [ ] Мобильная ширина ~375px — форма и матрица с horizontal scroll

## Test maintenance applied during run

1. **`e2e/fixtures/auth.ts`** — `waitForUserAuthenticatedHeader` updated: header shows user login link (`data-testid="header-user-login"`) instead of «Личный кабинет».
2. **`e2e/contest_predictions_tab.spec.ts`** — aligned with pre-deadline participant stub on round 10; matrix asserted on round 9 only.
3. **Bootstrap order** — `load_test_data --reset` must run **before** `bootstrap_users.py` (loader clears staff/demo users).

## Environment notes

- Playwright browsers installed to sandbox cache (`npx playwright install chromium`).
- Fixture: contest 1, round 10 ACTIVE (e2e), round 9 PUBLISHED post-deadline.
- Demo user `user/user` from bootstrap (contest 1 participant).

## Next

Ready for **2.4** (leaderboard & integration).
