# Tester Instructions — Stage 1.16 Fix: Pytest Regression Cleanup

> **Status gate:** `IMPLEMENTED` — all §2.1–§2.6 fixes applied; full pytest green (383 pass)
> **Context:** Full `uv run pytest` reported 15 failures unrelated to public predictions (2.2.1 scope PASS). This doc locks **fix strategy per failure group** for a follow-up coder/tester pass.
> **Prerequisite:** `backend/coder_1.16_fix_public_predictions.md` + `coder_2.2.1.md` shipped
> **Language policy:** code comments English; API detail Russian unchanged

---

## 1. Objective

Restore full pytest green by updating stale tests to match current product behaviour:

| Stage | Behaviour change causing drift |
|-------|--------------------------------|
| 1.12 | `ENFORCE_PASSWORD_SETUP=true` → temp-password login blocked (`PASSWORD_SETUP_REQUIRED`) |
| 1.16 | Auto-close ACTIVE→CLOSED when deadline passed |
| 2.3.1 | Public round leaderboard/results only when `PUBLISHED` |
| 1.4+ | Contest delete may return `DELETED` (soft delete) |

**Non-goals:** Change production API to satisfy old tests; modify `docs/`.

---

## 2. Fix decisions (append-only)

### §2.1 — `enforce_password_setup` (9 tests) — **LOCKED: Option D**

**Problem:** Tests call `api_login(client, "temp_user")` or `api_login(login, temp_password)` expecting **200 + JWT**. With default `ENFORCE_PASSWORD_SETUP=true`, `POST /auth/login` for `is_temp_password=true` returns **403** `PASSWORD_SETUP_REQUIRED`.

**Affected tests:**

| ID | File | Test |
|----|------|------|
| AUTH-TEMP | `tests/api/test_auth_rbac_1_3.py` | `test_auth_temp_password_restricted` |
| CONTACTS-* | `tests/api/test_contacts.py` | `test_contacts_get_default`, `test_contacts_patch`, `test_contacts_invite`, `test_contacts_temp_password` |
| ME-CONTESTS-* | `tests/api/test_me_contests.py` | `test_me_contests_user`, `test_me_contests_empty` |
| SETUP-* | `tests/api/test_operational_gaps_1_4.py` | `test_setup_part_auth` |
| SETUP-* | `tests/api/test_setup_phase_1_4.py` | `test_setup_participant_invite` |

**Chosen strategy (D):** Migrate all 9 tests to **`stage_112_api`** fixture + **`tests/api/stage_112_helpers.py`** (`invite_participant`, `complete_setup`, `create_draft_contest`). Do **not** change `loaded_api` / `empty_api` default env.

**Implementation notes:**

1. Replace fixture param: `empty_api` / `loaded_api` → `stage_112_api` where temp-user JWT is needed.
2. For tests needing a regular user JWT:
   - `invite_participant(...)` → `complete_setup(client, data["setup_url"])` → `api_login(client, login, NEW_SECURE_PASSWORD)`.
3. For `test_auth_temp_password_restricted`: assert **403** on raw login with temp password (mirror `test_login_gate_enforce_true` in `test_auth_setup.py`); then `complete_setup` and verify predictions/change-password on **accepted** user.
4. For `test_me_contests_empty`: invite + complete-setup user with **no** contest enrollment, or use completed user not added to any contest.
5. For `test_contacts_temp_password`: rename intent — after complete-setup user has `is_temp_password=false`; test contacts on **setup-completed** invitee instead of seeded `temp_user`.
6. Reuse `NEW_SECURE_PASSWORD` from `stage_112_helpers.py`; do not duplicate setup token parsing.

**Acceptance:** All 9 tests pass under `stage_112_api` without setting `ENFORCE_PASSWORD_SETUP=false` globally.

---

### §2.2 — Leaderboard ETag after calculate (1 test) — **LOCKED: Option C**

**Problem:** `test_cache_etag_changes_after_calculate` expects anonymous `GET /rounds/2/leaderboard` → **200** after `calculate`. Stage 2.3.1 gates public round LB to **PUBLISHED** only; after calculate status is **CALCULATED** → visitor gets **403** `RESULTS_NOT_AVAILABLE`.

**Affected test:**

| ID | File | Test |
|----|------|------|
| API-CACHE-ETAG | `tests/api/test_calculate_smoke_1_3.py` | `test_cache_etag_changes_after_calculate` |

**Chosen strategy (C):** Verify ETag invalidation in **staff context** — SUPERVISOR/ADMIN may read round LB when status is **CALCULATED** (see `leaderboard_service._allowed_round_statuses`). Do **not** require publish for this test.

**Implementation notes:**

1. Keep `loaded_api` fixture; `ensure_contest_running` + supervisor login unchanged.
2. Replace anonymous GET with **authenticated** GET:
   - Prefer contest-scoped: `GET /api/v1/contests/1/rounds/{rid}/leaderboard` + `Authorization: Bearer {supervisor}`.
   - Legacy shim acceptable if contest_id=1 is default; contest-scoped preferred for 1.4 consistency.
