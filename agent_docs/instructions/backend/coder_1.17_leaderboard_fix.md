# Coder Instructions — Stage 1.17 Fix: Round Results Per-Match Points (Backend)

> **Status gate:** `INSTRUCTIONS_READY`
> **Prerequisite:** Stage 1.4+ scoring persistence (`calculate_round`, `Score` aggregates), public `GET …/results` handler in `contest_ops.py`
> **Blocks:** `agent_docs/instructions/coder_2.4.md` — frontend **Results** matrix cannot wire to API until this ships
> **Follow-up tester:** optional `agent_docs/instructions/tester_1.17_leaderboard_fix.md` (or extend `test_calculate_leaderboard_1_4.py`)
> **Related:** `agent_docs/contracts/api_v1.yaml`, `manuals/API_GUIDE.md`, `agent_docs/contracts/frontend_api_integration.md`, `src/services/leaderboard_service.py`
> **Language policy:** API `detail` Russian; code comments English

---

## 1. Objective

Fix **`GET /api/v1/contests/{contest_id}/rounds/{round_id}/results`** so each participant row includes **per-match base points** for the public results matrix (`user_result.jpg`). Today `results[].points` is always `[]` — the UI mock in Stage 2.4 cannot be replaced with live data.

| ID | Problem | Target |
|----|---------|--------|
| **R1** | `get_round_results` returns `"points": []` for every user | Ordered per-match `base_points` aligned with `matches[]` |
| **R2** | Missing `total_without_bonus3` on result rows | Expose field for «Итого без бон.» column |
| **R3** | OpenAPI `RoundResults` schema underspecified | Typed `ResultRow` + `MatchPoints` in `api_v1.yaml` |
| **R4** | No regression test for matrix payload | Pytest spot-check vs scoring engine on loaded fixture |

**Non-goals:**

- New DB table / migration for per-match persistence (compute on read via existing engine)
- Changing leaderboard aggregation (`GET …/leaderboard`) — already correct with B4 `count_*`
- Frontend changes (→ **2.4**)
- Bonus 1 per-match breakdown in matrix cells (UI shows round-level bonus columns only)

---

## 2. Background (verified)

| Layer | Today |
|-------|--------|
| `score_round()` | Produces `UserRoundScore.per_match: tuple[MatchScore, …]` with `base_points` per match |
| `_persist_scores()` | Writes **aggregates only** to `scores` — no per-match columns |
| `get_round_results()` | Reads `Score` rows + `Match` list; sets `"points": []` |
| Frontend `ResultsMatrix` | Expects `match_points: (number \| null)[]` in **matches column order** |

**Locked rule:** Matrix cells show **base match points** (`0`, `4`, `8`, `12`, `16` per contest rules) — use `MatchScore.base_points`, **not** `bonus1_points` and not round totals.

**Visibility** (unchanged): public / USER → round must be `PUBLISHED`; SUPERVISOR+ may read `CALCULATED` (see `_assert_round_visible` in `leaderboard_service.py`).

---

## 3. Response contract (LOCKED)

### 3.1 Top-level `RoundResultsOut`

```json
{
  "round_id": 42,
  "matches": [ { "id": 1, "team1": "…", "team2": "…", "score1": 1, "score2": 0, "date_time": "…", "status": "FINISHED" } ],
  "results": [ { "user_id": 3, "user_name": "Иванов И.И.", "points": […], "bonus1": 0, "bonus2": 8, "bonus3": null, "total_without_bonus3": 32, "total": 40, "correct_outcomes": 5 } ]
}
```

### 3.2 `results[].points` — one entry per `matches[]` item, **same order**

| Case | Value |
|------|--------|
| User predicted match; scorable | `{ "match_id": <id>, "base_points": <int ≥ 0> }` |
| User did not predict (no row / NULL scores) | `{ "match_id": <id>, "base_points": null }` |
| Match not scorable (`VOID`, `CANCELED`, unfinished) | `{ "match_id": <id>, "base_points": null }` |

**Do not** omit entries — length of `points` **must equal** `len(matches)`.

### 3.3 Row totals

| Field | Source |
|-------|--------|
| `bonus1`, `bonus2`, `bonus3` | Existing `Score` row (unchanged) |
| `total_without_bonus3` | `Score.total_without_bonus3` (**add** — was missing) |
| `total` | `Score.total_with_bonus3` (keep name `total` for backward compat) |
| `correct_outcomes` | `Score.correct_outcomes` (unchanged) |

---

## 4. Implementation

### 4.1 Pydantic schemas — `src/schemas/leaderboard.py`

Add:

```python
class MatchPointsOut(BaseModel):
    match_id: int
    base_points: int | None

class RoundResultRowOut(BaseModel):
    user_id: int
    user_name: str
    points: list[MatchPointsOut]
    bonus1: int
    bonus2: int
    bonus3: int | None = None  # optional: use 0 vs null per existing API habit; prefer int 0 if DB has 0
    total_without_bonus3: int
    total: int
    correct_outcomes: int

class RoundResultsOut(BaseModel):
    round_id: int
    matches: list[dict]  # keep MatchOut-compatible dicts or typed model if already exists
    results: list[RoundResultRowOut]
```

Replace `results: list[dict]` loose typing.

### 4.2 Scoring helper — DRY with persistence

Extract (or add) in `src/services/scoring_persistence.py`:

```python
async def compute_round_user_scores(
    session: AsyncSession, round_id: int, contest_id: int
) -> dict[int, UserRoundScore]:
    """Load round inputs and run score_round without persisting."""
```

