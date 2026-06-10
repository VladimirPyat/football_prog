# Reference: authoritative per-round `count_*` values (for fixing expected_scores.csv)

> Purpose: the user will correct the per-round `count_*` columns in
> `docs/test_data/contracted/expected_scores.csv` (read-only for agents) so they
> become consistent. The values below are the AUTHORITATIVE counts produced by the
> verified scoring engine — they satisfy `16·eh + 12·ex + 8·di + 4·ou ==
> expected_base_pts` for every row AND aggregate per user to `leaderboard.csv`
> (10/10). Use them as the correction checklist.

## Definitions (EXCLUSIVE — one category per match)
- `count_exact_high` — matches won with EXACT_HIGH (16 pts): `pred==res` AND (`|diff|>=3` OR `sum>3`).
- `count_exact`      — matches won with EXACT (12 pts), NORMAL only (NOT including high).
- `count_diff`       — matches won with DIFF+OUTCOME (8 pts).
- `count_outcome`    — matches won with OUTCOME only (4 pts).
These match `leaderboard.csv` columns `exact_high_count / exact_count / diff_count /
outcome_count` when summed across rounds.

## Rows to correct (38 of 90) — FILE → CORRECT (eh, ex, di, ou)
| round | user | FILE (eh,ex,di,ou) | CORRECT (eh,ex,di,ou) | base |
|------:|------|--------------------|------------------------|-----:|
| 1 | kuznetsov | (0,1,0,5) | (0,1,0,4) | 28 |
| 1 | russkov | (1,1,0,3) | (1,1,0,2) | 36 |
| 1 | starchenkov_c | (1,2,1,2) | (0,2,1,2) | 40 |
| 1 | shutov | (0,0,3,3) | (0,0,2,3) | 28 |
| 2 | volchenko | (0,0,2,3) | (0,0,2,2) | 24 |
| 2 | kuznetsov | (0,1,2,2) | (0,1,1,2) | 28 |
| 2 | kurakov | (1,0,2,3) | (0,0,2,3) | 28 |
| 2 | larin | (0,1,2,2) | (0,1,1,2) | 28 |
| 2 | shutov | (0,1,1,2) | (0,1,1,1) | 24 |
| 3 | kuznetsov | (0,3,1,3) | (0,2,1,3) | 44 |
| 3 | russkov | (0,3,0,2) | (0,3,0,1) | 40 |
| 3 | starchenkov_c | (1,3,1,2) | (0,3,1,2) | 52 |
| 4 | larin | (1,4,0,0) | (0,4,0,0) | 48 |
| 4 | starchenkov_c | (0,2,1,2) | (0,2,1,1) | 36 |
| 4 | shutov | (0,3,0,2) | (0,2,0,2) | 32 |
| 5 | larin | (2,1,1,2) | (1,1,1,2) | 44 |
| 5 | nikitin | (0,1,1,4) | (0,1,0,4) | 28 |
| 5 | serov | (1,0,0,3) | (1,0,0,2) | 24 |
| 5 | starchenkov_c | (0,2,1,1) | (0,2,0,1) | 28 |
| 6 | kurakov | (2,1,0,4) | (1,1,0,4) | 44 |
| 6 | nikitin | (0,0,2,5) | (0,0,2,4) | 32 |
| 6 | serov | (0,1,2,4) | (0,1,1,4) | 36 |
| 7 | kuznetsov | (0,1,1,1) | (0,1,1,0) | 20 |
| 7 | kurakov | (0,0,3,3) | (0,0,2,3) | 28 |
| 7 | larin | (0,3,0,2) | (0,2,0,2) | 32 |
| 7 | nikitin | (0,1,2,2) | (0,1,1,2) | 28 |
| 7 | serov | (0,1,1,2) | (0,0,1,2) | 16 |
| 7 | starchenkov_r | (0,1,0,3) | (0,1,0,2) | 20 |
| 7 | starchenkov_c | (0,2,1,3) | (0,1,1,3) | 32 |
| 7 | shutov | (0,0,2,2) | (0,0,2,1) | 20 |
| 8 | kurakov | (0,1,2,3) | (0,1,2,2) | 36 |
| 8 | larin | (0,2,3,1) | (0,2,2,1) | 44 |
| 8 | russkov | (2,3,0,1) | (1,3,0,1) | 56 |
| 8 | starchenkov_c | (0,2,1,2) | (0,2,1,1) | 36 |
| 8 | shutov | (1,2,1,0) | (0,2,1,0) | 32 |
| 9 | larin | (0,1,1,5) | (0,1,1,4) | 36 |
| 9 | russkov | (0,1,3,3) | (0,1,2,3) | 40 |
| 9 | starchenkov_r | (1,1,3,2) | (0,1,3,2) | 44 |

The other 52 rows already match the engine. After correction, every row must satisfy
`16·count_exact_high + 12·count_exact + 8·count_diff + 4·count_outcome == expected_base_pts`,
and per-user sums must equal `leaderboard.csv`. Once corrected, the per-row `count_*`
assertion is ENABLED in `tester_1.1.md` / `tester_1.2.md`.
