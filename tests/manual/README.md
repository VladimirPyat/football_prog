# Manual verification scripts (Stage 1.4)

Two-phase verification for Stage 1 sign-off. Scripts do **not** modify reference CSVs under `docs/test_data/contracted/`.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./football_verify.db` | Target database |
| `CONTEST_ID` | `1` | Contest for Script 2 comparison |
| `API_BASE_URL` | `http://test` | ASGI client base (Script 1 in-process) |
| `VERIFY_BOOTSTRAP` | `load` | Script 1 mode: `load` or `empty` |

## Script 1 — HTTP drive (`verify_via_api.py`)

Builds or loads a contest, runs contest-scoped calculate (rounds 1–9 when using loader), smoke-tests public GET endpoints. **Does not read `expected_scores.csv`.**

```bash
uv run alembic upgrade head
uv run python tests/manual/verify_via_api.py --bootstrap load
# or full HTTP setup (slower):
uv run python tests/manual/verify_via_api.py --bootstrap empty --database-url sqlite+aiosqlite:///./football_e2e.db
```

Exit code `0` on success.

## STOP — DBeaver

Inspect the SQLite file from `DATABASE_URL` (read-only). Check `predictions`, `matches`, `scores`, `rounds.status`.

## Script 2 — DB vs CSV (`compare_db_vs_reference.py`)

Read-only comparison: `scores` vs `expected_scores.csv` (90/90), aggregates vs `leaderboard.csv` (10/10).

```bash
uv run python tests/manual/compare_db_vs_reference.py --contest-id 1 --database-url sqlite+aiosqlite:///./football_verify.db
```

## CANARY

Copy `expected_scores.csv` to a temp file, change one `expected_total`, point Script 2 at it with `--expected-scores`. Must fail. Revert → pass.

## Pytest equivalents

```bash
uv run pytest tests/api/test_calculate_leaderboard_1_4.py -v
uv run pytest tests/api/test_canary_scoring_1_4.py -v
```
