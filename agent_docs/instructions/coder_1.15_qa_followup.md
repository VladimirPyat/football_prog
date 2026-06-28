# Coder Instructions — Stage 1.15 QA Follow-up (Backend, chat-driven)

> **Status gate:** `IMPLEMENTED` (manual QA chat 2026-06-28; not part of `coder_1.15_fix_setup.md`)
> **Prerequisite:** `agent_docs/instructions/coder_1.15_fix_setup.md` shipped (`POST /start`, DRAFT delete policy)
> **Frontend counterpart:** `agent_docs/instructions/coder_2.3.4_qa_followup.md`
> **Follow-up tester:** `agent_docs/instructions/tester_2.3.4_qa_followup.md`
> **Related contracts:** `agent_docs/contracts/scoring_flow.md` §6, `agent_docs/contracts/bonus_rules.md`, `agent_docs/contracts/db_schema.md`, `agent_docs/contracts/api_v1.yaml`
> **Language policy:** API `detail` Russian; code comments English

---

## 1. Objective

Capture **backend** changes made during supervisor manual QA (2026-06-28) via ad-hoc chat prompts — **outside** the scoped `coder_1.15_fix_setup.md` instruction.

| ID | QA / chat topic | Problem | Target |
|----|-----------------|---------|--------|
| **Q1** | S0.6 soft-delete | Deleted contests still listed; no retention purge | `deleted_at` column, list filter, purge script |
| **Q2** | S1.12 start guards | Contest starts with incomplete teams/participants | `validate_contest_start_readiness()` before `start_contest()` |
| **Q3** | S1.11 dev workflow | Bulk confirm awkward; password required every run | `dev_invite_setup.py list-pending`; auto password from `SEED_SUPERVISOR_PASSWORD` |
| **Q4** | Manual QA | No quick reference after `dev_setup` | Cheatsheet printed by `dev_setup.py` |
| **Q5** | Free / supplementary tours | «Тур N» label wrong for postponed matches | `Round.kind`, `supplementary_index`, `Match.origin_round_id` |
| **Q6** | Postponement scoring | Bonuses applied before all logical-tour matches played | `bonuses_pending` on leaderboard API; scoring contract (engine deferred) |

**Non-goals (this instruction):**

- Re-implementing `POST /start` or DRAFT delete from `coder_1.15_fix_setup.md`
- Full deferred bonus2/3 recalc in scoring engine (contract only — see §6.3)
- SMTP / production invite flow

---

## 2. Q1 — Contest soft-delete & purge

### 2.1 Schema

Migration `alembic/versions/f7a8b9c0d1e2_contest_soft_delete.py`:

| Column / change | Semantics |
|-----------------|-----------|
| `contests.deleted_at` | `NULL` = visible; timestamp = soft-deleted |
| List endpoints | Exclude rows where `deleted_at IS NOT NULL` (supervisor picker, discovery) |

### 2.2 Delete behaviour

On `DELETE /contests/{id}`:

1. Existing snapshot + wipe flow unchanged
2. Set `deleted_at = now()` on contest shell (do not hard-delete row)
3. Contest hidden from `GET /contests` and supervisor lists

### 2.3 Hard purge (ops)

| File | Role |
|------|------|
| `src/services/contest_purge_service.py` | Select contests past retention window |
| `src/scripts/purge_deleted_contests.py` | CLI for cron / manual ops |
| `config/settings.py` | `contest_purge_retention_seconds` (default documented in `manuals/CONFIG.md`) |

### 2.4 Tests

`tests/api/test_contest_soft_delete.py` — list filter, delete sets `deleted_at`, restore clears it.

---

## 3. Q2 — Start readiness validation

### 3.1 Rules (LOCKED)

Before `start_contest()` transitions DRAFT → RUNNING:

| Check | Error (Russian `detail`) |
|-------|--------------------------|
| `COUNT(teams) == contest.total_teams` | «Для запуска нужно добавить все команды: создано X из Y» |
| `COUNT(participants WHERE status=ACCEPTED) >= 2` | «Для запуска нужно минимум 2 принятых участника» |

Constants: `MIN_ACCEPTED_PARTICIPANTS_FOR_START = 2` in `contest_lifecycle_service.py`.

PENDING participants are still purged **after** validation passes (existing purge-on-start).

### 3.2 API

`POST /contests/{id}/start` returns **422** (`ValidationError`) when checks fail.

### 3.3 Tests

Extend `tests/api/test_contest_start_1_15.py`:

| ID | Case |
|----|------|
| `[START-TEAMS]` | Fewer teams than `total_teams` → 422 |
| `[START-PARTICIPANTS]` | 0–1 ACCEPTED → 422 |
| `[START-READY]` | Full teams + ≥2 ACCEPTED → 200 |
| `[START-RULES]` | `rules_json` persisted and returned after start (if PATCH before start) |

Helper: `tests/api/stage_112_helpers.py` → `fulfill_start_prerequisites()`.

---

## 4. Q3 — `dev_invite_setup.py` improvements

### 4.1 `list-pending`

```bash
uv run python src/scripts/dev_invite_setup.py list-pending [--contest-id ID]
```

Prints pending invites (contest id, email, token hint) for manual QA workflow S1.11.

### 4.2 Auto password

`_resolve_confirm_password()` reads `SEED_SUPERVISOR_PASSWORD` from `.env` when `--password` omitted (same pattern as bootstrap scripts).

### 4.3 Tests

`tests/api/test_dev_invite_setup.py` — list-pending output, password resolution.

### 4.4 Docs

`manuals/DEV_SETUP.md` — Workflow B: invite → `list-pending` → `confirm-all --contest-id ID`.

---

## 5. Q4 — Manual QA cheatsheet

