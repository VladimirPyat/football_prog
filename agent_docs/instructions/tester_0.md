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

### 2.3 Seed Data Verification
- Run the seed script (`python -m src.scripts.seed` or equivalent).
- Query the `contest_settings` table to verify that `rules_json` exactly matches the contents of `docs/test_data/config/contest_defaults.json`.
- Verify that structural limits (`total_teams`, `matches_per_round`, etc.) are correctly populated.

## 3. Reporting
- Create a test report at `agent_docs/reports/test_0.md`.
- **LANGUAGE RULE**: The report MUST be written in **RUSSIAN**.
- Detail the results of the migration tests, constraint validations, and seed data verification.
- Provide a clear verdict: whether Stage 0 is ready or requires fixes from `@Coder`.