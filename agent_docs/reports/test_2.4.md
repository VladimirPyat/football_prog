# Test Report — Stage 2.4 (Leaderboard, Results & Integration E2E)

## Verdict: TEST_FAIL

Stage 2.4 integration QA gate **failed** (2026-07-08). Backend 1.17 and frontend unit/lint/build are green; **mandatory 2.4 E2E specs are missing**, several mandatory unit targets are absent/deferred, and the **full Playwright suite is not green** (51 passed / 19 failed).

---

## Backend API (1.17)

Command: `uv run pytest tests/api/test_round_results_points_1_17.py -v` → **6/6 passed** (exit 0)

| ID | Result | Notes |
|----|--------|-------|
| `[API-RESULTS-POINTS-LEN]` | PASS | |
| `[API-RESULTS-POINTS-NONEMPTY]` | PASS | |
| `[API-RESULTS-POINTS-ORDER]` | PASS | |
| `[API-RESULTS-TOTAL-WITHOUT-BONUS3]` | PASS | |
| `[API-RESULTS-NOT-PUBLISHED]` | PASS | |
| `[API-RESULTS-CALC-STAFF]` | PASS | |

### B4 API smoke

Command: `curl -s http://127.0.0.1:8000/api/v1/contests/1/leaderboard | jq '.leaderboard[0] | {count_exact_high, count_exact, count_diff, count_outcome}'`

Result: **OK** — all four keys present as non-null integers (e.g. `count_exact_high: 2`, `count_exact: 13`, `count_diff: 5`, `count_outcome: 20`). Global leaderboard: 10 rows after `dev_setup.py` reset.

---

## Unit tests (Vitest)

