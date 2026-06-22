# Tester Instructions — Stage 1.7: Leaderboard Counts & Invite Accept

> Status gate: @Coder `READY_FOR_TEST` for 1.7. **Prerequisite:** Stage 1.6 at `TEST_PASS`.
> Reference: `instructions/coder_1.7.md`, `plans/draft_1.7_frontend_prerequisites.md` §7.1.
> Independent of 1.8 / 1.9 test status.

## 1. Objective

Verify Stage 1.7 closes blockers **B4** (leaderboard `count_*`) and **B6** (invite accept + prediction guard):

1. Leaderboard responses expose four count fields with correct values.
2. Password change flips participant `PENDING → ACCEPTED`.
3. PENDING users cannot submit predictions; ACCEPTED users can (regression).
4. Contract + docs updated.
5. Full regression green.

**Non-goals:** B1–B3, B5, frontend E2E, re-run CANARY manual scripts.

## 2. Scope — files you may create

```
tests/api/test_leaderboard_counts.py    # extend if gaps
tests/api/test_participant_accept.py
agent_docs/reports/test_1.7.md          # NEW — Russian report
```

**Do NOT modify** `src/` unless Coder blocker (document in report).

## 3. B4 — Leaderboard counts

Use `loaded_api` fixture (contracted loader DB, contest id=1).

### 3.1 `[LB-COUNTS-ROUND]`

1. Pick a **PUBLISHED** round with scores (e.g. round from existing leaderboard tests).
2. `GET /api/v1/contests/1/rounds/{rid}/leaderboard` (no auth required).

Assert for each row in `leaderboard`:

- Keys present: `count_exact_high`, `count_exact`, `count_diff`, `count_outcome`
- All values are `int >= 0`
- At least one row has non-zero counts on contracted data (sanity — historical CSVs have counts)

Optional cross-check: compare one user's counts to DB `scores` row for that round via `sf` fixture.

### 3.2 `[LB-COUNTS-GLOBAL]`

`GET /api/v1/contests/1/leaderboard`

Same key presence. Pick user with multiple scored rounds — global `count_*` should reflect **aggregated** standings (from `StandingRow`), not a single round's row.

### 3.3 `[LB-COUNTS-REG]`

Re-run subset:

```bash
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -q
```

Rank order and ETag behaviour unchanged.

## 4. B6 — Invite accept

Use `empty_api` (same flow as `[SETUP-PART-AUTH]`).

### 4.1 `[ACCEPT-INVITE]`

1. Supervisor creates contest, 16 teams, invites participant.
2. Login with temp password → `change-password` → 200.
3. `GET /contests/{cid}/participants` as supervisor → invited user `status == "ACCEPTED"`.

### 4.2 `[ACCEPT-PRED-GUARD]`

After invite, before password change:

1. Login with temp password.
2. Supervisor creates + activates round (minimal 8 matches).
3. Invitee `POST .../predictions` → **403**.
4. Response `code == "PARTICIPANT_NOT_ACCEPTED"` (or documented equivalent).

### 4.3 `[ACCEPT-REG]`

Full `[SETUP-PART-AUTH]` path: after change-password, predictions → **200**.

Run existing test if present:

```bash
uv run pytest tests/api/test_operational_gaps_1_4.py::test_setup_part_auth -q
```

### 4.4 `[ACCEPT-ME-CONTESTS]` (optional, if 1.8 merged)

Invitee `GET /me/contests` → `participant_status == "ACCEPTED"` after password change.

## 5. Documentation audit

| ID | Check |
|----|-------|
| `[DOC-CONTRACT]` | `api_v1.yaml` `ScoreDetail` has four `count_*` properties |
| `[DOC-API-GUIDE]` | Temp-password / accept flow and count fields documented |

## 6. Regression (mandatory)

```bash
uv run pytest tests/ --ignore=tests/manual -q
```

## 7. Report (`agent_docs/reports/test_1.7.md`)

Russian summary. Table:

| ID | Result | Notes |
|----|--------|-------|
| `[LB-COUNTS-ROUND]` | PASS/FAIL | |
| `[LB-COUNTS-GLOBAL]` | PASS/FAIL | |
| `[LB-COUNTS-REG]` | PASS/FAIL | |
| `[ACCEPT-INVITE]` | PASS/FAIL | |
| `[ACCEPT-PRED-GUARD]` | PASS/FAIL | |
| `[ACCEPT-REG]` | PASS/FAIL | |
| `[DOC-*]` | PASS/FAIL | |
| Regression | PASS/FAIL | N passed |

Verdict: **TEST_PASS** / **TEST_FAIL**.

## 8. Progress update

On **TEST_PASS**, append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Tester (1.7)
- STATUS: TEST_PASS
- Blockers verified: B4, B6
- Report: agent_docs/reports/test_1.7.md
```

## 9. OUT OF SCOPE

- `[ME-*]`, `[PUBLIC-*]`, `[CONTACTS-*]`, `[LOGO-*]`
- Updating `BLOCKED.md` to RESOLVED (wait for full 1.7–1.9 bundle or user request)