After successful `dev_setup.py` (full stack or `--run-only` when already provisioned), print a short cheatsheet:

- Login URLs / default users
- `dev_invite_setup.py` commands
- `alembic upgrade head` reminder when migrations pending

Implementation: `_print_manual_qa_cheatsheet()` in `src/scripts/dev_setup.py`.

---

## 6. Q5 — Supplementary (free) tour metadata

### 6.1 Schema

Migration `alembic/versions/g8h9i0j1k2l3_supplementary_rounds.py`:

| Model field | Values |
|-------------|--------|
| `Round.kind` | `REGULAR` \| `SUPPLEMENTARY` |
| `Round.supplementary_index` | 1, 2, 3… per contest (ДопТур sequence) |
| `Match.origin_round_id` | FK → round where match was postponed from |

`create_free_tour()` sets `kind=SUPPLEMENTARY`, increments `supplementary_index`, links postponed matches via `origin_round_id`.

### 6.2 API enrichment

`src/services/round_serialization.py` → `rounds_to_out()`:

- `kind`, `supplementary_index`
- `source_round_numbers: int[]` — distinct origin round numbers for matches in this supplementary round

`GET /contests/{id}/rounds` returns enriched `RoundOut`.

### 6.3 Restore snapshot

`contest_restore_service.py` — persist/restore `kind`, `supplementary_index`, `origin_round_number` in snapshot JSON.

### 6.4 Tests

Extend `tests/api/test_free_tour_1_4.py` for supplementary metadata and `source_round_numbers`.

---

## 7. Q6 — Postponement scoring & `bonuses_pending`

### 7.1 Logical tour unit

A **logical tour** = origin round + all matches with `origin_round_id` pointing to that round (excluding `CANCELED` / `VOID` from “all played” wait).

`scores.round_id` always references the **origin** round.

### 7.2 Base vs bonus timing (contract)

| Phase | Scoring |
|-------|---------|
| Main matches of origin round finished | Base points + bonus1 may apply |
| Postponed matches still pending | bonus2/bonus3 **deferred** until all non-canceled logical-tour matches have results |

Documented in `agent_docs/contracts/scoring_flow.md` §6 and `bonus_rules.md`.

### 7.3 API flag (implemented)

`src/services/round_scoring_pending.py` — `is_bonuses_pending(session, round_id)`.

`LeaderboardOut` extended:

```yaml
bonuses_pending: boolean
bonuses_pending_message: string | null  # Russian UI hint
```

`leaderboard_service.py` sets fields on round leaderboard responses.

### 7.4 Engine (deferred — not in this chat impl)

`calculate_round` / scoring engine does **not** yet skip bonus2/3 when pending. Frontend shows note from API; full engine alignment is a follow-up task.

### 7.5 Tests

`tests/services/test_round_scoring_pending.py` — pending detection matrix.

---

## 8. Migrations note

Migrations **do not** run on uvicorn reload. After pull:

```bash
uv run alembic upgrade head
```

Includes at minimum: `f7a8b9c0d1e2` (soft delete), `g8h9i0j1k2l3` (supplementary rounds).

---

## 9. File checklist

| File | Change |
|------|--------|
| `alembic/versions/f7a8b9c0d1e2_contest_soft_delete.py` | NEW |
| `alembic/versions/g8h9i0j1k2l3_supplementary_rounds.py` | NEW |
| `src/database/models.py` | `deleted_at`, round kind fields, `origin_round_id` |
| `src/services/contest_lifecycle_service.py` | `validate_contest_start_readiness`, soft-delete on wipe |
| `src/services/contest_discovery_service.py` | Filter `deleted_at` |
| `src/services/contest_purge_service.py` | NEW |
| `src/services/round_serialization.py` | NEW — `rounds_to_out()` |
| `src/services/round_scoring_pending.py` | NEW |
| `src/services/leaderboard_service.py` | `bonuses_pending` fields |
| `src/services/contest_restore_service.py` | Supplementary snapshot fields |
| `src/schemas/leaderboard.py`, `src/schemas/rounds.py` | New response fields |
| `src/scripts/dev_invite_setup.py` | `list-pending`, auto password |
| `src/scripts/dev_setup.py` | QA cheatsheet |
| `src/scripts/purge_deleted_contests.py` | NEW |
| `config/settings.py` | `contest_purge_retention_seconds` |
| `tests/api/test_contest_soft_delete.py` | NEW |
| `tests/api/test_contest_start_1_15.py` | Readiness + rules |
| `tests/api/test_dev_invite_setup.py` | list-pending |
| `tests/api/test_free_tour_1_4.py` | Supplementary metadata |
| `tests/services/test_round_scoring_pending.py` | NEW |
| `tests/api/stage_112_helpers.py` | `fulfill_start_prerequisites()` |
| `agent_docs/contracts/*`, `manuals/DEV_SETUP.md`, `manuals/API_GUIDE.md` | Sync |

---

## 10. Acceptance criteria

- [ ] Soft-deleted contests hidden from lists; purge script respects retention
- [ ] Start blocked until teams full and ≥2 ACCEPTED participants
- [ ] `dev_invite_setup.py list-pending` + env password work
- [ ] Supplementary rounds expose `kind`, `supplementary_index`, `source_round_numbers`
- [ ] Leaderboard returns `bonuses_pending` when logical tour incomplete
- [ ] `uv run alembic upgrade head` applies new migrations
- [ ] `uv run pytest` on files in §9 green; `uv run ruff check src/` on touched files

---

## 11. Execution order

```text
1. coder_1.15_fix_setup.md          (POST /start baseline)
2. coder_1.15_qa_followup.md (this) — chat QA backend
3. coder_2.3.4_qa_followup.md       — matching frontend
```
