# Contest Lifecycle Flow — SETUP vs RUNNING

> Authoritative operational matrix for Stage 1.4+. Complements `api_v1.yaml` and `db_schema.md`.
> Source: `docs/04_supervisor_scenario.md`, user chat decisions 2026-06-21.

## 1. Contest status machine

```
DRAFT ──(first round activate)──► RUNNING ──(POST pause)──► PAUSED
                                    │                         │
                                    │                    (POST resume)
                                    │                         │
                                    └──(POST finish)──► FINISHED ◄──┘
```

| Status | Phase | `is_locked` | Meaning |
|--------|-------|-------------|---------|
| `DRAFT` | SETUP | `false` | Contest being configured; structural CRUD allowed |
| `RUNNING` | OPERATIONAL | `true` (after first activate) | Predictions, rounds, results, calculate |
| `PAUSED` | OPERATIONAL (frozen) | `true` | No mutating ops; public GET OK; required before safe delete |
| `FINISHED` | TERMINAL | `true` | Read-only; recalculate (ADMIN) still allowed |

**First activation side effects:** `contests.is_locked = true`, `contests.status: DRAFT → RUNNING`.

## 2. SETUP vs RUNNING — who can do what

| Operation | SETUP (`DRAFT`, `!is_locked`) | RUNNING / PAUSED / FINISHED (`is_locked`) |
|-----------|--------------------------------|-------------------------------------------|
| `POST /contests` | ✅ ADMIN/SUPERVISOR | ✅ (new contest starts in DRAFT) |
| `PATCH /contests/{id}` (structure, `rules_json`) | ✅ | ❌ 403 ContestLocked |
| CRUD teams | ✅ | ❌ 403 |
| CRUD participants, send invite | ✅ | ❌ 403 |
| Create round (DRAFT) | ✅ | ✅ (pairs from existing teams only) |
| Activate round | ✅ (locks on first activate) | ✅ |
| PATCH round/matches (pre-deadline rules) | N/A until RUNNING | ✅ per 24h / match-count rules |
| POST predictions | ❌ until RUNNING + ACTIVE round | ✅ while RUNNING, ACTIVE, `now < deadline` |
| POST close / auto-close | N/A | ✅ when `now >= deadline` |
| PUT match result | ❌ | ✅ only `now >= deadline`, contest RUNNING, round CLOSED* |
| POST calculate | ❌ | ✅ round must be CLOSED |
| POST publish | ❌ | ✅ round CALCULATED |
| PUT exceptional-tiebreak on participant | ✅ (no effect until scored) | ✅ **allowed** (operational, not rules) |
| POST pause / resume / finish | ❌ from DRAFT (finish → 409) | ✅ ADMIN |
| DELETE contest (safe delete) | ❌ | ✅ PAUSED + grace |

\*If round still ACTIVE at deadline, **auto-close** (sync hook) or explicit **close** must run first so status becomes CLOSED before results.

## 3. Round lifecycle

```
DRAFT ──(activate)──► ACTIVE ──(deadline passed: auto-close OR POST close)──► CLOSED
                                                                                    │
                                                                         (POST calculate)
                                                                                    ▼
                                                                              CALCULATED
                                                                                    │
                                                                         (POST publish)
                                                                                    ▼
                                                                              PUBLISHED
```

### 3.1 Transitions

| From | To | Trigger | Guard |
|------|-----|---------|-------|
| DRAFT | ACTIVE | `POST .../activate` | Valid matches; contest not PAUSED/FINISHED |
| ACTIVE | CLOSED | Auto-close OR `POST .../close` | `now >= deadline` |
| CLOSED | CALCULATED | `POST .../calculate` | All matches terminal (FINISHED/VOID/CANCELED); predictions scored |
| CALCULATED | PUBLISHED | `POST .../publish` | — |
| CALCULATED | CALCULATED | VOID on match | Atomic recalculate |

Illegal: skip states (e.g. ACTIVE → CALCULATED), mutate PUBLISHED round structure.

### 3.2 Auto-close (sync, no BackgroundTasks)

**Batch hook:** `auto_close_expired_rounds(session, contest_id)`