Command: `cd frontend && npm run test:unit` → **163/163 passed** (exit 0)

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-LB-COLUMNS]` | **FAIL** | `leaderboardColumns.ts` not implemented; closest coverage is `mapLeaderboardRow.test.ts` (B4 field mapping only) |
| `[UNIT-LB-VIEW-MODE]` | **FAIL** | `useLeaderboardViewMode` / `fp_leaderboard_view_mode` not implemented; `LeaderboardTable` uses viewport `matchMedia` auto-compact only |
| `[UNIT-ETAG-CACHE]` | **FAIL** | `lib/api/cache.ts` is a stub; no 304/cache tests |
| `[UNIT-RESULTS-GUARD]` | PASS | `roundResultsGuard.test.ts` — PUBLISHED only |

---

## E2E — Stage 2.4 specific (mandatory)

**Spec files not found** in `frontend/e2e/`:

- `leaderboard_visitor.spec.ts`
- `leaderboard_mobile_toggle.spec.ts`
- `results_graceful.spec.ts`
- `user_full_flow.spec.ts`

| ID | Result | Notes |
|----|--------|-------|
| `[E2E-LB-VISITOR]` | **FAIL** | Spec missing |
| `[E2E-LB-B4-COLUMNS]` | **FAIL** | Spec missing; B4 API smoke OK but no UI assertion |
| `[E2E-LB-MOBILE-TOGGLE]` | **FAIL** | Spec missing; no `data-testid="leaderboard-view-toggle"` in codebase |
| `[E2E-LB-STICKY]` | **FAIL** | Not automated; sticky CSS exists in `LeaderboardTable` but no E2E |
| `[E2E-LB-GREEN-TOTAL]` | **FAIL** | Spec missing |
| `[E2E-RESULTS-UNAVAILABLE]` | **FAIL** | Spec missing; `ResultsUnavailableMessage` component exists |
| `[E2E-RESULTS-MATRIX]` | **FAIL** | Spec missing |

Existing `contest_leaderboard_stub.spec.ts` still tests mock-era flow (`[E2E-LB-MOCK-DISPLAY]`) with logged-in user — does not satisfy 2.4 visitor/B4/mobile/results criteria.

---

## E2E — integration suite (mandatory — all must pass)

Command: `cd frontend && CI=1 npm run test:e2e -- --reporter=line` → **51 passed / 19 failed** (exit 1, ~11 min)

### Failed specs (19 tests)

| Spec | Test ID (if mapped) |
|------|---------------------|
| `auth_401_logout.spec.ts` | auth regression |
| `auth_login_profile.spec.ts` | login regression |
| `auth_logout.spec.ts` | logout regression |
| `auth_role_routing.spec.ts` (3 tests) | role routing |
| `auth_temp_password.spec.ts` | temp password |
| `prediction_privacy.spec.ts` | `[E2E-PRED-PRIVACY-PRE]` |
| `profile_contacts.spec.ts` | profile |
| `rbac_guards.spec.ts` | RBAC |
| `supervisor_24h_rule.spec.ts` | `[E2E-SUPERVISOR-24H]` |
| `supervisor_active_round.spec.ts` | supervisor |
| `supervisor_create_round.spec.ts` | `[E2E-SUPERVISOR-CREATE-ROUND]` / tour date validation |
| `supervisor_results_kickoff.spec.ts` | supervisor results |
| `supervisor_results_preview.spec.ts` (2 tests) | supervisor results pipeline |
| `supervisor_results.spec.ts` | `[E2E-SUPERVISOR-RESULTS]` |
| `user_contests.spec.ts` | user contests |
| `visitor_discovery.spec.ts` | visitor discovery |

### Common failure pattern (auth cluster)

Multiple auth specs failed waiting for `data-testid="header-user-login"` after login (`e2e/fixtures/auth.ts:45`, timeout 10s). Example:

```
Error: Timed out 10000ms waiting for expect(locator).toBeVisible()
Locator: getByTestId('header-user-login')
```

**Required action for @Coder:** Investigate post-login header rendering (`UserNavMenu` / `AppShell`) — login may succeed but header testid not visible within timeout; blocks user + supervisor flows that depend on `loginAsUser` / `loginAsDemoUser`.

### Mandatory §6 mapping (partial)

| ID | Result | Notes |
|----|--------|-------|
| `[E2E-USER-FULL-FLOW]` | **FAIL** | `user_full_flow.spec.ts` missing |
| `[E2E-PRED-BATCH]` | PASS | Not in failure list |
| `[E2E-PRED-VALIDATION]` | PASS | Not in failure list |
| `[E2E-PRED-PRIVACY-PRE]` | **FAIL** | `prediction_privacy.spec.ts` |
| `[E2E-PRED-PRIVACY-POST]` | PASS | Not in failure list (round 9 matrix) |
| `[E2E-DEADLINE-BLOCK]` | PASS | Not in failure list |
| `[E2E-USER-PREDICT-FLOW]` | PASS | Not in failure list |
| `[E2E-VISITOR-PRED-STUB]` | PASS | Not in failure list |
| `[E2E-SUPERVISOR-CREATE-ROUND]` | **FAIL** | `supervisor_create_round.spec.ts` |
| `[E2E-SUPERVISOR-24H]` | **FAIL** | `supervisor_24h_rule.spec.ts` |
| `[E2E-SUPERVISOR-RESULTS]` | **FAIL** | `supervisor_results.spec.ts` |
| `[E2E-SUPERVISOR-VOID]` | PASS | Not in failure list |
| `[E2E-SUPERVISOR-FREE-TOUR]` | PASS | Not in failure list |
| `[E2E-RBAC-ADMIN]` | PASS | `admin_rbac.spec.ts` not in failure list |
| `[E2E-TEARDOWN]` | PASS | API stopped; `dev_setup.py --check-ports` exit 0 |

---

## Lint & build

| ID | Result | Notes |
|----|--------|-------|
| `[LINT-ESLINT]` | PASS | `npm run lint` exit 0 |
| `[LINT-TSC]` | PASS | `npm run type-check` exit 0 after `npm run build` generated `.next/types` |
| `[LINT-PRETTIER]` | PASS | `npm run format:check` exit 0 |
| `[BUILD]` | PASS | `npm run build` exit 0 |

**Note:** Running `type-check` before any `next build` fails with missing `.next/types/**/*.ts` (environment ordering issue; not a source defect once build has run).

---

## Documentation audit

| ID | Result | Notes |
|----|--------|-------|
| `[DOC-UI-COMPONENTS]` | PASS | `LeaderboardTable`, `ResultsMatrix`, `ResultsUnavailableMessage` marked **API-wired (2.4)** |
| `[DOC-UI-PAGES]` | PASS | `/contest/[id]` tabbed page marked **API-wired (2.4)** |
| `[DOC-INTEGRATION]` | PASS | `useLeaderboard`, `useRoundResults` documented; ETag noted as deferred |
| `[DOC-CODER-HANDOFF]` | PASS | `stage_2.md` Coder 2.4 `READY_FOR_TEST` |

---

## BLOCKED.md

| Check | Result |
|-------|--------|
| B1–B6 RESOLVED | OK — unchanged |
| B4 live (API + UI) | API **OK**; UI B4 columns **not E2E-verified** (spec missing) |
| New B7+ | **Not added** — API B4 fields present; gaps are missing E2E specs and integration regressions |

---

## Manual checklist — human developer

> Разработчик должен вручную проверить перед релизом Stage 2:
> - [ ] `user_leaderboard.jpg` — column order, bonus tint, green total column
> - [ ] `user_result.jpg` — results matrix layout, points green highlight
> - [ ] Sticky columns feel correct on real device horizontal scroll
> - [ ] Toggle «📊 Полная» / «Краткая» on phone ~375px
> - [ ] Round selector updates all three tabs consistently
> - [ ] Cross-browser smoke (Chromium minimum)

---

## Required actions for @Coder (blocking)

1. **Add 2.4 E2E specs** per `tester_2.4.md` §5: `leaderboard_visitor`, `leaderboard_mobile_toggle`, `results_graceful`, `user_full_flow`.
2. **Implement or document deferral** for mobile view toggle + `fp_leaderboard_view_mode` if product requires `[UNIT-LB-VIEW-MODE]` / `[E2E-LB-MOBILE-TOGGLE]`.
3. **Fix auth header regression** — `header-user-login` not visible after login (19-spec cascade includes core user flows).
4. **Fix supervisor E2E regressions** — `supervisor_results`, `supervisor_24h_rule`, `supervisor_create_round`, results preview/kickoff specs.
5. **Re-run full suite** until `npm run test:e2e` is green and 2.4-specific IDs are covered.

---

## Commands executed

```bash
uv run python src/scripts/dev_setup.py
uv run python src/scripts/dev_setup.py --ensure-running-only --e2e
uv run uvicorn main:app --host 127.0.0.1 --port 8000  # background, stopped after E2E
uv run pytest tests/api/test_round_results_points_1_17.py -v          # 6 passed
cd frontend && npm run test:unit                                     # 163 passed
cd frontend && npm run lint && npm run type-check && npm run format:check
cd frontend && npm run build                                         # passed
cd frontend && CI=1 npm run test:e2e -- --reporter=line              # 51 passed, 19 failed
uv run python src/scripts/dev_setup.py --check-ports                 # exit 0
```

---

## Stage 2.4 readiness checklist (§10)

| Criterion | Verified |
|-----------|----------|
| Visitor leaderboard no login | **NO** — E2E missing |
| Results graceful if not published | **NO** — E2E missing |
| Results matrix when published | **NO** — E2E missing |
| Mobile toggle compact/full | **NO** — not implemented |
| localStorage view mode | **NO** |
| Sticky columns | **NO** — manual only |
| Green total column | **NO** — E2E missing |
| B4 count columns | API **YES** / UI E2E **NO** |
| Full integration E2E green | **NO** — 19 failures |
| Lint toolchain | **YES** |

**Stage 2 frontend: NOT COMPLETE** — pipeline should **STOP** on blocking TEST_FAIL.
