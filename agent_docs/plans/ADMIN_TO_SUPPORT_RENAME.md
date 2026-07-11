# ADMIN → Support: Role and API Path Rename

> **Status:** Planned — **do not run** until explicitly scheduled.  
> **Single commit** recommended, then full test suite.  
> **Audit reference:** [agent_docs/reports/audit_admin_terminology.md](../agent_docs/reports/audit_admin_terminology.md)

---

## Terminology (after rename)

| Term | `users.role` | Who |
|------|--------------|-----|
| **Supervisor (organizer)** | `SUPERVISOR` | Runs contest: teams, rounds, results, calculate/publish |
| **Support (technical staff)** | `SUPPORT` (was `ADMIN`) | Lifecycle overrides, restore, global recalculate, create supervisor accounts, pre-deadline prediction visibility |

**Do not rename (by agreement):**

| Item | Reason |
|------|--------|
| `…/contests/{id}/admin/rounds`, `…/admin/matches` | Organizer API — historical path name; supervisor role |
| Frontend `/admin/*` (except support-only pages) | Organizer UI shell |
| `frontend/src/lib/admin/*`, `components/admin/*` | Code module names |

---

## Scope

### In scope (this instruction)

1. **Role enum:** `UserRole.ADMIN` → `UserRole.SUPPORT`, DB value `ADMIN` → `SUPPORT`
2. **Env / bootstrap:** `SEED_SUPPORT_*` — **done** (2026-07-11). Default login `admin` kept (`SEED_SUPPORT_LOGIN`).
3. **Support-only API paths** (same commit as role):
   - `POST /api/v1/admin/users/supervisor` → `POST /api/v1/support/users/supervisor`
   - `POST /api/v1/contests/{id}/admin/recalculate` → `POST /api/v1/contests/{id}/support/recalculate`
   - Mark old paths `deprecated=True` in OpenAPI for one release, or remove if no external clients
4. **Frontend:** guards, `UserRole` type, privacy bypass, lifecycle/users pages, `endpoints.ts`
5. **Tests / E2E:** update fixtures and role strings
6. **Docs:** `manuals/*`, `docs/*` prose (Admin → Support where role is meant; add «(supervisor)» for organizer UI)

### Out of scope

- Renaming organizer paths `…/admin/rounds|matches` → `…/supervisor/…` (deferred indefinitely)
- Renaming frontend route prefix `/admin` → `/supervisor`
- API version bump to `v2` (stay on `v1` + deprecated aliases if needed)

---

## What support can do today (verify after rename)

| Capability | API | UI |
|------------|-----|-----|
| Create organizer | `POST /api/v1/support/users/supervisor` | `/admin/users` |
| List deleted contests | `GET /api/v1/contests/deleted` | `/admin/lifecycle` |
| Restore contest | `POST /api/v1/contests/{id}/restore` | `/admin/lifecycle` |
| Finish contest | `POST /api/v1/contests/{id}/finish` | `/admin/lifecycle` |
| Global recalculate | `POST …/support/recalculate` | `/admin/lifecycle` → «Пересчитать» |
| Exceptional tiebreak | `PUT …/participants/{uid}/exceptional-tiebreak` | admin API |
| All predictions pre-deadline | `GET …/predictions` | contest page matrix |
| Restore CANCELED match | — | `/admin/rounds` (ADMIN-only UI rule) |

**Recalculate vs calculate:** `POST …/rounds/{id}/calculate` (supervisor, CLOSED→CALCULATED) is **not** the same as `…/support/recalculate` (support, all CALCULATED rounds re-scored).

---

## Execution order (one commit)

### Phase 1 — Database and config

1. **Alembic migration** (new revision):

   ```sql
   UPDATE users SET role = 'SUPPORT' WHERE role = 'ADMIN';
   ```

   No CHECK constraint on `users.role` today — migration is sufficient.

2. **`src/database/models.py`:** `SUPPORT = "SUPPORT"` (remove `ADMIN` or keep alias temporarily — prefer clean break).

3. **`config/settings.py`:** `seed_support_*` — **done** (2026-07-11).

4. **`.env.example`**, **`frontend/.env.local.example`:** `SEED_SUPPORT_*`, `E2E_SUPPORT_PASSWORD`.

5. **`src/scripts/bootstrap_users.py`**, **`src/scripts/seed.py`:** role + env keys.

### Phase 2 — Backend RBAC

Replace `UserRole.ADMIN` with `UserRole.SUPPORT` everywhere. Rename dependency variables for clarity: `_admin` → `_support` where role is support-only.

**Critical files:**

