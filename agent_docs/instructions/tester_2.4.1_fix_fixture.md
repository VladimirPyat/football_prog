# Tester 2.4.1 — E2E hybrid fixture profile (`--e2e-with-published`)

## Goal

Unify conflicting E2E vs manual dev fixture profiles so the **full Playwright suite** can run without profile clashes.

## Root cause (recap)

| Profile | Command | Rounds 1–9 | Round 10 | Demo `user` |
|---------|---------|------------|----------|-------------|
| Manual | `--ensure-running-only` | PUBLISHED | CALCULATED | PENDING |
| Legacy E2E | `--ensure-running-only --e2e` | CLOSED | ACTIVE | PENDING after finalize |

E2E helpers mixed both profiles → prediction tests failed (`PARTICIPANT_NOT_ACCEPTED`), LB/results tests failed (no PUBLISHED rounds), supervisor ACTIVE tests failed (round 10 CALCULATED).

## Variant C — hybrid profile

**Command:** `uv run python src/scripts/dev_setup.py --ensure-running-only --e2e-with-published`

| Rounds 1–9 | Round 10 | Round 11 | Demo `user` |
|------------|----------|----------|---------------|
| PUBLISHED + scores | ACTIVE, future deadline, 0 scores | CLOSED | ACCEPTED |

Legacy manual profile unchanged: `--ensure-running-only` (no flags) or `--finalize-fixture-only`.

## Implementation checklist

### Backend

- [x] `finalize_dev_fixture.py` — profile `e2e_with_published`
- [x] `dev_setup.py` — flag `--e2e-with-published` (mutually exclusive with `--e2e`)
- [x] `tests/scripts/test_finalize_dev_fixture_1_14.py` — hybrid profile test

### E2E fixtures

- [x] `adminApi.ts` — `reloadLoadedContestFixture`, `ensureLoadedContestDevState` use hybrid
- [x] `predictionsApi.ts` — `ensureE2eActiveRound` uses hybrid
- [x] Old helpers archived: `.trash/frontend/e2e/fixtures/adminApi.fixtureHelpers.old.ts`
- [x] Supervisor tests expecting CALCULATED round 10 call `finalizeLoadedContestFixture()` in-test (manual profile; API cannot patch ACTIVE future deadline to past)

### Verification

```bash
# Backend fixture test
uv run pytest tests/scripts/test_finalize_dev_fixture_1_14.py -q

# Apply hybrid to running dev DB (API must be up for E2E)
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e-with-published

# Full E2E (from frontend/)
npm run test:e2e

# 2.4-specific specs
npx playwright test e2e/contest_leaderboard_stub.spec.ts e2e/results_graceful.spec.ts
```

### Report

Update `agent_docs/reports/test_2.4.md` with full-suite results and note hybrid profile adoption.

## Rollback

If hybrid breaks unrelated tests, restore old helpers from `.trash/frontend/e2e/fixtures/adminApi.fixtureHelpers.old.ts` into `adminApi.ts` and revert E2E fixture calls to `--ensure-running-only` (manual).
