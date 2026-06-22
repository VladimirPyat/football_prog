# Tester Instructions — Stage 2.4: Leaderboard, Results & Integration E2E

> **Status gate:** @Coder `READY_FOR_TEST` for 2.4 in `agent_docs/progress/stage_2.md`.
> **Prerequisites:** Sub-stages **2.1**, **2.2**, and **2.3** at `TEST_PASS`; backend B1–B6 **RESOLVED** — see `agent_docs/reports/BLOCKED.md`.
> **Reference:** `instructions/coder_2.4.md`, `docs/03_user_scenarios.md`, `docs/04_supervisor_scenario.md`, `docs/06_front_tests.md`, `instructions/tester_2.2.md`, `instructions/tester_2.3.md`.
> **Strategy:** Unit (Vitest) + **full E2E suite** (Playwright) — agent runs; visual/mobile UX — **human** (agent reminds in report).

Stage **2.4** is the **integration QA gate** for Stage 2 frontend: leaderboard/results polish **plus** re-run of all user (2.2) and supervisor (2.3) E2E specs in one green suite.

---

## 1. Objective

Verify Stage **2.4** deliverables:

1. **Unit tests** — leaderboard columns, view-mode persistence, ETag cache, results guard.
2. **E2E — new 2.4** — visitor leaderboard, results graceful/unavailable, mobile toggle, sticky smoke.
3. **E2E — integration (must all pass)** — user + supervisor + RBAC specs listed in §6.
4. **Build** — `npm run build`.
5. **Docs** — Coder updated living specs (§8 of `coder_2.4.md`).
6. **BLOCKED.md** — confirm B4 live; append **B7+** only if new gaps found.

---

## 2. Test environment

Same as `tester_2.2.md` / `tester_2.3.md`:

```bash
cd /work/football_prog
uv run alembic upgrade head
uv run python src/scripts/bootstrap_users.py
uv run python src/scripts/load_test_data.py
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_CONTEST_ID=1
```

Playwright: `:3000` + `:8000`. Credentials: `user/user`, `supervisor` + `SEED_SUPERVISOR_PASSWORD`, `admin` + `SEED_ADMIN_PASSWORD`.

**Fixture facts for 2.4:**

| Round | Status | Use |
|-------|--------|-----|
| **9** | PUBLISHED | Results matrix; post-deadline predictions |
| **10** | ACTIVE | Results unavailable message; open predictions |
| Global LB | — | `GET …/contests/1/leaderboard` public |

**B4 smoke (API):**

```bash
curl -s http://127.0.0.1:8000/api/v1/contests/1/leaderboard | jq '.leaderboard[0] | {count_exact_high, count_exact, count_diff, count_outcome}'
```

All four keys must exist (non-null integers). If missing → **BLOCKER B7** in report + `BLOCKED.md`.

---

## 3. Scope — files you may create/modify

```
frontend/e2e/
  leaderboard_visitor.spec.ts           # NEW — 2.4
  leaderboard_mobile_toggle.spec.ts   # NEW — 2.4
  results_graceful.spec.ts            # NEW — 2.4
  rbac.spec.ts                          # NEW or extend — user /admin blocked
  user_full_flow.spec.ts              # NEW or from 2.2/2.4 — full integration
  # Re-use or verify exist from 2.2:
  prediction_validation.spec.ts
  prediction_batch.spec.ts
  prediction_privacy.spec.ts
  prediction_deadline_warning.spec.ts
  deadline_block.spec.ts
  user_predict_flow.spec.ts
  visitor_predictions_stub.spec.ts
  contest_predictions_tab.spec.ts
  # Re-use or verify exist from 2.3:
  admin_rbac.spec.ts
  admin_setup.spec.ts
  supervisor_create_round.spec.ts
  supervisor_24h_rule.spec.ts
  supervisor_results.spec.ts
  supervisor_void_match.spec.ts
  supervisor_free_tour.spec.ts
  admin_pause.spec.ts
frontend/e2e/fixtures/                # auth, predictionsApi, adminApi
agent_docs/reports/test_2.4.md          # NEW — verdict report
```

