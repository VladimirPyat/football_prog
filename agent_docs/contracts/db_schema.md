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
- **Note:** Exceptional tie-break points moved to `contest_participants` (Stage 1.4).

### 1.2 `contacts`
- `user_id`: INTEGER PRIMARY KEY REFERENCES `users(id)`
- `email`: VARCHAR NULL
- `vk_id`: VARCHAR NULL
- `tg_id`: VARCHAR NULL
- `notify_enabled`: BOOLEAN NOT NULL DEFAULT FALSE

### 1.3 `contests` (replaces `contest_settings`, Stage 1.4)
- `id`: INTEGER PRIMARY KEY
- `name`: VARCHAR NOT NULL
- `slug`: VARCHAR UNIQUE NULL
- `is_locked`: BOOLEAN NOT NULL DEFAULT FALSE — when TRUE, structural fields and `rules_json` are immutable
- `status`: VARCHAR NOT NULL DEFAULT 'DRAFT' (Enum: 'DRAFT', 'RUNNING', 'PAUSED', 'FINISHED')
- `paused_at`: TIMESTAMPTZ NULL — set when status becomes PAUSED
- `finished_at`: TIMESTAMPTZ NULL — set when status becomes FINISHED
- `total_teams`: INTEGER NOT NULL
- `matches_per_round`: INTEGER NOT NULL
- `total_rounds`: INTEGER NOT NULL
- `is_round_robin`: BOOLEAN NOT NULL
- `rules_json`: JSONB NOT NULL (scoring rules, bonuses, tiebreakers from `contest_defaults.json`)
- **Constraints**: `CHECK (status IN ('DRAFT','RUNNING','PAUSED','FINISHED'))`

### 1.4 `contest_participants` (Stage 1.4)
- `contest_id`: INTEGER NOT NULL REFERENCES `contests(id)` ON DELETE CASCADE
- `user_id`: INTEGER NOT NULL REFERENCES `users(id)`
- `status`: VARCHAR NOT NULL DEFAULT 'ACCEPTED' (Enum: 'PENDING', 'ACCEPTED')
- `exceptional_tiebreak_points`: INTEGER NOT NULL DEFAULT 0 — admin tie-break only (NOT contest rules; not frozen by `is_locked`)
- **Primary key**: `(contest_id, user_id)`
- **Constraints**: `CHECK (exceptional_tiebreak_points >= 0)`

### 1.5 `teams`
- `id`: INTEGER PRIMARY KEY
- `contest_id`: INTEGER NOT NULL REFERENCES `contests(id)` ON DELETE CASCADE
- `name`: VARCHAR NOT NULL
- `short_name`: VARCHAR NOT NULL
- `logo_url`: VARCHAR NULL
- **Constraints**: `UNIQUE (contest_id, name)`

### 1.6 `rounds`
- `id`: INTEGER PRIMARY KEY
- `contest_id`: INTEGER NOT NULL REFERENCES `contests(id)` ON DELETE CASCADE
- `number`: INTEGER NOT NULL
- `deadline`: TIMESTAMPTZ NOT NULL
- `status`: VARCHAR NOT NULL (Enum: 'DRAFT', 'ACTIVE', 'CLOSED', 'CALCULATED', 'PUBLISHED')
- `matches_count`: INTEGER NOT NULL DEFAULT 0
- `kind`: VARCHAR NOT NULL DEFAULT `'REGULAR'` (`REGULAR` | `SUPPLEMENTARY`)
- `supplementary_index`: INTEGER NULL — 1, 2, 3… for ДопТур labels (only when `kind=SUPPLEMENTARY`)
- **Constraints**: `UNIQUE (contest_id, number)`

### 1.7 `matches`
- `id`: INTEGER PRIMARY KEY
- `round_id`: INTEGER NOT NULL REFERENCES `rounds(id)`
- `origin_round_id`: INTEGER NULL REFERENCES `rounds(id)` — set when match moved to supplementary round
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

### 1.8 `predictions`
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

### 1.9 `scores`
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
- **Scoring scope:** row always references the **origin (regular) round** `round_id`.
  Matches played in supplementary (ДопТур) rounds add points to this same row via
  `matches.origin_round_id`. See [scoring_flow.md](scoring_flow.md) §6.
- **Constraints**:
  - `UNIQUE (user_id, round_id)`

## 2. Migration notes (Stage 1.4)

1. Create `contests` from legacy `contest_settings` row(s); default contest `id=1`, `name='Default'`.
2. Add `contest_id=1` to all existing `teams` and `rounds`.
3. Populate `contest_participants` from users; migrate `users.exceptional_tiebreak_points` → participant row.
4. Drop `contest_settings`; drop `users.exceptional_tiebreak_points`.
5. `load_test_data.py` seeds into contest `id=1` for backward-compatible integration tests.

## 3. Global Rules
- Use `uv add` for all package installations.
- All timestamps must be timezone-aware (`TIMESTAMPTZ`).
- CSV delimiter for any data import/export is `;` (teams.csv uses `,` per loader config).