3. Flow:
   - `first = GET .../leaderboard` with supervisor headers → expect **200** (round CLOSED or CALCULATED per loader state after ensure).
   - `POST .../calculate` with supervisor headers.
   - `second = GET .../leaderboard` with same headers → expect **200**.
   - If `first` had `ETag` header: assert `second.headers["etag"] != first.headers["etag"]`.
4. **Out of scope for this test:** visitor 403 before publish — cover separately in publish-gate tests (`test_leaderboard_published_only_2_3_1.py` or similar).
5. Update docstring: «ETag changes after calculate (staff view on CALCULATED round)».

**Acceptance:** Test passes without `publish` step; still validates cache/ETag bump on recalculate.

---

## 3. Pending decisions

(Items §2.3–§2.6 added after user selects fix option for each group.)

---

### §2.3 — Tiebreak / global leaderboard (2 tests) — **LOCKED: Option D**

**Problem:** Both tests use legacy `GET /api/v1/leaderboard` after `calculate` without `publish`. Global LB aggregates scores only from **PUBLISHED** rounds (`get_global_leaderboard` filters `Round.status == PUBLISHED`). With no published rounds in the test path, the leaderboard is empty or incomplete → `StopIteration` / `KeyError`.

**Affected tests:**

| ID | File | Test | Failure |
|----|------|------|---------|
| API-TB-DISPLAY | `test_contest_lifecycle_1_3.py` | `test_tiebreak_display_on_leaderboard` | `StopIteration` — shutov not in rows |
| API-TB-RANK | `test_contest_lifecycle_1_3.py` | `test_tiebreak_rank_synthetic` | `KeyError: 10` — user not in rank map |

**Additional drift:** Legacy `PUT /api/v1/admin/users/{uid}/exceptional-tiebreak` (deprecated); prefer contest-scoped `PUT /api/v1/contests/{id}/participants/{uid}/exceptional-tiebreak`.

**Chosen strategy (D — hybrid A + C):**

| Test | Approach |
|------|----------|
| `test_tiebreak_display_on_leaderboard` | **A:** calculate round 1 → **publish** round 1 → contest-scoped global LB |
| `test_tiebreak_rank_synthetic` | **C:** synthetic tied users in `stage_112_api` (or isolated fixture), not contracted shutov/volchenko |

**Implementation notes — display test (A part):**

1. Keep `loaded_api`; after calculate round 1: `POST /api/v1/contests/1/admin/rounds/{rid}/publish` (supervisor).
2. Replace legacy endpoints:
   - Tiebreak: `PUT /api/v1/contests/1/participants/{uid}/exceptional-tiebreak` (admin).
   - LB: `GET /api/v1/contests/1/leaderboard`.
3. Assert `exceptional_tiebreak_points == 3` on shutov row.

**Implementation notes — rank synthetic test (C part):**

1. Move to **`stage_112_api`** (or dedicated fixture): create draft contest, 2 accepted participants, one round with deterministic equal scores (same predictions → tied on keys 1–4).
2. Calculate + publish round; set exceptional tiebreak 10 vs 0 via contest-scoped PUT.
3. Assert higher tiebreak → better rank (`rank_high < rank_low`).
4. Remove dependency on contracted loader tie state and fragile `pytest.skip` on non-tied shutov/volchenko.
5. Reference tie-break rules: `agent_docs/contracts/leaderboard_tiebreakers.md` §2 key 5.

**Acceptance:** Both tests pass deterministically without relying on loader publish state or accidental ties in contracted CSV.

---

## 4. Pending decisions

(Items §2.4–§2.6 added after user selects fix option for each group.)

---

### §2.4 — Global LB count_* name lookup (1 test) — **LOCKED: Option D**

**Problem:** `test_lb_counts_global` fails with `KeyError: ' Ларин'` when indexing `rows` by constructed display name.

**Root causes (both must be fixed):**

1. **Name format:** Loader uses `name_split_strategy=last_name_only` → `first_name=""`, `last_name="Ларин"`. Test builds `f"{first_name} {last_name}"` → `" Ларин"` (leading space). API `user_name` from `_user_name_map` may differ or user absent from rows.
2. **PUBLISHED gate:** `calculate_rounds_via_http` calculates rounds 1–9 but does **not** publish. Global LB aggregates **PUBLISHED only** — without publish, `larin` may be missing from `rows` entirely.

**Affected test:**

| ID | File | Test |
|----|------|------|
| LB-COUNTS-GLOBAL | `tests/api/test_leaderboard_counts.py` | `test_lb_counts_global` |

**Chosen strategy (D — hybrid A + C):**

1. **Publish:** After `calculate_rounds_via_http`, publish rounds **1–9** (loop `POST .../admin/rounds/{rid}/publish` with supervisor token) — mirror pattern in `test_lb_counts_zero_user_omitted` (which publishes round 1).
2. **Lookup by user_id:** Replace name-keyed dict with `{r["user_id"]: r for r in resp.json()["leaderboard"]}`; resolve `larin.id` from DB; assert counts against `load_leaderboard()` CSV for login `larin`.