Implementation: reuse `_collect_round_data` + `score_round` + contest `rules_json` — same path as `calculate_round`, **no** DB writes.

`get_round_results` calls this **after** `_assert_round_visible` and loading `matches` / `Score` rows.

### 4.3 Build `points` array — `leaderboard_service.get_round_results`

```python
match_ids = [m["id"] for m in match_out]  # preserve match_out order
engine_scores = await compute_round_user_scores(session, round_id, contest_id)

for score in scores:
    uid = score.user_id
    user_round = engine_scores.get(uid)
    per_match = {ms.match_id: ms.base_points for ms in (user_round.per_match if user_round else ())}
    points = [
        {"match_id": mid, "base_points": per_match.get(mid)}
        for mid in match_ids
    ]
    results.append({..., "points": points, "total_without_bonus3": score.total_without_bonus3, ...})
```

**Performance:** ~10 users × 8 matches — on-read recompute is acceptable for MVP. Log DEBUG timing once if >100ms.

**Consistency:** Aggregates in response (`total`, bonuses) come from persisted `Score` (post-calculate). Per-match values come from engine recompute — must match aggregates; if mismatch, log WARNING (do not fail request).

### 4.4 ETag

No change — `compute_etag` already keys on `max_score_id` + round status. Recompute does not alter ETag inputs.

### 4.5 Legacy shim

If `admin_misc.py` deprecated `GET …/results` delegates to `get_round_results_response`, it picks up the fix automatically — verify with one pytest.

---

## 5. Scope — files you may create/modify

```
src/schemas/leaderboard.py              # MatchPointsOut, RoundResultRowOut
src/services/scoring_persistence.py     # compute_round_user_scores (extract)
src/services/leaderboard_service.py     # get_round_results — populate points
agent_docs/contracts/api_v1.yaml        # RoundResults schema detail
manuals/API_GUIDE.md                    # Document results[].points shape
agent_docs/contracts/frontend_api_integration.md  # §7 types + update log row
agent_docs/progress/stage_1.md          # APPEND handoff (append-only)
```

**Do NOT modify:** `docs/`, frontend, scoring engine rules.

If aggregate vs per-match mismatch is systematic, append note to `agent_docs/reports/BLOCKED.md` — do not silently return empty `points`.

---

## 6. Tests (pytest)

Add `tests/api/test_round_results_points_1_17.py`:

| ID | Case |
|----|------|
| `[API-RESULTS-POINTS-LEN]` | PUBLISHED round 9 → 200; `len(results[0].points) == len(matches)` |
| `[API-RESULTS-POINTS-NONEMPTY]` | At least one user has some `base_points > 0` on loaded fixture |
| `[API-RESULTS-POINTS-ORDER]` | `points[i].match_id == matches[i].id` for all `i` |
| `[API-RESULTS-TOTAL-WO-B3]` | Row includes `total_without_bonus3` matching `scores` table |
| `[API-RESULTS-NOT-PUBLISHED]` | ACTIVE round → 403 `RESULTS_NOT_AVAILABLE` (unchanged) |
| `[API-RESULTS-CALC-STAFF]` | SUPERVISOR on CALCULATED round 10 → 200 with points (if fixture has scores) |

Optional cross-check: for one `(user_id, round_id)` from `expected_scores.csv`, sum of non-null `base_points` ≤ `points_base` aggregate (engine invariant).

Run before handoff:

```bash
uv run pytest tests/api/test_round_results_points_1_17.py -q
uv run ruff check src/services/leaderboard_service.py src/services/scoring_persistence.py src/schemas/leaderboard.py
uv run mypy src/services/leaderboard_service.py src/services/scoring_persistence.py src/schemas/leaderboard.py
```

---

## 7. Acceptance criteria

- [ ] `GET …/rounds/{rid}/results` returns populated `points[]` (not empty) for calculated/published rounds with scores
- [ ] Each `points` entry has `match_id` + `base_points` (int or null)
- [ ] `points` length matches `matches` length and order
- [ ] `total_without_bonus3` present on every result row
- [ ] `api_v1.yaml` documents `MatchPoints` + `RoundResultRow`
- [ ] `manuals/API_GUIDE.md` updated
- [ ] Pytest §6 green; ruff + mypy on touched files
- [ ] Handoff appended to `stage_1.md`

---

## 8. Implementation order

1. `compute_round_user_scores` in `scoring_persistence.py`
2. Pydantic models in `schemas/leaderboard.py`
3. `get_round_results` — build `points` arrays
4. `api_v1.yaml` + `API_GUIDE.md` + `frontend_api_integration.md`
5. Pytest `test_round_results_points_1_17.py`
6. Append handoff → `stage_1.md`

---

## 9. Handoff

Append to `agent_docs/progress/stage_1.md`:

```
## YYYY-MM-DD — Coder (1.17 results per-match points)
- STATUS: READY_FOR_TEST
- Scope: GET …/results populates results[].points (base_points per match), total_without_bonus3
- Key paths: leaderboard_service.py, scoring_persistence.py, schemas/leaderboard.py
- Verified: pytest test_round_results_points_1_17.py; ruff/mypy
- Contracts: api_v1.yaml RoundResults, API_GUIDE.md, frontend_api_integration.md
- Next: agent_docs/instructions/coder_2.4.md
```

---

## 10. Explicitly OUT OF SCOPE

- Persisting per-match scores to DB
- Changing leaderboard endpoints or B4 count columns
- Frontend `ResultsMatrix` wiring
- Storing bonus1 per cell in the matrix