- Invoked at the start of every contest-scoped API handler (via `ContestContext` in `deps.py`).
- Select rounds where `contest_id = ? AND status = ACTIVE AND deadline <= now(UTC)`.
- For each: `ensure_round_closed_if_expired` → `transition_round(session, round_id, CLOSED)`.
- Commits when any round closed (see `get_contest_context`).

**Per-round hook:** `ensure_round_closed_if_expired(session, round_id)` [NEW 1.16]

- Called at the start of prediction, result, calculate, and leaderboard services for a specific round.
- Covers legacy shims (`GET/POST /rounds/…` without `contest_id`) and single-round mutations without a prior list fetch.
- Idempotent; same DB transaction as the caller when possible.

**Explicit close:** `POST /api/v1/contests/{contest_id}/admin/rounds/{id}/close`

- Requires `status = ACTIVE` and `now >= deadline`; else 400.
- Sets `CLOSED` (same as auto-close).

### 3.3 Predictions window

| Condition | POST predictions |
|-----------|------------------|
| `contest.status = RUNNING` | Allowed |
| `round.status = ACTIVE` | Allowed |
| `now < round.deadline` | Allowed |
| Any of above fails | 403 |

GET predictions visibility: pre-deadline — own scores only for USER and SUPERVISOR; ADMIN sees all (support). Anonymous callers receive **403** `PREDICTIONS_NOT_PUBLIC`. Post-deadline — full table for everyone (including anonymous). Aligns with `docs/03_user_scenarios.md` §4.

### 3.4 Results window

| Condition | PUT match result |
|-----------|------------------|
| `contest.status = RUNNING` | Allowed |
| `round.status = CLOSED` | Allowed (auto-close ensures this after deadline) |
| `now >= round.deadline` | Allowed |
| Round ACTIVE and `now >= deadline` | Auto-closed inline via `ensure_round_closed_if_expired` before guard [UPDATED 1.16] |

Calculate requires `round.status = CLOSED` (not ACTIVE).

**Admin UI matrix (effective status, match «Идёт», per-page actions):** [admin_ui_status_matrix.md](admin_ui_status_matrix.md)

## 4. Free Tour (operational exception)

**Endpoint:** `POST /api/v1/contests/{contest_id}/admin/rounds/free-tour`

| Rule | Detail |
|------|--------|
| Contest phase | RUNNING (`is_locked`) |
| Source matches | Status must be `POSTPONED` |
| Teams | Readonly — taken from source match |
| Action | Create new round; **move** matches (`UPDATE round_id`); set new `date_time` |
| Round number | `max(number)+1` within contest |
| Source rounds | Decrement `matches_count`; validate min matches if needed |
| Round metadata | `kind=SUPPLEMENTARY`, `supplementary_index` (ДопТур1, 2, …); `matches.origin_round_id` set on move |
| Scoring | Logical tour = origin round + moved matches; `scores` row stays on **origin** `round_id` — see [scoring_flow.md](scoring_flow.md) §6, [bonus_rules.md](bonus_rules.md) |

Activation of free-tour round follows normal activate flow (does not re-lock contest).

## 5. Multi-contest isolation

- All contest data scoped by `contest_id` on `contests`, `teams`, `rounds`, `contest_participants`.
- `users` global; participation per contest via `contest_participants`.
- Leaderboard / results / predictions filtered by contest (via round → contest).
- Lifecycle (pause/finish/delete) applies to **one** contest row.
- Safe delete wipes only that contest's teams, rounds, matches, predictions, scores, participants — not other contests or global users.

## 6. Legacy API shims (Stage 1.3 regression)

Paths without `/contests/{contest_id}/` resolve **default contest**:

1. Single contest in DB → that id.
2. Else first `status = RUNNING`.
3. Else lowest `id`.

Shims are **deprecated**; new clients must use contest-scoped paths.

## 7. Exceptional tie-break (unchanged semantics from 1.3)

- **Not** contest rules; stored on `contest_participants.exceptional_tiebreak_points`.
- ADMIN may set **after** `is_locked = true`.
- Criterion 5 when keys 1–4 tie; see `leaderboard_tiebreakers.md`.
- API: `PUT .../contests/{contest_id}/participants/{user_id}/exceptional-tiebreak`.