**Do NOT modify:** `docs/`, Python `src/` (backend bugs → `BLOCKED.md`).

---

## 4. Unit tests (Vitest) — mandatory

```bash
cd frontend && npm run test:unit
```

| ID | Target | Assert |
|----|--------|--------|
| `[UNIT-LB-COLUMNS]` | `leaderboardColumns.ts` | Full 13 headers order; compact 3; field map |
| `[UNIT-LB-VIEW-MODE]` | `useLeaderboardViewMode` | localStorage `fp_leaderboard_view_mode`; persist read/write |
| `[UNIT-ETAG-CACHE]` | `lib/api/cache.ts` | 304 uses cache; new ETag stored |
| `[UNIT-RESULTS-GUARD]` | results guard helper | ACTIVE/CLOSED → false; CALCULATED/PUBLISHED → true |

---

## 5. E2E — Stage 2.4 specific (mandatory)

### 5.1 `[E2E-LB-VISITOR]` — `leaderboard_visitor.spec.ts`

1. Clear storage; visit `/contest/1` (or `/` → select contest).
2. Tab **Лидерборд** default/active.
3. Assert `data-testid="leaderboard-table"` visible with ≥1 row.
4. Assert column headers include **Место**, **Фамилия Имя**, **Всего очков**.
5. No login required (`localStorage` no token).

Maps to: **Visitor global leaderboard without login**.

### 5.2 `[E2E-LB-B4-COLUMNS]` — (in `leaderboard_visitor` or separate)

Desktop viewport `1280×720`:

1. Assert headers include **Точный кр. счет**, **Точный счет**, **Разница**, **Исход** (B4).
2. First data row has numeric cells in those columns (not empty headers only).

If columns hidden → FAIL + file B7 unless Coder documented legacy fallback with empty API.

### 5.3 `[E2E-LB-MOBILE-TOGGLE]` — `leaderboard_mobile_toggle.spec.ts`

Viewport **`390×844`** (mobile).

1. Open `/contest/1` → **Лидерборд**.
2. Assert `data-testid="leaderboard-view-toggle"` visible.
3. Default or select **Краткая** → table shows **3** column headers (Место, Фамилия Имя, Всего очков); **no** «Бонус 1» header.
4. Click **📊 Полная** → **13** column headers visible; container `overflow-x` scrollable.
5. Switch to round **9** via `RoundSelector` → toggle still **Полная** (localStorage persisted).
6. Reload page → mode still **Полная**.

Desktop viewport `1280×720`: toggle **hidden** (or not visible); **13** columns shown without needing toggle.

Maps to: **mobile full/short toggle + localStorage persistence**.

### 5.4 `[E2E-LB-STICKY]` — (in mobile toggle or manual)

Mobile **Полная** mode with horizontal scroll:

1. Scroll table horizontally.
2. Assert **Место** and **Фамилия Имя** cells remain visible (Playwright: bounding box of first column stable while scrolling — or `toBeVisible` after scroll).

Mark `[MANUAL-STICKY]` in report if automated check flaky.

### 5.5 `[E2E-LB-GREEN-TOTAL]` — (in visitor or mobile spec)

Assert **Всего очков** header or cells have green styling class (e.g. `text-green-700`, `bg-green-50`) in **both** compact and full mobile modes.

### 5.6 `[E2E-RESULTS-UNAVAILABLE]` — `results_graceful.spec.ts`

1. `/contest/1` → tab **Результаты** → select **round 10** (ACTIVE).
2. Assert `data-testid="results-unavailable"` or text «Результаты будут доступны после подведения итогов».
3. **No** points matrix with user rows.

### 5.7 `[E2E-RESULTS-MATRIX]` — (same file)

1. Select **round 9** (PUBLISHED).
2. Assert results grid visible (match headers + points cells).
3. API smoke: `GET …/rounds/{id}/results` → 200 with `results[]` non-empty.

Maps to: **Results only CALCULATED/PUBLISHED**.

---

## 6. E2E — integration suite (mandatory — all must pass)

Run **entire** `frontend/e2e/` (or grouped npm scripts). Minimum spec list:

