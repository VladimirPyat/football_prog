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

## 2026-06-11 — Coder (1.1)
- STATUS: READY_FOR_TEST
- Files: src/scoring/__init__.py, src/scoring/types.py, src/scoring/rules.py, src/scoring/engine.py, src/scoring/standings.py, tests/unit/test_scoring_engine.py
- Verified: uv run pytest tests/unit/test_scoring_engine.py -v -> 35 passed

## 2026-06-11 — Planner hotfix (1.1)
- Fixed round_rank: competition ranking (1,2,2,4) → dense ranking (1,2,2,3).
  Coder followed a contradictory example in the prompt; dense is what expected_scores.csv uses (verified 90/90).
  engine.py: rank = 1 + count of DISTINCT totals strictly higher.
  test updated accordingly. 35 passed after fix.

## 2026-06-11 — Tester (1.1)
- STATUS: TEST_PASS
- Tests: tests/scoring/__init__.py, tests/scoring/conftest.py, tests/scoring/test_contracted_scores.py
- Executed: uv run pytest tests/scoring/ -v → 18 passed, 0 failed (0.09s)
- Verified: [SC-BASE] 90/90, [SC-B1B2] 90/90, [SC-B3] 90/90, [SC-TOTAL] 90/90, [SC-RANK] 90/90, [SC-COUNTS] 90/90, [LB-COUNT] 10/10, [LB-TOTALS] 10/10, [LB-RANK] 10/10, edge cases: PASS
- Report: agent_docs/reports/test_1.1.md

## 2026-06-11 — Coder (1.2)
- STATUS: READY_FOR_TEST
- Files:
  - config/test_data_loader.json (loader format/mapping config — all in config, nothing hardcoded)
  - src/scripts/load_test_data.py (CSV→DB loader; --reset flag; idempotent)
  - src/services/__init__.py (empty module init)
  - src/services/round_service.py (DRAFT→ACTIVE→CLOSED→CALCULATED→PUBLISHED machine; 24h deadline rule)
  - src/services/match_service.py (set_result; change_status with VOID→recalculate trigger)
  - src/services/prediction_service.py (submit_batch batch-only; visible_predictions privacy filter)
  - src/services/scoring_persistence.py (calculate_round; recalculate_round; atomic upsert)
  - src/database/models.py (Score extended: count_exact_high, count_exact, count_diff, count_outcome added)
  - alembic/versions/a2b3c4d5e6f7_scores_counts.py (additive migration; server_default=0)
  - tests/unit/test_services_1_2.py (34 unit tests, ~80% edge cases)
- Verified:
  - uv run alembic upgrade head → exit 0 (migration applied: 0992bb744cc8 → a2b3c4d5e6f7)
  - uv run alembic downgrade -1 → exit 0 (drops 4 count columns cleanly)
  - uv run alembic upgrade head → exit 0 (re-applied)
  - uv run python src/scripts/load_test_data.py --reset → "✅ Data loaded successfully", exit 0
    (16 teams, 10 users, 80 matches, 712 predictions)
  - uv run pytest tests/unit/test_services_1_2.py -v → 34 passed, 0 failed
- Note for Planner: scores schema extended with count_* columns (additive, backward-compatible).
  Please sync contracts/db_schema.md.
- Next: agent_docs/instructions/tester_1.2.md

## 2026-06-11 — Tester (1.2)
- STATUS: TEST_PASS
- Tests: tests/integration/conftest.py, tests/integration/test_loader_1_2.py, tests/integration/test_deadline_batch_1_2.py, tests/integration/test_calculate_persistence_1_2.py
- Executed: uv run alembic upgrade head → exit 0; uv run pytest tests/integration/ -v → 36 passed, 0 failed (5.27s)
- Verified: [LD-COUNT/NULL/ABSENCE/MAP/IDEMPOTENT] PASS, [DL-24H-FAIL/OK] PASS, [ST-ILLEGAL/LOCK] PASS, [BT-PARTIAL/FULL/ZERO/DEADLINE] PASS, [CALC-ROUND] 90/90, [CALC-COUNTS] 10/10, [CALC-COUNTS-ROW] 90/90, [CALC-ATOMIC/VOID] PASS
- Report: agent_docs/reports/test_1.2.md

## 2026-06-09 — Planner (1.3 augment — Phase B)
- STATUS: INSTRUCTIONS_READY (1.3 updated; 1.2.1 migration spec added)
- Artifacts:
  - `instructions/coder_1.3.md` — lifecycle, immutability, exceptional tie-break, safe delete
  - `instructions/tester_1.3.md` — [API-CS-*], [API-TB-*], [API-CONTEST-*] tests
  - `instructions/coder_1.2.1.md` — migration only (status/paused_at/finished_at + exceptional_tiebreak_points)
  - `contracts/api_v1.yaml` — contest admin endpoints; removed legacy override endpoint
  - `contracts/db_schema.md`, `contracts/leaderboard_tiebreakers.md` — synced
  - `plans/draft_1.3_contest_lifecycle.md`
- Next: @Coder runs 1.2.1 then 1.3

## 2026-06-21 — Coder (1.2.1)
- STATUS: READY_FOR_TEST
- Files: src/database/models.py, alembic/versions/b3c4d5e6f7a8_contest_lifecycle_and_tiebreak.py, agent_docs/contracts/db_schema.md (already synced), tests/unit/test_migration_1_2_1.py
- Verified: alembic upgrade head → exit 0; alembic downgrade -1 → exit 0; re-upgrade → exit 0; pytest tests/unit/test_services_1_2.py tests/unit/test_migration_1_2_1.py → 35 passed

