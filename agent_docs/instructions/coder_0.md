# Coder Instructions: Stage 0 (Database & Configuration)

## 1. Objective
Implement the database foundation for the Football Predictions application. This includes setting up SQLAlchemy models, Alembic migrations, and a seed script to load initial configuration.

## 2. Dependencies
Use `uv add` to install the required packages. Do NOT use `pip install` or `poetry add`.
- `uv add sqlalchemy alembic asyncpg aiosqlite pydantic pydantic-settings`
- `uv add --dev pytest pytest-asyncio`

## 3. Tasks

### 3.1 SQLAlchemy Models
Create the models in `src/database/models.py` (or a similar structure) according to the schema defined in `agent_docs/contracts/db_schema.md`.
- **CRITICAL RULE**: A missing prediction or match score MUST be represented as `NULL` (i.e., `None` in Python), NEVER as `0`. Zero is a valid score in football.
- **CRITICAL RULE**: Enforce `CHECK` constraints on `score1` and `score2` to be between 0 and 20 (inclusive) OR `NULL`.
- **CRITICAL RULE**: Enforce `UNIQUE` constraints (e.g., `user_id, round_id, match_id` in `predictions`).
- **CRITICAL RULE**: Enforce `CHECK (team1_id != team2_id)` in `matches`.
- Use `TIMESTAMPTZ` for all datetime fields.
- Use `JSONB` (or `JSON` for SQLite compatibility during dev) for `rules_json` in `contest_settings`.

### 3.2 Alembic Migrations
- Initialize Alembic (`alembic init -t async alembic`).
- Configure `alembic.ini` and `env.py` to support async SQLAlchemy and load your models.
- Generate the initial migration: `alembic revision --autogenerate -m "Initial schema"`.

### 3.3 Seed Script
- Create a script (e.g., `src/scripts/seed.py`) that reads `docs/test_data/config/contest_defaults.json`.
- Insert the JSON data into the `contest_settings` table.
- Create an initial ADMIN user (from configuration or hardcoded defaults for dev).

### 3.4 Unit Tests & Edge Cases (CRITICAL)
You MUST write unit tests for the database models and constraints using `pytest` and `pytest-asyncio` (e.g., in `tests/unit/test_db_models.py`).
- Test that inserting `score1=0, score2=0` succeeds.
- Test that inserting `score1=None, score2=None` (missing prediction) succeeds.
- Test that inserting `score1=-1` or `score1=25` raises an IntegrityError (due to CHECK constraints).
- Test that inserting a match where `team1_id == team2_id` raises an IntegrityError.
- Test that inserting duplicate predictions for the same user, round, and match raises an IntegrityError.

## 4. Completion
Once completed, verify that your tests pass and update `agent_docs/progress/stage_0.md` with your status. The code must be minimally working and return expected results for `@Tester`.