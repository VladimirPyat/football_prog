# Tester Instructions — Stage 1.3: API Integration & Triggers (Narrow Scope)

> Status gate: @Coder `READY_FOR_TEST` for 1.3. Prerequisite: 1.2.1 migration applied.
> Tests/reports English; user verdict Russian. Contracts: `api_v1.yaml`,
> `leaderboard_tiebreakers.md`, `bonus_rules.md`.

## 1. Objective

HTTP validation on **loader data** (`load_test_data.py`): auth/RBAC, batch/deadline/privacy,
**contest immutability**, **lifecycle** (pause/finish/safe delete), **exceptional tie-break
points**, VOID, caching. Lightweight calculate smoke only — **NOT** the 90/90 contract gate
(moved to Stage 1.4 full E2E).

Use `httpx.AsyncClient` against the ASGI app. Legacy paths (without `/contests/{id}/`) OK via shims after 1.4; for 1.3-only Coder use singleton paths.

## 2. Scope — files you may create

```
tests/api/conftest.py                     # loader DB, lifecycle helpers, instant-delete env
tests/api/test_auth_rbac_1_3.py
tests/api/test_predictions_flow_1_3.py
tests/api/test_contest_lifecycle_1_3.py   # immutability, lifecycle, tie-break
tests/api/test_calculate_smoke_1_3.py     # VOID, cache, single-round smoke — NOT 90/90
```
Do NOT create `verify_via_api.py` / `compare_db_vs_reference.py` here (Stage 1.4).
Isolated test DB for DELETE tests. Do NOT modify `src/`.

## 3. Auth & RBAC (`[AUTH-*]`, `[RBAC-*]`)
- `[AUTH-LOGIN]` valid creds → 200 + token; bad creds → 401.
- `[AUTH-TEMP]` temp password restricted to change-password/me → 403 elsewhere; clears after change.
- `[RBAC-USER]` USER cannot call SUPERVISOR endpoint → 403.
- `[RBAC-PUB]` public GET leaderboard/results without token → 200.
- `[RBAC-ADMIN]` `POST /admin/recalculate` ADMIN only.

## 4. Predictions over HTTP (`[API-PRED-*]`)
- `[API-PRED-PARTIAL]` 7/8 → 400.
- `[API-PRED-FULL]` 8/8 ACTIVE round before deadline → 200.
- `[API-PRED-RANGE]` score 21 → 422; 0 accepted.
- `[API-PRED-DEADLINE]` after deadline / non-ACTIVE → 403.
- `[API-PRED-PRIVACY]` before deadline: own scores + others `submitted` only; after: all visible.
- `[API-PRED-VISITOR]` GET predictions without token → 401.

## 5. Calculate smoke + cache (`[API-SMOKE-*]`) — NOT full contract

**Out of scope for 1.3:** `[API-CALC]` 90/90, `[API-LB-*]` 10/10 global leaderboard contract,
manual two-phase scripts → see `tester_1.4.md`.

- `[API-SMOKE-CALC]` single round calculate on loader → status CALCULATED, `users_scored > 0`.
- `[API-VOID]` VOID → atomic recalc; leaderboard row changes.
- `[API-CACHE]` public GET have Cache-Control + ETag; POST predictions does not.
- `[API-CACHE-ETAG]` ETag changes after calculate.

## 5a. Contest immutability (`[API-CS-*]`)
- `[API-CS-GET]` GET `/admin/contest-settings` (or contest-scoped equivalent via shim) as SUPERVISOR → 200 with `status`, `is_locked`.
- `[API-CS-PATCH-UNLOCKED]` PATCH `rules_json.scoring_rules` before first activate → 200.
- `[API-CS-PATCH-LOCKED]` after activate, PATCH any settings field → 403.
- `[API-CS-ACTIVATE]` first activate → `is_locked=true`, `status=RUNNING`.

## 5b. Exceptional tie-break (`[API-TB-*]`)
- `[API-TB-SET]` ADMIN `PUT .../exceptional-tiebreak` `{points: 5}` → 200.
- `[API-TB-LOCKED]` set exceptional points **after** contest locked → 200 (not a rules change).
- `[API-TB-RANK]` construct synthetic 4-criteria tie; user with higher exceptional points ranks above.
- `[API-TB-RBAC]` SUPERVISOR cannot set exceptional points → 403.
- `[API-TB-DISPLAY]` `GET /leaderboard` includes `exceptional_tiebreak_points` column.

## 5c. Contest lifecycle & safe delete (`[API-CONTEST-*]`)
- `[API-CONTEST-PAUSE]` POST pause from RUNNING → PAUSED, `paused_at` set.
- `[API-CONTEST-PAUSE-BLOCK]` POST predictions while PAUSED → 403.
- `[API-CONTEST-RESUME]` pause → resume → RUNNING; predictions work again.
- `[API-CONTEST-FINISH]` POST finish → FINISHED; predictions → 403; public GET still 200.
- `[API-CONTEST-FINISH-IDEM]` finish when already FINISHED → 200 no-op.
- `[API-CONTEST-DELETE-RBAC]` DELETE as SUPERVISOR → 403.
- `[API-CONTEST-DELETE-NOGRACE]` DELETE immediately after pause (instant=false) → 400.
- `[API-CONTEST-DELETE-BADCONFIRM]` wrong confirm body → 400.
- `[API-CONTEST-DELETE-OK]` with `contest_allow_instant_delete=true` in conftest:
  pause → DELETE `{confirm:"DELETE"}` → 200; DB wiped/reseeded; `status=DRAFT`.

## 6. Automated execution & report

```
uv run pytest tests/api/ -v
```
- **PASS** → `agent_docs/reports/test_1.3.md` (Russian) with [TEST-ID] table;
  append `STATUS: TEST_PASS` to `progress/stage_1.md`.
- **FAIL** → per [TEST-ID] expected vs actual; append `STATUS: TEST_FAIL`. Never edit `src/`.

## 7. Verdict to user (Russian)

Этап 1.3, PASS/FAIL, покрытие: auth/RBAC, batch/privacy, **immutability (lock guards)**,
**exceptional tie-break**, **lifecycle + safe delete**, VOID/cache smoke на loader data.
**Без** 90/90 и 10/10 (перенесено в 1.4). Дефекты с [TEST-ID].

## 8. Next step

After 1.3 PASS → @Coder implements 1.4 per `coder_1.4.md`; full E2E per `tester_1.4.md`.