## 2026-06-21 — Coder (1.3)
- STATUS: READY_FOR_TEST
- Files: main.py, config/settings.py, src/core/security.py, src/api/__init__.py, src/api/deps.py, src/api/v1/{auth,rounds,predictions,admin_rounds,admin_results,admin_contest,admin_misc}.py, src/schemas/{auth,predictions,rounds,admin,leaderboard,contest}.py, src/services/{contest_lifecycle_service,contest_teardown,leaderboard_service}.py, tests/unit/test_api_unit_1_3.py, tests/unit/test_contest_lifecycle_1_3.py
- Verified: app import OK (main.app); pytest tests/unit/test_contest_lifecycle_1_3.py tests/unit/test_api_unit_1_3.py → 24 passed
- Deps added (approved): fastapi, uvicorn[standard], python-jose[cryptography], passlib[bcrypt], python-multipart

## 2026-06-21 — Planner (1.4)
- STATUS: INSTRUCTIONS_READY
- Artifacts: draft_1.4_contest_setup.md, coder_1.4.md, tester_1.4.md, contest_lifecycle_flow.md
- Updated: tester_1.3.md (narrow scope), api_v1.yaml, db_schema.md
- Note: full HTTP integration test → Stage 1.4
- Next: @Tester runs 1.3 (narrow), then @Coder 1.4
- Note: tester_1.4.md §8a — deliverable `manuals/MANUAL_SCORING_VERIFICATION.md` (RU, Stage 1 sign-off)

## 2026-06-21 — Tester (1.3)
- STATUS: TEST_PASS
- Tests: tests/api/conftest.py, tests/api/test_auth_rbac_1_3.py, tests/api/test_predictions_flow_1_3.py, tests/api/test_contest_lifecycle_1_3.py, tests/api/test_calculate_smoke_1_3.py
- Executed: uv run pytest tests/api/ -v → 31 passed, 1 skipped, 0 failed (~109s); regression tests/integration/ → 36 passed
- Verified: [AUTH-*] [RBAC-*] [API-PRED-*] [API-SMOKE-*] [API-VOID] [API-CACHE-*] [API-CS-*] [API-TB-*] (except [API-TB-RANK] SKIP) [API-CONTEST-*] PASS
- Report: agent_docs/reports/test_1.3.md
- Notes: SQLite naive datetime workaround in conftest for grace period; [API-CONTEST-DELETE-BADCONFIRM] returns 422 (Pydantic Literal)
- Next: @Coder implements 1.4 per coder_1.4.md

## 2026-06-21 — Coder (1.4)
- STATUS: READY_FOR_TEST
- Files: src/database/models.py, alembic/versions/c4d5e6f7a8b9_multi_contest_and_participants.py, src/services/{contest_setup_service,round_auto_close_service,contest_lifecycle_service,contest_teardown,round_service,match_service,prediction_service,scoring_persistence,leaderboard_service}.py, src/api/{deps,v1/contests,contest_teams,contest_participants,contest_ops}.py, refactored legacy v1 routers, src/schemas/{contest,rounds,leaderboard}.py, src/scripts/{load_test_data,seed}.py, main.py, tests/unit/test_{contest_setup,multi_contest,round_auto_close}_1_4.py, extended test_contest_lifecycle_1_3.py, integration/unit test updates for Contest model
- Verified: alembic upgrade head → exit 0; pytest tests/unit/test_*_1_4.py tests/unit/test_contest_lifecycle_1_3.py tests/unit/test_api_unit_1_3.py → 31 passed; pytest tests/unit/test_services_1_2.py → 34 passed; pytest tests/integration/ → 36 passed; pytest tests/api/ → 31 passed, 1 skipped
- Migration: c4d5e6f7a8b9_multi_contest_and_participants
- Next: agent_docs/instructions/tester_1.4.md

## 2026-06-21 — Planner/audit (1.4.1 patch)
- Gap audit: tester_1.4 vs docs/03_user_scenarios.md, docs/04_supervisor_scenario.md, api_v1.yaml
- Created: agent_docs/instructions/tester_1.4.1.md — safe delete contest-scoped, operational gaps (privacy/24h/round-edit/recalc), CANARY pytest + manual cross-ref
- API routes complete for Stage 1; gaps were test coverage only (newsletters/contacts out of scope)

## 2026-06-21 — Tester (1.4 + 1.4.1)
- STATUS: TEST_FAIL
- Tests: tests/api/conftest.py, reference_compare.py, test_setup_phase_1_4.py, test_operational_phase_1_4.py, test_multi_contest_1_4.py, test_calculate_leaderboard_1_4.py, test_free_tour_1_4.py, test_contest_lifecycle_1_4.py, test_operational_gaps_1_4.py, test_canary_scoring_1_4.py, tests/manual/{verify_via_api.py,compare_db_vs_reference.py,README.md}, manuals/MANUAL_SCORING_VERIFICATION.md
- Executed: uv run pytest tests/api/ -v → 81 passed, 1 failed, 2 skipped; uv run pytest tests/integration/ -v → 36 passed
- Verified: [API-RESULTS] 90/90, [API-LB-GLOBAL] 10/10, [CANARY-PYTEST-*] PASS, contest-scoped lifecycle/gaps/multi PASS; [OP-CLOSE] FAIL — auto_close + close handler conflict, no commit (see test_1.4.md)
- Report: agent_docs/reports/test_1.4.md
- Next: @Coder fix [OP-CLOSE] in src/api/deps.py + round close idempotency; re-test
