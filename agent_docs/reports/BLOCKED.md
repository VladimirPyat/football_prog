# Blockers Report

## Status table (Stage 2.3)

| ID | Status | Summary |
|----|--------|---------|
| B1–B6 | RESOLVED | See prior stage reports / `frontend_api_integration.md` |
| B7 | **RESOLVED** ✅ | Migration `d5e6f7a8b9c0` — legacy global UNIQUE on `rounds.number` dropped; re-verified 2026-06-25 (`[FIX-B7-*]` pytest) |
| B8 | **RESOLVED** ✅ | Same migration — legacy global UNIQUE on `teams.name` dropped; IntegrityError → 409; re-verified 2026-06-25 (`[FIX-B8-*]` pytest) |
| **B11** | **RESOLVED** ✅ | Auth setup links, invite `setup_url`, purge on start, dev scripts — verified 2026-06-27 (`test_1.12_fix`, 25/25 pytest) |
| **B12** | **RESOLVED** ✅ | Supervisor training mode (finish/delete/restore), snapshot restore — verified 2026-06-27 (`test_1.12_fix`) |

---

## Resolved appendix

### B7: Multi-contest round creation fails (global `rounds.number` UNIQUE)

- **Root cause:** Migration `c4d5e6f7a8b9` added per-contest `uq_rounds_contest_number` but retained singleton-era `sqlite_autoindex_rounds_1` UNIQUE(`number`).
- **Fix:** `d5e6f7a8b9c0_drop_legacy_global_uniques.py` recreates `rounds` with composite unique only.
- **Verified:** `[FIX-B7-ROUND]`, `[FIX-B7-DUP-IN-CONTEST]` pytest green; post-migration indexes: `rounds` → `['contest_id', 'number']` only.

### B8: Team create returns 500 on duplicate name across contests

- **Root cause:** Legacy `sqlite_autoindex_teams_1` UNIQUE(`name`) coexisted with `uq_teams_contest_name`.
- **Fix:** Same migration drops global `teams.name` unique; `ConflictError` (409) handler for remaining `IntegrityError` UNIQUE violations.
- **Verified:** `[FIX-B8-TEAM]`, `[FIX-B8-DUP-IN-CONTEST]` pytest green; post-migration indexes: `teams` → `['contest_id', 'name']` only.

### B11: Participant accept + password setup via signed link

- **Deliverables:** `setup-preview`, `complete-setup`, `request-password-reset`; invite returns `setup_url`; purge PENDING on first activate; `dev_invite_setup.py`.
- **Fix (post-test):** Purge moved before `is_locked` in `activate_round`; purge removes all PENDING USER rows.
- **Verified:** `tests/api/test_auth_setup.py`, `test_participant_purge.py`, `test_dev_invite_setup.py`, `test_participant_accept.py` — 25/25 green (2026-06-27).

### B12: Supervisor lifecycle + training mode

- **Deliverables:** `supervisor_training_mode` enables SUPERVISOR finish/delete/restore; `contest_restore_snapshots` + `POST …/restore` within window.
- **Verified:** `tests/api/test_contest_restore.py` — pause/finish/delete/restore gates green (2026-06-27).

---

### Historical evidence (pre-fix)

**B7 evidence:** `IntegrityError: UNIQUE constraint failed: rounds.number` on `INSERT INTO rounds (contest_id, number, …) VALUES (2, 1, …)`.

**B8 evidence:** `IntegrityError: UNIQUE constraint failed: teams.name` when creating `"E2E Team 1"` in contest 2 while contest 1 had same name.
