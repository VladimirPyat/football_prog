# Coder Instructions — Stage 1.16 Fix: Round Deadline Auto-Close (Backend)

> **Status gate:** `IMPLEMENTED`
> **Prerequisite:** Stage 1.4 auto-close hook (`round_auto_close_service.py`, `get_contest_context` in `deps.py`) shipped
> **Frontend counterpart:** `agent_docs/instructions/coder_2.3.5_fix_deadline.md`
> **Follow-up tester:** (optional) `tester_1.16_fix_deadline.md` / `tester_2.3.5_fix_deadline.md` when created
> **Related:** `agent_docs/contracts/contest_lifecycle_flow.md` §3.2–3.4, `manuals/API_GUIDE.md`, `manuals/STATUS_REFERENCE.md`
> **Language policy:** API `detail` Russian; code comments English

---

## 1. Objective

Fix gap where an **ACTIVE** round stays in DB after `deadline` until a contest-scoped request runs batch auto-close. This blocks supervisor **results entry** (`ROUND_NOT_CLOSED`) and confuses UI even though `submit_batch` already rejects predictions by time.

| ID | Problem | Target |
|----|---------|--------|
| **D1** | `ACTIVE` + past deadline until `GET /contests/{id}/rounds` | Per-round lazy close on every round-touching operation |
| **D2** | Legacy `/rounds` shims skip `ContestContext` | Round-level ensure covers shim paths |
| **D3** | `set_result` / `calculate` require `CLOSED` but status stale | Auto-close before status guards in services |
| **D4** | `API_GUIDE.md` omits auto-close guarantees | Document dual-layer policy |

**Non-goals:**

- Background scheduler / cron
- Changing deadline placement or 24h lockout rules
- Skipping `CLOSED` in the state machine (still required for calculate)

---

## 2. Root cause (verified)

| Layer | Today |
|-------|--------|
| `get_contest_context` | Calls `auto_close_expired_rounds(session, contest_id)` + `commit` — **contest-scoped routes only** |
| `submit_batch` | Blocks `now >= deadline` even if status still `ACTIVE` ✅ |
| `visible_predictions` | Full table when `now >= deadline` regardless of status ✅ |
| `set_result` / `calculate_round` | Require `round.status ∈ {CLOSED, CALCULATED}` — **fails** if auto-close not run ❌ |
| `GET /contests/{id}` | No auto-close |
| Legacy `GET /rounds` | No auto-close |

**Product requirement:** No predictions after deadline; predictions visible immediately after deadline; results entry possible immediately after deadline — **without manual «Закрыть тур»** and **without a scheduler**.

---

## 3. D1 — `ensure_round_closed_if_expired()` (LOCKED)

### 3.1 Location

Add to `src/services/round_auto_close_service.py` (or `round_service.py` if cleaner — prefer **one module** for all auto-close logic):

```python
async def ensure_round_closed_if_expired(
    session: AsyncSession,
    round_id: int,
    *,
    now: datetime | None = None,
) -> Round:
    """If round is ACTIVE and deadline <= now(UTC), transition to CLOSED. Idempotent."""
```

### 3.2 Semantics

| Condition | Action |
|-----------|--------|
| Round not found | Propagate `NotFoundError` |
| `status != ACTIVE` | Return round unchanged |
| `status == ACTIVE` and `now < deadline` | Return unchanged |
| `status == ACTIVE` and `now >= deadline` | `transition_round(..., CLOSED)`; return refreshed round |

Use same UTC normalization as `close_round` (naive deadline → `replace(tzinfo=UTC)`).

**Do not** raise if deadline not yet passed — callers keep existing validation.

### 3.3 Refactor batch hook

Update `auto_close_expired_rounds` to call `ensure_round_closed_if_expired` per ACTIVE round (DRY), or delegate to shared internal helper.

---

## 4. D2 — Call sites (mandatory)

Invoke `ensure_round_closed_if_expired(session, round_id)` **at the start** of each function below (after loading `round_id`, before status/deadline guards):

| Service | Function |
|---------|----------|
| `prediction_service.py` | `submit_batch`, `visible_predictions` |
| `match_service.py` | `set_result`, `change_status` (when round-scoped) |
| `scoring_persistence.py` | `calculate_round`, `recalculate_round` (if round_id known) |
| `leaderboard_service.py` | Round leaderboard / results builders that read round status |
| `api/handlers/predictions.py` | `build_round_predictions_view` — **before** loading matches |

**Order in `submit_batch`:**

1. `ensure_round_closed_if_expired`
2. Existing checks (`ACTIVE`, `now < deadline`, enrollment, batch completeness)

