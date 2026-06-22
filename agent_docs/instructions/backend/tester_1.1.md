# Tester Instructions — Stage 1.1: Scoring Engine cross-check

> Status gate: start only when `agent_docs/progress/stage_1.md` shows @Coder
> `READY_FOR_TEST` for 1.1. Language: tests/reports in English; user verdict in Russian.
> Reference data (read-only): `docs/test_data/contracted/` —
> `predictions.csv`, `matches.csv`, `users.csv`, `teams.csv`, `expected_scores.csv`,
> `leaderboard.csv`; config `docs/test_data/config/contest_defaults.json`.
> Source of truth for rules: `agent_docs/contracts/bonus_rules.md`,
> `agent_docs/contracts/leaderboard_tiebreakers.md`.

## 1. Objective
Prove the pure scoring engine (`src/scoring/`) reproduces the contracted reference
**row by row**, with **0 points of discrepancy**. This stage needs NO database and
NO API — feed the CSVs straight into the engine.

## 2. Scope — files you may create
```
tests/scoring/test_contracted_scores.py
tests/scoring/conftest.py            # CSV loaders/helpers (no DB)
```
Do NOT modify `src/`. If the engine output disagrees with the reference, report it;
@Coder fixes the engine.

## 3. Data loading rules (match the fixtures exactly)
- `predictions.csv`, `matches.csv`, `users.csv`, `expected_scores.csv`,
  `leaderboard.csv` use delimiter `;`. **`teams.csv` uses `,`** (comma) — handle it.
- Join keys: predictions/matches reference teams by `home_team_short`/`away_team_short`;
  build a `short_name -> team_id` map and a `login -> user_id` map. **Verify by id**,
  use names only for human-readable assert messages.
- `matches.csv`: `actual_score1/2` empty + `status=SCHEDULED` (round 10) ⇒ not
  scorable. Only rounds 1–9 (`FINISHED`) are scored here.
- **Absence = no row.** Confirm `serov` has NO predictions in round 4 and is still
  scored as 0 with `expected_rank` present. NEVER synthesize 0:0 for missing rows.

## 4. MANDATORY assertions (per-round, expected_scores.csv — 90 rows)
For every `(user_login, round_number)` row compare engine output to the file
(map login→user_id first). Verify with **exact equality**:
- `[SC-BASE]` `engine.base_points == expected_base_pts`  (expect 90/90)
- `[SC-B1B2]` `engine.bonus1 + engine.bonus2 == expected_bonus1`  AND
  `expected_bonus2 == 0`  (fixture folds bonus2 into the bonus1 column — see
  bonus_rules.md "FIXTURE QUIRK"). (expect 90/90)
- `[SC-B3]` `engine.bonus3 == expected_bonus3`  (90/90)
- `[SC-TOTAL]` `engine.total_with_bonus3 == expected_total`  (90/90)
- `[SC-RANK]` `engine.round_rank == expected_rank`  (dense rank by total; 90/90)
- `[SC-COUNTS]` `(engine.count_exact_high, count_exact, count_diff, count_outcome)` ==
  the per-round `count_*` columns of `expected_scores.csv`, by exact equality, for all 90 rows.
  Counts are EXCLUSIVE (one category per match; `count_exact` excludes high).

> NOTE: the `expected_scores.csv` `count_*` columns were CORRECTED and re-verified on
> 2026-06-11 (now 90/90 — see `agent_docs/reports/BLOCKED.md`). `[SC-COUNTS]` is ACTIVE.
> Keep the safety-gate: first assert EVERY row satisfies
> `16·count_exact_high + 12·count_exact + 8·count_diff + 4·count_outcome == expected_base_pts`.
> If the gate ever fails (fixture regressed), report `[SC-COUNTS] BLOCKED: data inconsistent`
> (point to count_fix_reference.md) and do NOT silently skip or weaken the assertion.

## 5. MANDATORY cross-check (anti-lucky-sum, leaderboard.csv — 10 users)
Aggregate engine results across rounds 1–9 per user, then assert exact equality to
`leaderboard.csv`:
- `[LB-COUNT]` `Σ count_exact_high == exact_high_count`, `Σ count_exact == exact_count`,
  `Σ count_diff == diff_count`, `Σ count_outcome == outcome_count`  (10/10).
- `[LB-TOTALS]` `Σ base == total_without_bonuses`, `Σ(bonus1+bonus2+bonus3) == total_bonuses`,
  `Σ total_with_bonus3 == total_points`, `total_predictions` matches (serov=64, others=72).
- `[LB-RANK]` engine `build_standings(...)` order and 1-based ranks == `leaderboard.csv`
  `rank` column, including the tie-break pairs: shutov(320) above kurakov(320) by
  exact_scores_count 7>5; volchenko(232) above serov(232) by 5>4.

## 6. Boundary / edge tests (engine-level, no CSV)
- `[EDGE-NULL]` Missing prediction excluded; assert a contrived 0:0 result does NOT
  award points to a user who has no row for that match.
- `[EDGE-ZERO]` `0:0` prediction vs `0:0` result → EXACT (not high), real points.
- `[EDGE-TIE]` Synthetic round where 3 users tie on total → identical dense rank;
  and where two tie on total but differ on exact_scores_count → standings order.
- `[EDGE-VOID]` A match flagged non-scorable contributes 0 to everyone and is
  excluded from `correct_outcomes`.

## 7. Execution & report
```
uv run pytest tests/scoring/ -v
```
Capture exit code and any assertion diffs. Then:
- **PASS** → write `agent_docs/reports/test_1.1.md` (Russian) confirming 90/90 +
  10/10 + edge cases; append `STATUS: TEST_PASS` to `agent_docs/progress/stage_1.md`.
- **FAIL** → for each failing `[TEST-ID]`: expected vs actual (with user/round and
  numbers), and the required fix for @Coder. Append `STATUS: TEST_FAIL`. Do NOT edit `src/`.

## 8. Verdict to user (Russian)
Этап 1.1, вердикт PASS/FAIL, число строк сверки (ожидаемо 90/90 и 10/10), найденные
дефекты с `[TEST-ID]`, следующий шаг.
