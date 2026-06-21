# Coder Instructions — Stage 1.7: Leaderboard Counts & Invite Accept

> Status gate: `INSTRUCTIONS_READY`. **Prerequisite:** Stage 1.6 at `TEST_PASS` (1.8 may land before or after — no hard dependency).
> Plan: `agent_docs/plans/draft_1.7_frontend_prerequisites.md` §5.1–5.2, §6.1.
> **Language policy:** code comments English; HTTP `detail` Russian; handler docstrings Russian; manuals English.

## 1. Objective

Close two frontend blockers from `agent_docs/reports/BLOCKED.md`:

| ID | Change | Purpose |
|----|--------|---------|
| **B4** | Add `count_*` fields to leaderboard API (`ScoreDetailOut`) | Leaderboard columns: Точный кр. счёт / Точный счёт / Разница / Исход |
| **B6** | `PENDING→ACCEPTED` on password change + prediction guard | Participant invite lifecycle matches UI |

**Non-goals:** B1–B3 (1.8), B5 logo upload (1.9). No DB migrations.

## 2. Background

- `scores.count_exact_high`, `count_exact`, `count_diff`, `count_outcome` exist and are populated by scoring (`a2b3c4d5e6f7` migration).
- `leaderboard_service._score_to_user_round()` already reads counts; **serialization to HTTP response omits them**.
- `add_participant()` sets `ParticipantStatus.PENDING` + `is_temp_password=True`; `change_password()` clears temp flag but **never flips participant status**.
- PENDING users can POST predictions today but are excluded from scoring — guard closes the gap.

## 3. Scope — files you may create/modify

```
src/schemas/leaderboard.py              # +4 int fields on ScoreDetailOut
src/services/leaderboard_service.py     # add count_* to row dicts (round + global)
src/services/participant_service.py     # NEW — accept_pending_participations()
src/api/v1/auth.py                      # call accept on change_password
src/services/prediction_service.py      # ACCEPTED participant guard
src/core/exceptions.py                  # optional: document PARTICIPANT_NOT_ACCEPTED code
agent_docs/contracts/api_v1.yaml        # ScoreDetail schema + B6 flow note
manuals/API_GUIDE.md                    # Authentication + leaderboard sections
tests/api/test_leaderboard_counts.py    # NEW
tests/api/test_participant_accept.py    # NEW
agent_docs/progress/stage_1.md          # append handoff
```

**Do NOT modify:** `docs/`, `src/scoring/*` math, loader CSVs.

## 4. B4 — `ScoreDetailOut` extension

### 4.1 Schema (`src/schemas/leaderboard.py`)

Add to `ScoreDetailOut`:

```python
count_exact_high: int = 0
count_exact: int = 0
count_diff: int = 0
count_outcome: int = 0
```

### 4.2 Round leaderboard (`get_round_leaderboard`)

In the row dict built per `StandingRow`, map from the user's `Score` row for that round:

```python
"count_exact_high": sr.count_exact_high if sr else 0,
"count_exact": sr.count_exact if sr else 0,
"count_diff": sr.count_diff if sr else 0,
"count_outcome": sr.count_outcome if sr else 0,
```

### 4.3 Global leaderboard (`get_global_leaderboard`)

Map from aggregated `StandingRow` (already computed in `build_standings()`):

```python
"count_exact_high": row.exact_high_count,
"count_exact": row.exact_count,
"count_diff": row.diff_count,
"count_outcome": row.outcome_count,
```

Do **not** sum raw `Score` rows for global counts — use `StandingRow` tie-break aggregates (same as rank logic).

### 4.4 Contract (`api_v1.yaml`)

Extend `ScoreDetail` with the four integer fields (minimum 0). Bump `info.version` note in changelog comment only (full **1.2.0** after 1.9).

## 5. B6 — Invite accept flow

### 5.1 Service — `participant_service.py`

```python
async def accept_pending_participations(session: AsyncSession, user_id: int) -> int:
    """Flip all PENDING contest_participants rows to ACCEPTED for user. Returns rows updated."""
```

Use SQLAlchemy `update(ContestParticipant)` with `ParticipantStatus.PENDING` → `ACCEPTED`.

### 5.2 Auth hook (`auth.py` → `change_password`)