- `src/api/v1/contests.py` — `require_finish_role`, `require_restore_role`, `GET /deleted`
- `src/api/v1/admin_users.py` — move router to `support_users.py` or change prefix to `/support/users`
- `src/api/v1/contest_ops.py` — recalculate endpoint path
- `src/api/v1/contest_participants.py` — exceptional tiebreak
- `src/services/prediction_service.py` — `is_privileged`
- `src/services/leaderboard_service.py` — `_STAFF_ROLES`

**SUPERVISOR+ tuples:** replace `UserRole.ADMIN` with `UserRole.SUPPORT` in `RoleChecker(SUPERVISOR, …)` across `admin_rounds.py`, `admin_results.py`, `contest_teams.py`, etc.

**Optional cleanup:** remove or leave deprecated legacy shims in `admin_contest.py`, `admin_misc.py` (`POST /api/v1/admin/recalculate` without contest_id).

### Phase 3 — Frontend

- `frontend/src/types/api.ts` — `UserRole`
- `frontend/src/lib/auth/guards.ts`, `resolvePostLoginPath.ts`
- `frontend/src/lib/privacy/shouldShowScore.ts`
- `frontend/src/app/admin/lifecycle/page.tsx`, `users/page.tsx` — `role !== "SUPPORT"`
- `frontend/src/app/contest/[contestId]/page.tsx` — `isSupportViewer`
- `frontend/src/lib/admin/matchScheduleEdit.ts`, `RoundManagementPanel.tsx`
- `frontend/src/lib/api/endpoints.ts` — support paths

### Phase 4 — Tests

Update role strings and paths in:

- `tests/api/conftest.py` (`support_api` login)
- `tests/api/test_auth_rbac_1_3.py`
- `tests/api/test_contest_lifecycle_1_3.py`
- `tests/api/test_admin_users.py`
- `tests/unit/test_api_unit_1_3.py`
- `frontend/e2e/fixtures/auth.ts`, `credentials.ts`, `adminApi.ts`
- `frontend/e2e/auth_role_routing.spec.ts`, `z_admin_pause.spec.ts`, `prediction_privacy.spec.ts`
- `frontend/src/lib/auth/resolvePostLoginPath.test.ts`, `shouldShowScore.test.ts`, `participantRoundFilter.test.ts`

### Phase 5 — Documentation (same PR or follow-up)

| Priority | Files |
|----------|-------|
| P0 | `docs/01_tech_regulations.md` §1.2, UC-13 |
| P0 | `manuals/API_GUIDE.md`, `CONFIG.md`, `BOOTSTRAP_USERS.md` |
| P1 | `manuals/SUPERVISOR_TESTING_SCENARIOS.md`, `FRONTEND_REFERENCE.md` |
| P1 | `docs/03_user_scenarios.md`, `docs/04_supervisor_scenario.md`, `docs/06_front_tests.md` |

Glossary blurb for `manuals/README.md` or `API_GUIDE.md`:

```text
Supervisor (organizer) — role SUPERVISOR; tour/match API under …/admin/… (historical path).
Support — role SUPPORT; lifecycle, restore, recalculate, create supervisor accounts.
```

---

## Post-deploy

1. **Re-run bootstrap** on fresh DB, or migration on existing DB.
2. **All users with old JWT must re-login** (`role` claim changes).
3. Update local `.env` from `.env.example`.

---

## Verification (full suite)

Run after the single commit:

```bash
# Backend lint + security
uv run ruff check src/
uv run mypy src/
uv run bandit -r src/ -ll

# Backend tests (full)
uv run pytest

# Frontend
cd frontend
npm run lint
npm run type-check
npm run test:unit
npm run test:e2e
```

**High-signal tests if time-constrained:**

```bash
uv run pytest tests/api/test_auth_rbac_1_3.py tests/api/test_contest_lifecycle_1_3.py tests/api/test_admin_users.py -q
cd frontend && npm run test:unit -- src/lib/auth/resolvePostLoginPath.test.ts src/lib/privacy/shouldShowScore.test.ts
```

**Manual smoke:**

1. Login as support → `/admin/lifecycle`, `/admin/users` accessible.
2. Login as supervisor → lifecycle/users **blocked**; `/admin/rounds` works.
3. Support: `POST …/support/recalculate` returns `{ recalculated_rounds: N }`.
4. Pre-deadline: support sees full prediction matrix; supervisor sees stub only own scores on predict page.

---

## API versioning note

Stay on **`/api/v1`**. For path renames, prefer:

- new path + old path `deprecated=True` for one release, **or**
- atomic rename if only this frontend consumes the API.

Raising **`v2`** is optional and only needed when external clients cannot migrate in sync.

---

## Related artifacts

- Audit (full file lists): [agent_docs/reports/audit_admin_terminology.md](../agent_docs/reports/audit_admin_terminology.md)
- Deprecated endpoint rename (`…/admin/*` → `…/supervisor/*`): **cancelled** — see `.trash/agent_docs/instructions/backend/tester_1.13_supervisor_rename.md`
