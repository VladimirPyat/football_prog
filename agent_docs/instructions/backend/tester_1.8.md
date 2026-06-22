# Tester Instructions — Stage 1.8: Contest Discovery & User Contacts

> Status gate: @Coder `READY_FOR_TEST` for 1.8. **Prerequisite:** Stage 1.6 at `TEST_PASS`.
> Reference: `instructions/coder_1.8.md`, `plans/draft_1.7_frontend_prerequisites.md` §7.2.
> **Note:** 1.8 does not require 1.7/1.9 to be implemented first.

## 1. Objective

Verify Stage 1.8 **contest discovery and user contacts** API (blockers B1–B3):

1. **B1** — `GET /me/contests` for enrolled users.
2. **B2** — `GET /contests/public` for anonymous Visitor (RUNNING only).
3. **B3** — `GET/PATCH /auth/me/contacts` with upsert and invite email inheritance.
4. **Docs & contract** — `api_v1.yaml` v1.2.0-rc, `API_GUIDE.md`.
5. **Regression** — full automated suite green.

**Non-goals:** B4 leaderboard counts, B6 invite accept, B5 logo upload, frontend E2E.

## 2. Scope — files you may create

```
tests/api/test_me_contests.py           # extend if Coder left gaps
tests/api/test_contests_public.py
tests/api/test_contacts.py
agent_docs/reports/test_1.8.md          # NEW — Russian report with [TEST-ID] table
```

You may **extend** `tests/api/conftest.py` with helpers (e.g. `_create_contest_with_status`).

**Do NOT modify** `src/` unless Coder left a blocker (document in report).

## 3. API tests — B1 `/me/contests`

Use `empty_api` for isolated setup; `loaded_api` optional for regression on real loader data.

### 3.1 `[ME-CONTESTS-USER]`

Setup (`empty_api`):

1. Login as `supervisor_api`.
2. `POST /contests` → `cid`.
3. `POST /contests/{cid}/participants` with `{email, first_name, last_name}`.
4. Login as invitee with returned `temp_password` (or change password if 1.7 already landed — not required for this test).
5. `GET /api/v1/me/contests` with invitee token.

Assert:

- HTTP 200
- `len(body) == 1`
- `body[0]["id"] == cid`
- `body[0]["participant_status"] == "PENDING"` (or `"ACCEPTED"` if 1.7 merged)
- `body[0]["role"] == "USER"`
- `body[0]["status"]` matches contest lifecycle (likely `"DRAFT"` before activate)

### 3.2 `[ME-CONTESTS-EMPTY]`

Create USER via DB or API without enrolling in any contest → `GET /me/contests` → **200**, `[]`.

### 3.3 `[ME-CONTESTS-RBAC]`

`GET /api/v1/me/contests` without Authorization → **401**.

### 3.4 `[ME-CONTESTS-MULTI]` (optional)

Enroll same user in two contests → list length 2, ordered by name ascending.

### 3.5 `[ME-CONTESTS-NO-SUPERVISOR-LIST]` (optional)

`supervisor_api` not enrolled in contest → `GET /me/contests` → `[]` (organizer uses `GET /contests`, not `/me/contests`).

## 4. API tests — B2 `/contests/public`

### 4.1 `[PUBLIC-LIST]`

In `empty_api`, create four contests and set statuses:

| Contest | Target status | Visible in public? |
|---------|---------------|-------------------|
| A | DRAFT | No |
| B | RUNNING | **Yes** |
| C | PAUSED | No |
| D | FINISHED | No |

Use admin API (`pause`, `finish`, activate first round for RUNNING) or direct DB update via `sf` fixture if lifecycle setup is heavy.

`GET /api/v1/contests/public` (no auth):

- HTTP 200
- IDs returned == `{B.id}` only
- Each item has `id`, `name`, `status == "RUNNING"`

### 4.2 `[PUBLIC-NO-AUTH]`

Same request without Bearer → 200 (not 401).

### 4.3 `[PUBLIC-ROUTE-ORDER]` (optional smoke)

`GET /contests/public` must not 404 or match `contest_id="public"` — confirms route registered before `/{contest_id}`.

### 4.4 `[PUBLIC-LOADER]` (optional)

On `loaded_api`, if default contest is RUNNING, public list includes contest id=1.