After `user.is_temp_password = False` (or only when it **was** `True` before change):

```python
await accept_pending_participations(session, user.id)
```

Call **before** `session.commit()`.

Document in docstring: «При смене временного пароля участник переводится в статус ACCEPTED во всех конкурсах.»

### 5.3 Prediction guard (`prediction_service.submit_batch`)

After contest/round validation, before writing predictions:

1. Load `ContestParticipant` for `(contest_id, user_id)`.
2. If missing → `ContestRuleError("Вы не участник этого конкурса", code="PARTICIPANT_NOT_ENROLLED")`.
3. If `status != ACCEPTED` → `ContestRuleError("Примите приглашение (смените временный пароль)", code="PARTICIPANT_NOT_ACCEPTED")`.

Import `ContestParticipant`, `ParticipantStatus` from `database.models`.

**Edge case:** SUPERVISOR/ADMIN without enrollment — guard applies to prediction submit only (they typically don't predict). No change to admin routes.

## 6. Documentation

### `manuals/API_GUIDE.md`

- **Authentication:** add bullet under temp-password flow — password change accepts all pending invites.
- **Leaderboard:** document four `count_*` fields on each leaderboard row.

### `api_v1.yaml`

Add to `ScoreDetail` properties. Optional description on `change-password` about participant acceptance.

## 7. Tests

### `tests/api/test_leaderboard_counts.py`

Use `loaded_api` + existing calculate/publish flow (see `test_calculate_leaderboard_1_4.py`).

| ID | Assertion |
|----|-----------|
| `[LB-COUNTS-ROUND]` | After published round, `GET .../rounds/{id}/leaderboard` — first row has all four `count_*` keys; at least one user with non-zero counts on contracted data |
| `[LB-COUNTS-GLOBAL]` | `GET .../leaderboard` — rows include `count_*`; values match sum semantics from `StandingRow` for a known user |
| `[LB-COUNTS-ZERO]` | User with no score row omitted from leaderboard (unchanged behaviour) |

### `tests/api/test_participant_accept.py`

Use `empty_api` (pattern from `test_setup_part_auth` in `test_operational_gaps_1_4.py`).

| ID | Assertion |
|----|-----------|
| `[ACCEPT-INVITE]` | Invite → login → change-password → `GET /participants` shows `status=ACCEPTED` |
| `[ACCEPT-PRED-GUARD]` | After invite, login with temp password **without** change-password → POST predictions → **403**, `code=PARTICIPANT_NOT_ACCEPTED` |
| `[ACCEPT-REG]` | Extend or re-run `[SETUP-PART-AUTH]` — after change-password, predictions still **200** |

## 8. Acceptance criteria

- [ ] Round and global leaderboard JSON include `count_exact_high`, `count_exact`, `count_diff`, `count_outcome`
- [ ] Global counts come from `StandingRow`, not naive DB sum
- [ ] `change_password` flips all PENDING participations to ACCEPTED
- [ ] PENDING (temp password) user cannot submit predictions
- [ ] ACCEPTED user can submit predictions (existing flow)
- [ ] `api_v1.yaml` ScoreDetail updated
- [ ] `pytest tests/ --ignore=tests/manual` green

## 9. OUT OF SCOPE

- Dedicated `POST /accept-invite` endpoint
- Email notifications on accept
- B1–B5 endpoints

## 10. Implementation order

1. `ScoreDetailOut` + `leaderboard_service` serialization
2. `participant_service.py` + `auth.py` hook
3. `prediction_service` guard
4. Tests
5. `api_v1.yaml` + `API_GUIDE.md`
6. Progress handoff

## 11. Handoff

Append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Coder (1.7 counts & invite accept)
- STATUS: READY_FOR_TEST
- Blockers: B4, B6
- Verified: pytest tests/ -> N passed
- Next: agent_docs/instructions/tester_1.7.md
```

## 12. Frontend hints (Stage 2.4 / 2.3)

| UI | API field / behaviour |
|----|----------------------|
| Leaderboard count columns | `count_exact_high`, `count_exact`, `count_diff`, `count_outcome` on each leaderboard row |
| Participant status badge | `GET /participants` → `ACCEPTED` after user completes password change |
