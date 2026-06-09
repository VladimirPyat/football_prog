# Database Schema Contract

## 1. Tables Overview

### 1.1 `users`
- `id`: INTEGER PRIMARY KEY
- `login`: VARCHAR UNIQUE NOT NULL
- `password_hash`: VARCHAR NOT NULL
- `role`: VARCHAR NOT NULL (Enum: 'SUPERVISOR', 'ADMIN', 'USER')
- `first_name`: VARCHAR NOT NULL
- `last_name`: VARCHAR NOT NULL
- `is_temp_password`: BOOLEAN NOT NULL DEFAULT FALSE

### 1.2 `contacts`
- `user_id`: INTEGER PRIMARY KEY REFERENCES `users(id)`
- `email`: VARCHAR NULL
- `vk_id`: VARCHAR NULL
- `tg_id`: VARCHAR NULL
- `notify_enabled`: BOOLEAN NOT NULL DEFAULT FALSE

### 1.3 `teams`
- `id`: INTEGER PRIMARY KEY
- `name`: VARCHAR UNIQUE NOT NULL
- `short_name`: VARCHAR NOT NULL
- `logo_url`: VARCHAR NULL

### 1.4 `rounds`
- `id`: INTEGER PRIMARY KEY
- `number`: INTEGER UNIQUE NOT NULL
- `deadline`: TIMESTAMPTZ NOT NULL
- `status`: VARCHAR NOT NULL (Enum: 'DRAFT', 'ACTIVE', 'CLOSED', 'CALCULATED', 'PUBLISHED')
- `matches_count`: INTEGER NOT NULL DEFAULT 0

### 1.5 `matches`
- `id`: INTEGER PRIMARY KEY
- `round_id`: INTEGER NOT NULL REFERENCES `rounds(id)`
- `team1_id`: INTEGER NOT NULL REFERENCES `teams(id)`
- `team2_id`: INTEGER NOT NULL REFERENCES `teams(id)`
- `date_time`: TIMESTAMPTZ NOT NULL
- `score1`: INTEGER NULL
- `score2`: INTEGER NULL
- `status`: VARCHAR NOT NULL (Enum: 'SCHEDULED', 'POSTPONED', 'CANCELED', 'VOID', 'FINISHED')
- **Constraints**: 
  - `CHECK (team1_id != team2_id)`
  - `CHECK (score1 IS NULL OR (score1 >= 0 AND score1 <= 20))`
  - `CHECK (score2 IS NULL OR (score2 >= 0 AND score2 <= 20))`

### 1.6 `predictions`
- `id`: INTEGER PRIMARY KEY
- `user_id`: INTEGER NOT NULL REFERENCES `users(id)`
- `round_id`: INTEGER NOT NULL REFERENCES `rounds(id)`
- `match_id`: INTEGER NOT NULL REFERENCES `matches(id)`
- `score1`: INTEGER NULL
- `score2`: INTEGER NULL
- **Constraints**:
  - `UNIQUE (user_id, round_id, match_id)`
  - `CHECK (score1 IS NULL OR (score1 >= 0 AND score1 <= 20))`
  - `CHECK (score2 IS NULL OR (score2 >= 0 AND score2 <= 20))`
- **Note**: Missing prediction must be represented by the absence of a row or `NULL` values, never as `0`.

### 1.7 `scores`
- `id`: INTEGER PRIMARY KEY
- `user_id`: INTEGER NOT NULL REFERENCES `users(id)`
- `round_id`: INTEGER NOT NULL REFERENCES `rounds(id)`
- `points_exact`: INTEGER NOT NULL DEFAULT 0
- `points_diff`: INTEGER NOT NULL DEFAULT 0
- `points_outcome`: INTEGER NOT NULL DEFAULT 0
- `bonus1`: INTEGER NOT NULL DEFAULT 0
- `bonus2`: INTEGER NOT NULL DEFAULT 0
- `bonus3`: INTEGER NOT NULL DEFAULT 0
- `total_without_bonus3`: INTEGER NOT NULL DEFAULT 0
- `total_with_bonus3`: INTEGER NOT NULL DEFAULT 0
- `correct_outcomes`: INTEGER NOT NULL DEFAULT 0
- **Constraints**:
  - `UNIQUE (user_id, round_id)`

### 1.8 `contest_settings`
- `id`: INTEGER PRIMARY KEY
- `is_locked`: BOOLEAN NOT NULL DEFAULT FALSE
- `total_teams`: INTEGER NOT NULL
- `matches_per_round`: INTEGER NOT NULL
- `total_rounds`: INTEGER NOT NULL
- `is_round_robin`: BOOLEAN NOT NULL
- `rules_json`: JSONB NOT NULL (Stores scoring rules, bonuses, tiebreakers from `contest_defaults.json`)

## 2. Global Rules
- Use `uv add` for all package installations.
- All timestamps must be timezone-aware (`TIMESTAMPTZ`).
- CSV delimiter for any data import/export is `;`.
