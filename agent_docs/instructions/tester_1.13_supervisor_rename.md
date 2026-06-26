# Tester Instructions — Stage 1.13: admin → supervisor Rename Verification

> **Status gate:** @Coder `READY_FOR_TEST` for 1.13 rename (single commit).
> **Coder spec:** `agent_docs/instructions/coder_1.13_supervisor_rename.md`
> **Prerequisite:** `tester_1.12_fix.md` **TEST_PASS**; `tester_2.1.2_fix_supervisor.md` **TEST_PASS** (or run in parallel if rename commit includes 2.1.2 paths).
> **Report:** `agent_docs/reports/test_1.13_supervisor_rename.md`
> **Strategy:** Grep audit + full regression. **Do not modify** production code — report stragglers to @Coder.

---

## 1. Objective

Verify the **hard rename** of organizer paths from `admin` to `supervisor`:

| Layer | Old | New |
|-------|-----|-----|
| Contest API | `…/contests/{id}/admin/*` | `…/contests/{id}/supervisor/*` |
| Frontend UI | `/admin/*` | `/supervisor/*` |
| Platform API | `/api/v1/admin/users/*` | **unchanged** |

Confirm **no** contest-scoped `/admin/` remains in code, tests, or living contracts (except documented platform admin).

**Non-goals:**

- New features (auth, lifecycle) — already covered by `tester_1.12_fix.md`
- Real platform ADMIN UI
- Renaming `docs/` immutable specs

---

## 2. Test environment

Same as `tester_1.12_fix.md` §2.1 + frontend dev server.

After rename, supervisor login should land on `/supervisor/settings/parameters`.

---

## 3. Scope — files you may create

```
agent_docs/reports/test_1.13_supervisor_rename.md
```

Optional helper script in report (not committed unless team agrees):

```bash
# Straggler hunt — must return zero hits for contest-scoped admin paths
rg '/contests/\{[^}]+\}/admin/' --glob '!node_modules' --glob '!.venv'
rg 'contest_url\([^)]+,\s*"/admin/' tests/
rg '"/admin/settings' frontend/
```

---

## 4. Static audit (mandatory before runtime)

### 4.1 `[RENAME-GREP-API]`

Search repo (exclude `node_modules`, `.venv`, `docs/`):

| Pattern | Expected |
|---------|----------|
| `"/admin/rounds"` in `src/` `tests/` | **0** (use `/supervisor/rounds`) |
| `"/admin/matches"` in `src/` `tests/` | **0** |
| `contestAdmin` in `frontend/` | **0** (→ `contestSupervisor`) |
| `POST /api/v1/admin/users/supervisor` | **≥1** (platform admin kept) |

### 4.2 `[RENAME-GREP-UI]`

| Pattern | Expected |
|---------|----------|
| `frontend/src/app/admin/` | **0** (→ `app/supervisor/`) |
| `href="/admin/settings` in frontend | **0** (or redirect-only in next.config) |
| `gotoAdminContest` | **0** (→ `gotoSupervisorContest`) |
| `deriveAdminUiMode` | **0** (→ `deriveSupervisorUiMode`) |

### 4.3 `[RENAME-DOCS]`

| File | Check |
|------|-------|
| `agent_docs/contracts/api_v1.yaml` | All contest ops under `/supervisor/` |
| `agent_docs/contracts/frontend_api_integration.md` | §5.5 matrix + routing |
| `manuals/API_GUIDE.md` | Terminology § «Roles vs URL prefixes» |
| `manuals/BOOTSTRAP_USERS.md` | Still `/admin/users/supervisor` |

---

## 5. API runtime tests

Use supervisor token on fresh or loaded contest.

### 5.1 `[API-SUP-ROUNDS]` Round CRUD path

| Step | Call | Expected |
|------|------|----------|
| Create | `POST …/supervisor/rounds` | **200/201** |
| Activate | `POST …/supervisor/rounds/{rid}/activate` | **200** |
| Close | `POST …/supervisor/rounds/{rid}/close` | **200** (after deadline) |
| Calculate | `POST …/supervisor/rounds/{rid}/calculate` | **200** |
| Publish | `POST …/supervisor/rounds/{rid}/publish` | **200** |

### 5.2 `[API-SUP-MATCHES]` Match ops

`PUT …/supervisor/matches/{mid}/result` and `PATCH …/status` → **200** on valid CLOSED round.

### 5.3 `[API-OLD-410]` Legacy global shims (if kept)

`POST /api/v1/admin/rounds` (no contest prefix) → **410 Gone** or route removed (document actual behaviour).

### 5.4 `[API-OLD-FAIL]` Old contest-scoped paths must fail

`POST …/contests/{id}/admin/rounds` → **404** (no alias).

### 5.5 `[API-PLATFORM-ADMIN]` Platform admin unchanged

`POST /api/v1/admin/users/supervisor` with ADMIN token → **200/201**.

---

## 6. Frontend runtime tests

### 6.1 `[UI-ROUTE-SUPERVISOR]`

Supervisor login → lands on `/supervisor/settings/parameters` (not `/admin/…`).

Navigate tabs:

- `/supervisor/settings/participants`
- `/supervisor/settings/teams`
- `/supervisor/rounds`
- `/supervisor/results`

All load without 404.

### 6.2 `[UI-REDIRECT-ADMIN]` Optional redirects

If `next.config.mjs` redirects enabled:

- `GET /admin/settings/parameters` → **301/308** to `/supervisor/settings/parameters`

### 6.3 `[UI-NETWORK-PATHS]`

Browser devtools on rounds page: API calls use `…/supervisor/rounds`, not `…/admin/rounds`.

---

## 7. Automated regression (mandatory)

Coder must run before handoff; tester **re-runs** and records in report:

```bash
uv run pytest tests/ -v --tb=short
uv run ruff check src/ tests/
uv run mypy src/
cd frontend && npm run lint && npm run type-check
cd frontend && npm test -- --run   # if unit tests exist
cd frontend && npx playwright test
```

**Pass criterion:** zero failures; grep audit §4 clean.

---

## 8. E2E fixture updates

Verify Coder updated (or file follow-up if tester owns E2E):

| File | Expected |
|------|----------|
| `frontend/e2e/fixtures/adminApi.ts` | Renamed or paths use `/supervisor/` |
| `frontend/e2e/**/*.spec.ts` | `gotoSupervisorContest`, `/supervisor/…` URLs |
| `frontend/playwright.global-setup.ts` | No `/admin/` paths |

---

## 9. Exit criteria

| Gate | Requirement |
|------|-------------|
| **TEST_PASS** | §4 grep clean; §5–§7 runtime PASS; full pytest + Playwright green |
| **TEST_FAIL** | List straggler files/lines in report; do not patch `src/` yourself |

**Git expectation:** single commit `refactor: rename organizer admin paths to supervisor`; tester verifies **after** that commit only.