### 6.1 User flows (`docs/03` + `tester_2.2`)

| ID | Spec file | Source |
|----|-----------|--------|
| `[E2E-USER-FULL-FLOW]` | `user_full_flow.spec.ts` | Visitor LB → login → predict 8/8 → logout |
| `[E2E-PRED-BATCH]` | `prediction_batch.spec.ts` | 7/8 disabled, 8/8 save, 0:0 |
| `[E2E-PRED-VALIDATION]` | `prediction_validation.spec.ts` | invalid chars, max+1 |
| `[E2E-PRED-PRIVACY-PRE]` | `prediction_privacy.spec.ts` | «Прогноз сделан» |
| `[E2E-PRED-PRIVACY-POST]` | `prediction_privacy.spec.ts` | full matrix post-deadline |
| `[E2E-DEADLINE-BLOCK]` | `deadline_block.spec.ts` | readonly after deadline |
| `[E2E-USER-PREDICT-FLOW]` | `user_predict_flow.spec.ts` | profile → edit flow |
| `[E2E-VISITOR-PRED-STUB]` | `visitor_predictions_stub.spec.ts` | pre-deadline stub |

If `user_full_flow.spec.ts` missing — compose from steps in `docs/03` E2E §:

1. Visitor → `/contest/1` → leaderboard visible
2. Login `user/user` → `/profile`
3. **Сделать прогноз** → fill 8/8 → Save → **Редактировать** visible
4. **Выйти** → **Вход** visible

### 6.2 Supervisor flows (`docs/04` + `tester_2.3`)

| ID | Spec file |
|----|-----------|
| `[E2E-SUPERVISOR-CREATE-ROUND]` | `supervisor_create_round.spec.ts` |
| `[E2E-SUPERVISOR-24H]` | `supervisor_24h_rule.spec.ts` |
| `[E2E-SUPERVISOR-RESULTS]` | `supervisor_results.spec.ts` |
| `[E2E-SUPERVISOR-VOID]` | `supervisor_void_match.spec.ts` |
| `[E2E-SUPERVISOR-FREE-TOUR]` | `supervisor_free_tour.spec.ts` |

Optional but recommended from 2.3: `[E2E-ADMIN-LOCK]`, `[E2E-ADMIN-PAUSE]`.

### 6.3 RBAC

| ID | Spec file | Assert |
|----|-----------|--------|
| `[E2E-RBAC-ADMIN]` | `rbac.spec.ts` or `admin_rbac.spec.ts` | `user/user` → `/admin/settings/parameters` **blocked** |
| `[E2E-RBAC-ADMIN]` | same | `supervisor` → `/admin/*` **allowed** |

Maps to checklist: **user cannot access /admin**.

### 6.4 Single command

```bash
cd frontend && npm run test:e2e
# or: npx playwright test --project=chromium
```

Document pass count / skips in report.

---

## 7. Build & lint

```bash
npm run lint
npm run build
```

| ID | Pass |
|----|------|
| `[BUILD]` | exit 0 |
| `[LINT]` | no errors |

---

## 8. Documentation audit

| ID | Check |
|----|-------|
| `[DOC-UI-COMPONENTS]` | `LeaderboardTable`, `ResultsMatrix`, toggle — **Implemented (2.4)** |
| `[DOC-UI-PAGES]` | `/contest/[id]` complete tabbed page ✅ |
| `[DOC-INTEGRATION]` | ETag + responsive leaderboard documented |
| `[DOC-CODER-HANDOFF]` | `stage_2.md` Coder 2.4 `READY_FOR_TEST` |

---

## 9. BLOCKED.md verification

After all tests:

1. Confirm **B1–B6 RESOLVED** still accurate.
2. **B4 live check** — curl/jq in §2; UI shows four count columns.
3. **Stage 2.4 readiness checklist** (§10) — mark verified in `test_2.4.md`.
4. New gaps only:

```markdown
### OPEN — B7: …
- **Why:** `[E2E-…]` or API smoke …
- **Blocks:** 2.4 / release
- **Fallback:** …
```

Do **not** remove resolved B1–B6 entries.

