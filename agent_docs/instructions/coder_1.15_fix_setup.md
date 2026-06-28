# Coder Instructions — Stage 1.15 Fix: Contest Start & Supervisor Delete (Backend)

> **Status gate:** `INSTRUCTIONS_READY`
> **Blocks:** `agent_docs/instructions/coder_2.3.3_fix_setup.md` (S1.12, S0.6, S1.4)
> **Prerequisite:** Stage 1.12 lifecycle + restore snapshot shipped (`coder_1.12_fix.md` B12)
> **Related:** `agent_docs/contracts/contest_lifecycle_flow.md`, `src/services/contest_lifecycle_service.py`, `src/services/contest_restore_service.py`
> **Follow-up tester:** `agent_docs/instructions/tester_2.3.3_fix_setup.md` (§5 API tests)
> **Language policy:** API `detail` Russian; code comments English

---

## 1. Objective

Support supervisor workflow where **contest start** is decoupled from **first tour activation**, and **supervisor can delete** a contest with **admin restore** within a time window.

| ID | Frontend ref | Problem | Target |
|----|--------------|---------|--------|
| **B1** | S1.12 | No way to set `RUNNING` + `is_locked` without activating a round | `POST /contests/{id}/start` |
| **B2** | S0.6 | Supervisor cannot delete DRAFT contest (`assert_deletable` requires PAUSED) | Allow safe delete from DRAFT (training mode) + snapshot |
| **B3** | S0.6 | Restore only in training mode; supervisor delete role gated | Document + test role matrix |
| **B4** | S1.12 | Purge PENDING tied to round activate only | Purge on **contest start** (same rules as first activate) |

**Non-goals:**

- Changing pause/resume/finish semantics for production ADMIN
- SMTP / invite flow changes
- Removing lock-on-activate for rounds (still set `is_locked` on activate if somehow still false — idempotent)

---

## 2. B1 — `POST /contests/{id}/start` (LOCKED)

### 2.1 Semantics

Transition **SETUP → OPERATIONAL** without requiring any round:

| Field | Before | After |
|-------|--------|-------|
| `status` | `DRAFT` | `RUNNING` |
| `is_locked` | `false` | `true` |

Side effects (same as first round activation today):

1. `purge_before_first_activation(session, contest_id)` — remove PENDING USER participants with temp password
2. Log audit event (if audit helper exists)

**Idempotent:** if already `RUNNING` and `is_locked`, return 200 current state (no error).

**Forbidden:**

- `PAUSED`, `FINISHED` → 409 with clear `detail`
- Already locked but still `DRAFT` (inconsistent DB) → fix to `RUNNING` or 409 — pick **fix forward** to `RUNNING` + log warning

### 2.2 Service function

Add to `contest_lifecycle_service.py`:

```python
async def start_contest(session: AsyncSession, contest_id: int) -> Contest:
    """DRAFT → RUNNING + lock; purge unconfirmed participants."""
```

Implementation sketch:

```python
contest = await get_contest(session, contest_id)
if contest.status == ContestLifecycleStatus.RUNNING and contest.is_locked:
    return contest
if contest.status != ContestLifecycleStatus.DRAFT:
    raise IllegalTransitionError(...)
await purge_before_first_activation(session, contest_id)
contest.is_locked = True
contest.status = ContestLifecycleStatus.RUNNING
return contest
```

### 2.3 Route

In `src/api/v1/contests.py`:

```python
@router.post("/{contest_id}/start", response_model=ContestLifecycleOut, dependencies=[_supervisor])
async def start(contest_id: int, session: DbSession) -> ContestLifecycleOut:
    """Запустить конкурс (DRAFT → RUNNING, блокировка структуры)."""
```

Response: same shape as pause/resume (`ContestLifecycleOut` with `status`, etc.).

### 2.4 Round activation adjustment

In `admin_rounds.py` activate handler:

- Keep `purge_before_first_activation` call (no-op when already RUNNING)
- Keep `ensure_running_on_first_activation` (no-op when already RUNNING)
- Keep `transition_round` → `is_locked=True` on ACTIVE (idempotent if already locked)

**Do not** double-purge on activate after start — `purge_before_first_activation` already returns 0 when not DRAFT.

### 2.5 Tests (pytest)

| ID | Case | Expected |
|----|------|----------|
| `[START-DRAFT]` | POST start on DRAFT | 200, `RUNNING`, `is_locked=true` |
| `[START-PURGE]` | PENDING participant on DRAFT → start | PENDING removed, ACCEPTED kept |
| `[START-IDEM]` | POST start twice | 200, no error |
| `[START-DRAFT-PATCH]` | PATCH structure after start | 403 CONTEST_LOCKED |
| `[START-ACTIVATE]` | Start then activate DRAFT round | 200 activate, predictions allowed when ACTIVE |
| `[START-FORBIDDEN]` | start on PAUSED/FINISHED | 409 |

