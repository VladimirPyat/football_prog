# Fix 1.18 — Leaderboard: cumulative standings, predictions_count, total_bonus_points

**Renamed from** `fix_1.17_leaderboard_cumulative.md` (original 1.17 was `results[].points` — already shipped).
**Source:** manual QA of frontend stage 2.4 (leaderboard tab).
**Prerequisite for frontend:** `agent_docs/instructions/fix_2.4.1.md`.
**Scope:** backend only.

---

## 1. Symptoms (confirmed on live API)

| # | Symptom | Endpoint | Observed | Expected |
|---|---------|----------|----------|----------|
| S1 | «Дано прогнозов» is 0 for every user | `GET /contests/1/rounds/{r9}/leaderboard`, `GET /contests/1/leaderboard` | `predictions_count: 0` | 72 (64 for serov) after round 9, per `docs/test_data/contracted/leaderboard.csv` |
| S2 | Round leaderboard shows single-round points only | `GET /contests/1/rounds/{r9}/leaderboard` | leader `total_with_bonus3` 68 (round 9 only) | cumulative through round 9: leader `larin` 436 |
| S3 | No explicit total-bonus column in API; UI duplicated `total_with_bonus3` | leaderboard row | only `bonus1/2/3` + `total_without_bonus3` + `total_with_bonus3` | add `total_bonus_points` = sum(b1,b2,b3); matches CSV `total_bonuses` (larin: 128) |

**Already correct (do not break):**
- `points_base` = CSV `total_without_bonuses` (larin: 308)
- `total_with_bonus3` = CSV `total_points` (larin: 436)
- Global leaderboard rank/totals match `leaderboard.csv`

---

## 2. Root causes

### S1 — predictions_count

`leaderboard_service._score_to_user_round` sets `per_match=()`. `build_standings` counts
`sum(len(r.per_match))` → always 0. Count from `predictions` table instead.

### S2 — round leaderboard not cumulative

`get_round_leaderboard` filters `Score.round_id == round_id` only. Public leaderboard for
«Тур N» must be standings **as of** round N (sum rounds 1..N).

**Constraint:** same endpoint serves supervisor preview (`RoundLeaderboardPreview`, CALCULATED
round, per-round semantics). Default must stay `scope=round`.

### S3 — total_bonus_points missing

API exposes `bonus1`, `bonus2`, `bonus3` separately. Reference CSV has `total_bonuses`.
Frontend mistakenly rendered `total_with_bonus3` twice («Очки с бонусами» and «Всего очков»).
Add explicit `total_bonus_points` so clients don't re-derive or confuse with `total_without_bonus3`.

**Naming clarification (do not change existing field semantics):**

| API field | Meaning | CSV column |
|-----------|---------|------------|
| `points_base` | Sum of match base points (no bonuses) | `total_without_bonuses` |
| `total_without_bonus3` | base + bonus1 + bonus2 | *(no direct CSV column)* |
| `total_bonus_points` | bonus1 + bonus2 + bonus3 | `total_bonuses` |
| `total_with_bonus3` | Grand total | `total_points` |

---

## 3. Required changes

### 3.1 `GET /contests/{cid}/rounds/{rid}/leaderboard` — `scope` query param

- `scope=round` (default) — one round only (supervisor preview unchanged).
- `scope=total` — cumulative: aggregate `Score` for rounds with `number <= selected.number`
  and status in viewer-allowed set (`PUBLISHED` for public; staff may include selected
  `CALCULATED` round — keep `_allowed_round_statuses`).
- Reuse `build_standings` + column aggregation pattern from `get_global_leaderboard`.

### 3.2 predictions_count — from `predictions` table

Grouped query (no N+1):

```sql
SELECT p.user_id, COUNT(*) AS cnt
FROM predictions p
JOIN matches m ON m.id = p.match_id
JOIN rounds r ON r.id = p.round_id
WHERE r.contest_id = :cid AND r.id IN (:counted_round_ids)
GROUP BY p.user_id
```

Apply per scope:
- `scope=round` → selected round only;
- `scope=total` → cumulative round set;
- `get_global_leaderboard` → all PUBLISHED rounds.

### 3.3 Add `total_bonus_points` to leaderboard rows

In `get_round_leaderboard`, `get_global_leaderboard` (all scopes), and Pydantic
`LeaderboardEntryOut` / OpenAPI `ScoreDetail`:

```python
total_bonus_points = bonus1 + bonus2 + bonus3  # per aggregated row
```

Expose in JSON as `total_bonus_points` (integer, ≥ 0).

### 3.4 Contract & docs

- `agent_docs/contracts/api_v1.yaml`:
  - `scope` query param on `/rounds/{id}/leaderboard`;
  - `total_bonus_points` on leaderboard row schema;
  - clarify `points_base`, `predictions_count`, `total_with_bonus3`.
- `agent_docs/contracts/frontend_api_integration.md`: public LB uses `?scope=total`.

### 3.5 ETag

Include `scope` and contest-wide `max(Score.id)` in hash when `scope=total`.

---

## 4. Tests (`tests/api/`)

Fixture: contest id=1, manual finalize (rounds 1–9 PUBLISHED). Parse
`docs/test_data/contracted/leaderboard.csv` (`;`-sep).

1. `scope=total` round 9 == `leaderboard.csv`: ranks, `total_with_bonus3`,
   `total_bonus_points` (= `total_bonuses`), `points_base`, `predictions_count`,
   count columns, individual bonuses.
2. `scope=total` mid-round (e.g. 5): cumulative totals from `expected_scores.csv` rounds 1..5.
3. `scope=round` (default) round 9: single-round totals unchanged; `predictions_count == 8`.
4. Global leaderboard: `predictions_count` + `total_bonus_points` match CSV.
5. `total_bonus_points == bonus1 + bonus2 + bonus3` for every row.
6. Visibility: public + CALCULATED selected round → still `RESULTS_NOT_AVAILABLE`.

Lint: `uv run ruff check src/`, `uv run mypy src/`, `uv run bandit -r src/ -ll`.

---

## 5. Out of scope (tracked separately)

- **Demo `user` as participant** — product rule: demo login is for viewing only, must never
  be `ACCEPTED` in contest scoring or predictions matrix. Tracked in agent TODO; affects
  `bootstrap_users.py`, `finalize_dev_fixture` hybrid profile, E2E prediction tests.
- Frontend (`fix_2.4.1.md`).
- No new DB tables.

---

## 6. Handoff

- Append progress entry to `agent_docs/progress/stage_1.md`.
- After TEST_PASS → run `fix_2.4.1.md` on frontend.