---

## 10. Manual checklist — human developer

Include in `test_2.4.md`:

> Разработчик должен вручную проверить перед релизом Stage 2:
> - [ ] `user_leaderboard.jpg` — column order, bonus tint, green total column
> - [ ] `user_result.jpg` — results matrix layout, points green highlight
> - [ ] Sticky columns feel correct on real device horizontal scroll
> - [ ] Toggle «📊 Полная» / «Краткая» on phone ~375px
> - [ ] Round selector updates all three tabs consistently
> - [ ] Cross-browser smoke (Chromium minimum)

---

## 11. Report template — `agent_docs/reports/test_2.4.md`

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-LB-COLUMNS]` | PASS/FAIL | |
| `[UNIT-LB-VIEW-MODE]` | PASS/FAIL | |
| `[UNIT-ETAG-CACHE]` | PASS/FAIL | |
| `[UNIT-RESULTS-GUARD]` | PASS/FAIL | |
| `[E2E-LB-VISITOR]` | PASS/FAIL | |
| `[E2E-LB-B4-COLUMNS]` | PASS/FAIL | |
| `[E2E-LB-MOBILE-TOGGLE]` | PASS/FAIL | |
| `[E2E-LB-STICKY]` | PASS/FAIL/MANUAL | |
| `[E2E-LB-GREEN-TOTAL]` | PASS/FAIL | |
| `[E2E-RESULTS-UNAVAILABLE]` | PASS/FAIL | |
| `[E2E-RESULTS-MATRIX]` | PASS/FAIL | |
| `[E2E-USER-FULL-FLOW]` | PASS/FAIL | |
| `[E2E-PRED-*]` | PASS/FAIL | batch/validation/privacy/deadline |
| `[E2E-SUPERVISOR-*]` | PASS/FAIL | list specs run |
| `[E2E-RBAC-ADMIN]` | PASS/FAIL | |
| `[BUILD]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| B4 API smoke | OK / B7 | |
| BLOCKED.md | OK / NEW | |
| Manual checklist | REMINDER | §10 |

**Verdict:** `TEST_PASS` / `TEST_FAIL`.

On **TEST_PASS:** **Stage 2 frontend complete** (pending human manual checklist).

---

## 12. Acceptance mapping (Coder §9 + plan checklist)

| Criterion | Test ID |
|-----------|---------|
| Visitor leaderboard no login | `[E2E-LB-VISITOR]` |
| Results graceful if not published | `[E2E-RESULTS-UNAVAILABLE]` |
| Results matrix when published | `[E2E-RESULTS-MATRIX]` |
| Mobile toggle compact/full | `[E2E-LB-MOBILE-TOGGLE]` |
| localStorage view mode | `[E2E-LB-MOBILE-TOGGLE]`, `[UNIT-LB-VIEW-MODE]` |
| Sticky columns | `[E2E-LB-STICKY]` |
| Green total column | `[E2E-LB-GREEN-TOTAL]` |
| B4 count columns | `[E2E-LB-B4-COLUMNS]`, B4 curl |
| `user_full_flow` | `[E2E-USER-FULL-FLOW]` |
| `prediction_validation`, `deadline_block` | `[E2E-PRED-*]`, `[E2E-DEADLINE-BLOCK]` |
| supervisor_* suite | `[E2E-SUPERVISOR-*]` |
| RBAC user /admin | `[E2E-RBAC-ADMIN]` |

---

## 13. Progress update

On **TEST_PASS**, append to `agent_docs/progress/stage_2.md`:

```
## YYYY-MM-DD — Tester (2.4)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.4.md
- Unit: N passed; E2E: M passed (K skipped)
- Integration: user + supervisor + RBAC suite green
- BLOCKED.md: B4 verified / B7 added (…)
- Stage 2 frontend: COMPLETE (manual UX pending)
```

---

## 14. Explicitly OUT OF SCOPE

- Backend Stage 1 full regression pytest suite
- Visual `toHaveScreenshot()` vs `docs/screens/`
- Performance load test 100+ users (virtualization decision left to Coder profiling)
- Stage 3 newsletters / Docker
