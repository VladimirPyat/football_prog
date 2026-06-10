# Stage 1 Progress — Backend Core

- [2026-06-10] STATUS: INSTRUCTIONS_READY (Planner Phase B complete).
  Blockers 1 (bonuses) and 2 (detail counts) RESOLVED — see `agent_docs/reports/BLOCKED.md`.
  Scoring fully verified on contracted data: base 90/90, total 90/90, bonus3 90/90,
  expected_rank 90/90, leaderboard 10/10.

## Sub-stage split (sequential): 1.1 → 1.2 → 1.3
- 1.1 Scoring Engine (pure math): `instructions/coder_1.1.md`, `instructions/tester_1.1.md`
- 1.2 Setup, Deadlines & Data Loader: `instructions/coder_1.2.md`, `instructions/tester_1.2.md`
- 1.3 API Integration & Triggers: `instructions/coder_1.3.md`, `instructions/tester_1.3.md`

## Contracts backing Stage 1
- `contracts/api_v1.yaml`, `contracts/bonus_rules.md`, `contracts/leaderboard_tiebreakers.md`,
  `dataflow/scoring_flow.md`, `contracts/db_schema.md`

## Notes for execution
- 1.2 extends the `scores` table with `count_exact_high/exact/diff/outcome` (+ migration);
  Planner to sync `contracts/db_schema.md` after implementation.
- Test-data loader mapping/format lives in `config/test_data_loader.json`; verification by id.
- New API deps (`fastapi`, `uvicorn`, `python-jose`, `passlib[bcrypt]`, `python-multipart`)
  require user approval before `uv add` (see `plans/draft_1.md` §9).
- Per-round `count_*` columns in `expected_scores.csv`: user corrects 38 rows per
  `reports/count_fix_reference.md`; after that @Tester enables per-row count checks
  (`[SC-COUNTS]`, `[CALC-COUNTS-ROW]`), gated on `16eh+12ex+8di+4ou == expected_base_pts`.
  Aggregate counts vs `leaderboard.csv` remain verified (10/10).

## 2026-06-11 — Planner (re-verify + manual-verification flow)
- `expected_scores.csv` re-verified after user fix: 90/90 on ALL columns incl. `count_*`
  and the gate `16eh+12ex+8di+4ou==base`. `count_*` blocker CLOSED (see `reports/BLOCKED.md`).
- Score checks confirmed NOT disabled: `[SC-*]` active in `tester_1.1.md`, `[CALC-*]` active
  in `tester_1.2.md`; gate kept only as a regression canary.
- Two-phase manual verification placed in **1.3** (user choice, option B): added
  `tester_1.3.md` §6 — SCRIPT 1 `verify_via_api.py` (endpoints only, no reference knowledge)
  → manual DBeaver STOP → SCRIPT 2 `compare_db_vs_reference.py` (read-only DB↔CSV diff) +
  canary (edit reference ⇒ Script 2 must fail). `coder_1.3.md` notes endpoints must be
  HTTP-drivable with no test backdoors.
- Recommended execution order: per sub-stage code→test, sequential 1.1 → 1.2 → 1.3.
