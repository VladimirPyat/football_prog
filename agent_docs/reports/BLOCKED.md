# Blockers Report

## Status table (Stage 2.3)

| ID | Status | Summary |
|----|--------|---------|
| B1–B6 | RESOLVED | See prior stage reports / `frontend_api_integration.md` |
| B7 | **OPEN** | SQLite retains legacy global `UNIQUE` on `rounds.number` after migration `c4d5e6f7a8b9` |
| B8 | **OPEN** | SQLite retains legacy global `UNIQUE` on `teams.name` (same migration gap) |

---

### OPEN — B7: Multi-contest round creation fails (global `rounds.number` UNIQUE)

- **Why:** E2E `[E2E-SUPERVISOR-CREATE-ROUND]`, API `POST /api/v1/contests/{id}/admin/rounds` returns `500 INTERNAL_ERROR`. SQLite indexes: `sqlite_autoindex_rounds_1` UNIQUE(`number`) **and** `sqlite_autoindex_rounds_2` UNIQUE(`contest_id`,`number`). Inserting round `number=1` for contest `id=2` violates legacy index.
- **Evidence:** `IntegrityError: UNIQUE constraint failed: rounds.number` on `INSERT INTO rounds (contest_id, number, …) VALUES (2, 1, …)`.
- **Blocks:** 2.3 fresh-contest round flows (create/activate/24h/results pipeline), 2.4 if multi-contest E2E needed.
- **Fallback:** Tests limited to loaded contest `id=1` only; cannot validate SETUP→round lifecycle on fresh contests.
- **Required fix (@Coder/backend):** Alembic migration must **drop** legacy global UNIQUE on `rounds.number` when adding `uq_rounds_contest_number`; document `dev_setup.py --ensure-running-only` in tester bootstrap.

---

### OPEN — B8: Team create returns 500 on duplicate name across contests

- **Why:** E2E `[E2E-ADMIN-SETUP]` API helper `addTeam` with name `E2E Team 1` → `500`. `IntegrityError: UNIQUE constraint failed: teams.name`.
- **Evidence:** Legacy `sqlite_autoindex_teams_1` UNIQUE(`name`) coexists with `uq_teams_contest_name`.
- **Blocks:** 2.3 SETUP E2E on fresh contests when names collide with loaded CSV teams.
- **Fallback:** E2E uses unique suffixed team names (test-side); API should return `409` not `500`.
- **Required fix (@Coder/backend):** Drop global `teams.name` UNIQUE in migration; map `IntegrityError` → `409` in `contest_teams.py`.