**Implementation notes:**

- Keep `loaded_api` and contracted CSV reference (`load_leaderboard()`).
- Do not change loader name strategy for this fix.
- Optional: add helper `publish_rounds_via_http(client, sf, contest_id, round_numbers)` in `conftest.py` if reused by §2.3 display test.

**Acceptance:** Test passes deterministically; count_* values match `leaderboard.csv` for larin by user_id.

---

## 5. Pending decisions

(Items §2.5–§2.6 added after user selects fix option for each group.)

---

### §2.5 — Contest delete soft-delete (1 test) — **LOCKED: Option C**

**Problem:** `test_contest_delete_ok` expects `DELETE` response `status == "DRAFT"` and DB contest `DRAFT`. Current API returns **`DELETED`** (`ContestDeleteResponse` schema) after soft-delete: wipe operational data, `reset_contest_to_draft`, set `deleted_at`.

**Affected test:**

| ID | File | Test |
|----|------|------|
| API-CONTEST-DELETE-OK | `tests/api/test_contest_lifecycle_1_3.py` | `test_contest_delete_ok` |

**Chosen strategy (C — hybrid A + B):** Migrate to **contest-scoped** delete + assert full **soft-delete contract**.

**Implementation notes:**

1. Replace legacy `DELETE /api/v1/admin/contest` with `DELETE /api/v1/contests/1` (admin token, body `{confirm: "DELETE"}`).
2. Keep `delete_api` fixture flow: RUNNING → pause → delete (instant allowed via `CONTEST_ALLOW_INSTANT_DELETE=true`).
3. **Response assertions:**
   - `status_code == 200`
   - `resp.json()["status"] == "DELETED"`
   - `resp.json()["deleted"] is True`
4. **DB assertions (async session):**
   - Contest row: `status == DRAFT`, `deleted_at is not None`, `is_locked == False`
   - Operational wipe: no rounds/teams/participants for contest_id (or counts == 0)
5. **List visibility:** `GET /api/v1/contests/deleted` (admin) includes contest id=1 with `restore_available` per training window.
6. Update docstring: «soft-delete → DELETED response; DB DRAFT + deleted_at; data wiped».
7. Legacy shim test coverage optional — non-blocking if contest-scoped path covered.

**Acceptance:** Test documents current product behaviour; no API change to return DRAFT in delete response.

---

## 6. Pending decisions

(Item §2.6 added after user selects fix option.)

---

### §2.6 — Auto-close vs deadline guard (1 unit test) — **LOCKED: Option D**

**Problem:** `test_batch_after_deadline_rejected` expects `ContestRuleError` matching `"истёк"` (`DEADLINE_PASSED`). With Stage **1.16** auto-close, `submit_batch` → `ensure_round_closed_if_expired` transitions ACTIVE + past deadline to **CLOSED** first → `ROUND_NOT_ACTIVE` / «активный тур (статус: CLOSED)».

**Affected test:**

| ID | File | Test |
|----|------|------|
| UNIT-BATCH-DEADLINE | `tests/unit/test_services_1_2.py` | `test_batch_after_deadline_rejected` |

**Chosen strategy (D — hybrid A + B):** Assert **`ROUND_NOT_ACTIVE`** (or message containing «активный тур» / «CLOSED»); document that auto-close runs before deadline guard.

**Implementation notes:**

1. Replace `pytest.raises(ContestRuleError, match="истёк")` with:
   ```python
   with pytest.raises(ContestRuleError) as exc_info:
       ...
   assert exc_info.value.code in ("ROUND_NOT_ACTIVE", "DEADLINE_PASSED")
   ```
   Prefer **`ROUND_NOT_ACTIVE`** as primary expected code after 1.16; accept `DEADLINE_PASSED` only if test setup bypasses auto-close in future.
2. Update docstring: «After 1.16 auto-close, expired ACTIVE round is CLOSED before submit_batch deadline check».
3. **Do not** change `submit_batch` / auto-close order to satisfy old message.
4. Optional separate unit test for raw `DEADLINE_PASSED` with mocked round still ACTIVE (out of scope unless requested).

**Acceptance:** Test passes and documents 1.16 interaction; no production code change.

---

## 3. Summary — all decisions locked

| § | Group | Tests | Option |
|---|-------|-------|--------|
| 2.1 | Password setup | 9 | **D** — stage_112_api + helpers |
| 2.2 | LB ETag | 1 | **C** — staff GET after calculate |
| 2.3 | Tiebreak | 2 | **D** — publish+global / synthetic |
| 2.4 | LB counts global | 1 | **D** — publish 1–9 + user_id lookup |
| 2.5 | Contest delete | 1 | **C** — contest-scoped soft-delete |
| 2.6 | Auto-close unit | 1 | **D** — ROUND_NOT_ACTIVE assertion |

**Total:** 15 tests. Follow-up: coder implements per §2; tester runs full `uv run pytest` green.
