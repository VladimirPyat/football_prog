# Tester Instructions: Stage 0 (Database & Configuration)

## 1. Objective
Verify the database schema, constraints, migrations, and seed data implemented by `@Coder`. You should receive minimally working code that strictly adheres to the contracts.

## 2. Tasks

### 2.1 Migration Verification
- Run `alembic upgrade head` to ensure the database schema applies cleanly.
- Run `alembic downgrade base` to ensure the rollback logic is correct.
- Re-run `alembic upgrade head` to prepare the DB for further tests.

### 2.2 Integration / Constraint Verification
Run the test suite provided by `@Coder` (e.g., `pytest tests/`) and verify the following edge cases are covered and passing:
- **Missing vs Zero**: Ensure that a missing prediction is stored as `NULL` and not `0`. Inserting `0` must be treated as a valid score.
- **Score Limits**: Ensure `CHECK` constraints block scores `< 0` and `> 20`.
- **Unique Constraints**: Ensure duplicate predictions (`user_id, round_id, match_id`) are rejected.
- **Team Constraints**: Ensure a match cannot have `team1_id == team2_id`.

## 2.3 Integration Flow (Realistic Data Lifecycle)
Test the schema with actual data patterns that Stage 1 will use. Use `sqlite+aiosqlite:///:memory:` for speed.

| ID | Test | Steps | Expected |
|---|---|---|---|
| **IF-01** | **Full Round Lifecycle** | 1. Seed contest & settings.<br>2. Insert 16 teams (from `teams.csv` subset).<br>3. Create `round 1`.<br>4. Insert 8 matches with `status='SCHEDULED'`, `score1/2=None`.<br>5. Insert predictions for 10 users × 8 matches (batch insert).<br>6. Update 2 matches to `status='FINISHED'` with real scores.<br>7. Query joined data: `user.login, match.id, pred.score1, match.score1`. | All inserts succeed. FK relations resolve correctly. NULL scores stay NULL for scheduled matches. Join query returns 80 rows exactly. |
| **IF-02** | **Batch Prediction Uniqueness** | 1. Insert full prediction set for user `volchenko` in round 1.<br>2. Try to insert duplicate `(user_id, round_id, match_id)` for one match.<br>3. Try to insert partial batch (only 5 of 8 matches). | Duplicate raises `IntegrityError`. Partial insert succeeds (app-layer batch validation is Stage 1, DB only enforces UNIQUE). |
| **IF-03** | **Match Result Update & Cascade Safety** | 1. Take match from IF-01.<br>2. Update `status='FINISHED'`, `score1=2, score2=1`.<br>3. Try to delete the contest.<br>4. Query predictions linked to this match. | Update succeeds. Contest delete raises `IntegrityError` (due to `RESTRICT` on teams) or cascades as designed. Predictions remain intact (ON DELETE CASCADE on match_id should NOT delete predictions if match is just updated). |
| **IF-04** | **Leaderboard Query Readiness** | Run a complex aggregation query that mimics Stage 1 scoring prep:<br>`SELECT u.login, COUNT(p.id) as total_preds, SUM(CASE WHEN p.score1=m.score1 AND p.score2=m.score2 THEN 1 ELSE 0 END) as exact_hits FROM users u JOIN predictions p ON ... LEFT JOIN matches m ON ... WHERE p.round_id=1 GROUP BY u.id` | Query executes without errors. Returns correct counts. Indexes on `ix_predictions_user_round` and `ix_matches_round_id` are used (verify with `EXPLAIN QUERY PLAN` if possible). |

### 2.4 Seed Data Verification
- Run the seed script (`python -m src.scripts.seed` or equivalent).
- Query the `contest_settings` table to verify that `rules_json` exactly matches the contents of `docs/test_data/config/contest_defaults.json`.
- Verify that structural limits (`total_teams`, `matches_per_round`, etc.) are correctly populated.

## 3. Reporting
- Create a test report at `agent_docs/reports/test_0.md`.
- **LANGUAGE RULE**: The report MUST be written in **RUSSIAN**.
- Detail the results of the migration tests, constraint validations, and seed data verification.
- Provide a clear verdict: whether Stage 0 is ready or requires fixes from `@Coder`.
