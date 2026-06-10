# Leaderboard & Tie-breaking Rules (VERIFIED) — Stage 1

> Status: VERIFIED against `docs/test_data/contracted/leaderboard.csv` — the
> engine reproduces the full ranking AND every total **10/10 users** (rounds 1–9),
> including tie-break pairs. Kept as a SEPARATE file so the ordering logic (esp.
> the manual 5th criterion) is easy to review and change.
> Source of truth: `docs/01_tech_regulations.md` §4.3, confirmed by user 2026-06-10.

## 1. Leaderboard count columns = FREQUENCY of hits (not points)
In `leaderboard.csv` and in the global/aggregate leaderboard the columns
`exact_high_count`, `exact_count`, `diff_count`, `outcome_count` are **counts of
matches** (frequency of hits) in each EXCLUSIVE base category, aggregated over all
rounds. They are NOT point sums. The engine computes one exclusive category per
match (see `dataflow/scoring_flow.md` §1) and sums the counts per user.

Verification: engine per-round exclusive counts, summed per user, equal the
`leaderboard.csv` count columns for all 10 users.

> CAVEAT: the per-round `count_*` columns inside `expected_scores.csv` were
> INCONSISTENT (52/90). The user corrects the 38 rows per
> `agent_docs/reports/count_fix_reference.md` (authoritative engine values). After
> correction, @Tester verifies per-round counts row-by-row (gated on
> `16·eh+12·ex+8·di+4·ou == expected_base_pts`). The aggregated `leaderboard.csv`
> counts are already correct (10/10) and remain the source for tie-break inputs.

## 2. Final placement order (apply in sequence)
Rank users by the following keys; each next key is used only to break ties on all
previous keys.

1. `total_points` DESC  — points including all bonuses (1, 2, 3).
2. `exact_scores_count` DESC  — total exact scores guessed,
   = `exact_high_count + exact_count` (large + normal exacts).
3. `total_without_bonuses` DESC  — base points only (no bonus 1/2/3).
4. `correct_diffs_count` DESC  — `diff_count` (diff_plus_outcome hits).
5. `manual_tiebreak` DESC  — admin-set manual priority (see §3). Used only if 1–4
   are all equal. Set `tiebreaker_status = "manual_override"` for the affected users.

Bonuses affect only key 1 (`total_points`); they are excluded from keys 2–4 to keep
prize placement deterministic.

### Verified tie-break examples (rounds 1–9 aggregate)
- **shutov vs kurakov**: both `total_points = 320`. shutov `exact = 1+6 = 7`,
  kurakov `exact = 1+4 = 5` → shutov ranks higher (4th vs 5th). ✓
- **volchenko vs serov**: both `total_points = 232`. volchenko `exact = 5`,
  serov `exact = 4` → volchenko higher (9th vs 10th). ✓

## 3. Manual 5th criterion (config-driven, very rare)
When keys 1–4 are identical for 2+ users, an Admin assigns an explicit ordering
value. Store it in config so it is visible and editable, e.g. in
`contest_settings.rules_json.tiebreakers`:

```json
"manual_overrides": { "<user_id>": <int priority, higher = better>, ... }
```
- Default: empty → no manual override.
- Engine reads `manual_overrides`; missing user → priority 0.
- Exposed via `POST /api/v1/admin/leaderboard/{round_id}/override` (per api_v1.yaml)
  which persists the values into config.
- Probability is negligible, but the endpoint and config key are mandatory.

## 4. Scope: per-round vs global
- The same ordering applies to a single round's leaderboard and to the global
  aggregate leaderboard.
- Per-round: counts/points are the round's values. Global: aggregated over all
  CALCULATED/PUBLISHED rounds.