After step 1, expired rounds are `CLOSED` → step 2 returns `ROUND_NOT_ACTIVE` or `DEADLINE_PASSED` (either acceptable; prefer consistent `DEADLINE_PASSED` if `now >= deadline` even after close — optional polish).

**Order in `set_result`:**

1. Load match → round_id
2. `ensure_round_closed_if_expired`
3. Existing `now >= deadline` + `CLOSED|CALCULATED` checks

### 4.1 Transaction / commit

- Service functions **do not** commit; caller (router) commits.
- `get_contest_context` batch auto-close + commit **unchanged** (optimization for list endpoints).
- Per-round ensure in the same request session is sufficient for single-round mutations.

### 4.2 Legacy shims

`src/api/v1/predictions.py`, `src/api/v1/rounds.py` — no `ContestContext`; covered once handlers/services call `ensure_round_closed_if_expired`.

---

## 5. D3 — Behaviour matrix (acceptance)

| Operation | Before deadline, ACTIVE | After deadline, ACTIVE in DB |
|-----------|-------------------------|------------------------------|
| `POST …/predictions` | 200 | 403 `DEADLINE_PASSED` or `ROUND_NOT_ACTIVE` |
| `GET …/predictions` | Own scores only (USER) | Full table; `deadline_passed=true` |
| `PUT …/results` | 403 `DEADLINE_NOT_PASSED` | 200 after auto-close → `CLOSED` |
| `POST …/calculate` | 403 | 200 when matches terminal |
| `GET …/rounds` | `status=ACTIVE` | `status=CLOSED` (batch or prior ensure) |

---

## 6. Tests (pytest)

Add `tests/api/test_round_deadline_auto_close_1_16.py` (or extend `tests/unit/test_round_auto_close_1_4.py`):

| ID | Case |
|----|------|
| `[ENSURE-CLOSE]` | ACTIVE, deadline 1h ago → ensure → `CLOSED` |
| `[ENSURE-IDEM]` | Already `CLOSED` → no-op |
| `[ENSURE-FUTURE]` | ACTIVE, deadline +1h → unchanged |
| `[RESULT-AUTO-CLOSE]` | ACTIVE + past deadline → `set_result` succeeds (round closed inline) |
| `[PREDICT-BLOCK]` | After deadline → `submit_batch` 403 |
| `[PREDICT-VIEW]` | After deadline → `visible_predictions` full table |
| `[SHIM-PREDICT]` | Legacy `POST /rounds/{id}/predictions` after deadline → 403 |
| `[CALC-AFTER-DEADLINE]` | ACTIVE + past deadline → `calculate_round` after results → `CALCULATED` |

Use in-memory SQLite pattern from `test_round_auto_close_1_4.py`.

---

## 7. Contract & docs sync

| File | Change |
|------|--------|
| `agent_docs/contracts/contest_lifecycle_flow.md` §3.2 | Document **per-round ensure** + batch hook |
| `manuals/API_GUIDE.md` | New subsection **Auto-close (lazy)** — see §8 of this instruction |
| `manuals/STATUS_REFERENCE.md` | Cross-link if wording still says «only contest-scoped» |

---

## 8. API_GUIDE (verify during impl)

Section **Auto-close (lazy, no scheduler)** added to `manuals/API_GUIDE.md` under `round_service.py`. Keep in sync if function names or call sites change.

---

## 9. File checklist

| File | Change |
|------|--------|
| `src/services/round_auto_close_service.py` | `ensure_round_closed_if_expired`; refactor batch |
| `src/services/prediction_service.py` | Call ensure |
| `src/services/match_service.py` | Call ensure |
| `src/services/scoring_persistence.py` | Call ensure |
| `src/services/leaderboard_service.py` | Call ensure where round status matters |
| `src/api/handlers/predictions.py` | Call ensure in `build_round_predictions_view` |
| `tests/api/test_round_deadline_auto_close_1_16.py` | NEW |
| `agent_docs/contracts/contest_lifecycle_flow.md` | §3.2 update |
| `manuals/API_GUIDE.md` | Auto-close section |

---

## 10. Acceptance criteria

- [ ] ACTIVE round with past deadline auto-closes on prediction GET/POST, result PUT, calculate — not only on contest list
- [ ] Predictions blocked after deadline; full view after deadline
- [ ] Results entry works immediately after deadline without manual close button
- [ ] `auto_close_expired_rounds` still works via `ContestContext`
- [ ] `uv run pytest` new tests green; `uv run ruff check` on touched files

---

## 11. Execution order

```text
1. coder_1.16_fix_deadline.md (this) — backend
2. coder_2.3.5_fix_deadline.md       — frontend UI sync
3. manuals/API_GUIDE.md              — included in step 1
```