Add API test file: `tests/api/test_contest_start_1_15.py`

---

## 3. B4 — Purge timing

Today: purge runs in activate path only. After B1, purge runs on **start**.

Update `agent_docs/contracts/contest_lifecycle_flow.md`:

```text
DRAFT ──(POST /start)──► RUNNING + is_locked
DRAFT ──(first round activate)──► RUNNING + is_locked   [legacy path if start skipped]
```

Recommend single entry: **`start_contest`** is canonical; activate assumes contest already RUNNING or still DRAFT (backward compat: activate from DRAFT still works without prior start — **keep both paths** for API clients until frontend fully migrated).

---

## 4. B2 — Supervisor delete from DRAFT (LOCKED)

### 4.1 Current blocker

`assert_deletable()` requires `contest.status == PAUSED`. Fresh DRAFT contests cannot be deleted — supervisor must run contest, pause, wait grace — unusable for test cleanup.

### 4.2 New policy

Extend `assert_deletable(session, contest_id, *, instant: bool = False, allow_draft: bool = False)`:

| Condition | Delete allowed |
|-----------|----------------|
| `status == PAUSED` + grace elapsed (or `instant`) | ✅ existing |
| `status == DRAFT` + `allow_draft=True` | ✅ **instant**, no pause/grace |
| `status == RUNNING` | ❌ must pause first (unchanged) |
| `status == FINISHED` | ❌ or allow ADMIN only — **unchanged** (FINISHED not deletable) |

Set `allow_draft=True` when:

```python
settings.supervisor_training_mode or settings.contest_allow_instant_delete
```

And caller role is SUPERVISOR+ (existing deps).

### 4.3 Snapshot + wipe

Existing `delete_contest_data()` → `save_restore_snapshot()` → `reset_contest_to_draft()` — **reuse**. DRAFT delete still wipes operational data and resets contest shell (teams, rounds, participants cleared).

Confirm dialog body unchanged: `confirm: "DELETE"`.

### 4.4 Tests

| ID | Case | Expected |
|----|------|----------|
| `[DELETE-DRAFT-TRAIN]` | SUPERVISOR + training mode, DRAFT delete | 200, soft-delete, snapshot row |
| `[DELETE-DRAFT-PROD]` | SUPERVISOR + training off, DRAFT delete | 200, soft-delete (not 403) |
| `[DELETE-RUNNING]` | RUNNING without pause | 409/403 not paused |
| `[RESTORE-AFTER-DRAFT-DEL]` | delete DRAFT → restore within window | teams/participants back |

Extend `tests/api/test_contest_restore.py` or new file.

---

## 5. B3 — Role matrix (document) [UPDATED post soft-delete]

Update `manuals/API_GUIDE.md`:

| Endpoint | SUPERVISOR | ADMIN |
|----------|------------|-------|
| `POST …/start` | ✅ | ✅ |
| `DELETE …` DRAFT | ✅ (instant, soft-delete) | ✅ |
| `DELETE …` PAUSED | ✅ (+ grace unless instant) | ✅ |
| `POST …/finish` | ✅ only if `supervisor_training_mode` | ✅ always |
| `POST …/restore` | ❌ | ✅ (within window) |

Config defaults in `config/settings.py` — **not** duplicated in `.env.example`.

---

## 6. Schema / OpenAPI

- `ContestLifecycleOut` already sufficient for start response
- Add path to `agent_docs/contracts/api_v1.yaml`:

```yaml
/contests/{contest_id}/start:
  post:
    summary: Start contest (lock structure, RUNNING)
```

---

## 7. File checklist

| File | Change |
|------|--------|
| `src/services/contest_lifecycle_service.py` | `start_contest`, `assert_deletable` DRAFT branch |
| `src/api/v1/contests.py` | `POST /{id}/start` |
| `src/api/v1/admin_rounds.py` | Comments / idempotent purge |
| `tests/api/test_contest_start_1_15.py` | NEW |
| `tests/api/test_contest_restore.py` | DRAFT delete + restore |
| `agent_docs/contracts/contest_lifecycle_flow.md` | Start transition |
| `manuals/API_GUIDE.md` | Endpoint table |

---

## 8. Acceptance criteria

- [ ] `POST /api/v1/contests/{id}/start` on DRAFT → RUNNING + locked; purges PENDING
- [ ] PATCH teams/participants/structure after start → 403
- [ ] SUPERVISOR can DELETE DRAFT in training mode; snapshot + restore within window
- [ ] Round activate still works before or after start (backward compat)
- [ ] `uv run ruff check src/`, `uv run mypy src/`, `uv run bandit -r src/ -ll`, pytest new tests green

---

## 8. Execution order vs frontend

```text
1. This backend instruction (1.15 fix setup)
2. coder_2.3.3_fix_setup.md (frontend wires POST /start + delete UI)
3. Manual QA: S1.4, S1.12, S0.6 in SUPERVISOR_TESTING_SCENARIOS.md
```