## 5. API tests — B3 `/auth/me/contacts`

### 5.1 `[CONTACTS-GET-DEFAULT]`

USER with no `contacts` row → `GET /auth/me/contacts`:

```json
{ "email": null, "vk_id": null, "tg_id": null, "notify_enabled": false }
```

### 5.2 `[CONTACTS-PATCH]`

As authenticated USER:

```http
PATCH /api/v1/auth/me/contacts
{ "vk_id": "@myvk", "notify_enabled": true }
```

Then GET → `vk_id == "@myvk"`, `notify_enabled == true`, `email` still null.

Second PATCH `{ "email": "user@example.com" }` → GET reflects email.

### 5.3 `[CONTACTS-INVITE]`

After participant invite (§3.1 step 3–4), invitee `GET /auth/me/contacts` → `email` equals invite email.

### 5.4 `[CONTACTS-TEMP-PW]`

Use `temp_user` fixture user (`is_temp_password=true` in conftest) or fresh invitee before password change:

- GET contacts → 200
- PATCH `{ "tg_id": "123" }` → 200

Must **not** return 403 «Смените временный пароль…» (unlike prediction POST).

### 5.5 `[CONTACTS-VALIDATION]` (optional)

PATCH `{ "email": "not-an-email" }` → **400**, `code == "VALIDATION_ERROR"`.

### 5.6 `[CONTACTS-CLEAR-EMAIL]` (optional)

PATCH `{ "email": null }` or empty string (if Coder supports) → email cleared.

## 6. Documentation audit (read-only)

| Check | Pass criteria |
|-------|---------------|
| `[DOC-CONTRACT]` | `api_v1.yaml` version `1.2.0-rc`; paths `/me/contests`, `/contests/public`, `/auth/me/contacts` |
| `[DOC-API-GUIDE]` | `manuals/API_GUIDE.md` documents all three features; temp-password note for contacts |
| `[DOC-BLOCKED]` | B1–B3 still listed in `BLOCKED.md` until full 1.7–1.9 bundle resolves (expected) |

## 7. Regression (mandatory)

After 1.8-specific tests pass:

```bash
uv run pytest tests/ --ignore=tests/manual -q
```

Expect: all green (1.6 baseline + new tests).

Quick smoke:

```bash
uv run pytest tests/api/test_setup_phase_1_4.py tests/api/test_admin_users.py -q
```

## 8. Report template (`agent_docs/reports/test_1.8.md`)

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[ME-CONTESTS-USER]` | PASS/FAIL | |
| `[ME-CONTESTS-EMPTY]` | PASS/FAIL | |
| `[ME-CONTESTS-RBAC]` | PASS/FAIL | |
| `[PUBLIC-LIST]` | PASS/FAIL | |
| `[PUBLIC-NO-AUTH]` | PASS/FAIL | |
| `[CONTACTS-GET-DEFAULT]` | PASS/FAIL | |
| `[CONTACTS-PATCH]` | PASS/FAIL | |
| `[CONTACTS-INVITE]` | PASS/FAIL | |
| `[CONTACTS-TEMP-PW]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Regression | PASS/FAIL | N passed |

Verdict: **TEST_PASS** / **TEST_FAIL** with blockers for @Coder.

On **TEST_PASS**, note for frontend team:

- B1/B2/B3 endpoints ready for Stage 2.1 integration.
- Public list = **RUNNING only** (PAUSED/FINISHED excluded by design).
- `/me/contests` includes global `role`, not per-contest role.

## 9. Progress update

On **TEST_PASS**, append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Tester (1.8)
- STATUS: TEST_PASS
- Blockers verified: B1, B2, B3
- Report: agent_docs/reports/test_1.8.md
- Contract: api_v1.yaml v1.2.0-rc
- Next: Coder 1.7 or 1.9 per user schedule; frontend 2.1 can start API integration
```

## 10. Explicitly OUT OF SCOPE

- `[LB-COUNTS-*]`, `[ACCEPT-*]`, `[LOGO-*]` (stages 1.7 / 1.9)
- Playwright / frontend tests
- Re-run CANARY manual scoring scripts
- Updating `BLOCKED.md` to RESOLVED (wait until 1.7–1.9 complete or user request)
