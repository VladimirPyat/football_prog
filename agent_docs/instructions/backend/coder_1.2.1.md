# Coder Instructions — Stage 1.2.1: Contest Lifecycle Migration (ONLY)

> Prerequisite: Stage 1.2 at `TEST_PASS`. Gate for Stage 1.3 augment. **No service/API
> logic changes** — schema + model fields only.

## 1. Objective
Add contest lifecycle columns to `contest_settings` and admin exceptional tie-break
storage on `users`. Enables Stage 1.3 immutability guards and safe contest delete.

## 2. Scope — files ONLY
```
src/database/models.py
alembic/versions/<rev>_contest_lifecycle_and_tiebreak.py
agent_docs/contracts/db_schema.md          # sync §1.1 users + §1.8 contest_settings
tests/unit/test_migration_1_2_1.py       # optional smoke (upgrade/downgrade)
```

Do **NOT** modify `round_service`, `prediction_service`, `match_service`, loaders, or API.

## 3. Migration spec

### 3.1 `contest_settings` — lifecycle (Option B)
| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `status` | VARCHAR NOT NULL | `'DRAFT'` | Enum: `DRAFT`, `RUNNING`, `PAUSED`, `FINISHED` |
| `paused_at` | TIMESTAMPTZ NULL | NULL | Set on pause |
| `finished_at` | TIMESTAMPTZ NULL | NULL | Set on early finish |

**Backfill:** `UPDATE contest_settings SET status = 'RUNNING' WHERE is_locked = TRUE`.

Add CHECK: `status IN ('DRAFT','RUNNING','PAUSED','FINISHED')`.

### 3.2 `users` — exceptional tie-break (NOT contest rules)
| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `exceptional_tiebreak_points` | INTEGER NOT NULL | `0` | Admin-entered; criterion 5 only |

Add CHECK: `exceptional_tiebreak_points >= 0`.

**Semantics:** Operational tie-break for the rare case when criteria 1–4 are identical.
This is **not** part of `rules_json` and is **not** frozen by `is_locked`.

### 3.3 Model
Add `ContestLifecycleStatus` StrEnum on `ContestSettings`. Map new columns on
`ContestSettings` and `User`.

## 4. Tests
- `uv run alembic upgrade head` → exit 0
- `uv run alembic downgrade -1` → exit 0 (then re-upgrade)
- Existing `tests/unit/test_services_1_2.py` still green (no behaviour change)

## 5. Acceptance
- Migration applies on empty DB and on DB loaded via `load_test_data.py`
- `db_schema.md` updated
- No changes to 1.2 service behaviour

## 6. Handoff
Append to `agent_docs/progress/stage_1.md`:
```
## YYYY-MM-DD — Coder (1.2.1)
- STATUS: READY_FOR_TEST
- Files: models.py, alembic migration, db_schema.md
- Verified: alembic upgrade/downgrade; pytest tests/unit/test_services_1_2.py green
```
