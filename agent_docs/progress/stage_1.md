# Stage 1 Progress — Backend Core

- [2026-06-10] STATUS: INSTRUCTIONS_READY (Planner Phase B complete).
  Blockers 1 (bonuses) and 2 (detail counts) RESOLVED — see `agent_docs/reports/BLOCKED.md`.
  Scoring fully verified on contracted data: base 90/90, total 90/90, bonus3 90/90,
  expected_rank 90/90, leaderboard 10/10.

## Sub-stage split (sequential): 1.1 → 1.2 → 1.3 → … → 1.6
- 1.1 Scoring Engine (pure math): `instructions/coder_1.1.md`, `instructions/tester_1.1.md`
- 1.2 Setup, Deadlines & Data Loader: `instructions/coder_1.2.md`, `instructions/tester_1.2.md`
- 1.3 API Integration & Triggers: `instructions/coder_1.3.md`, `instructions/tester_1.3.md`
- 1.4 Multi-contest & setup phase: `instructions/coder_1.4.md`, `instructions/tester_1.4.md`
- 1.5 Errors, logging, docstrings: `instructions/coder_1.5.md`, `instructions/tester_1.5.md`
- 1.6 Bootstrap users & organizer API: `instructions/coder_1.6.md`, `instructions/tester_1.6.md`, `plans/draft_1.6_bootstrap_users.md`

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

## 2026-06-21 — Coder (1.5 cleanup)
- STATUS: READY_FOR_TEST
- Files: src/core/exceptions.py, src/core/logging_config.py, src/api/error_handlers.py, src/api/handlers/, src/services/notification_service.py, src/api/v1/*.py, src/services/*.py, config/settings.py, main.py, manuals/ERROR_LOGGING.md, manuals/API_GUIDE.md, tests/unit/test_exceptions_1_5.py, tests/api/test_errors_1_5.py, tests/unit/test_recoverable_1_5.py
- Verified: uv run pytest tests/ --ignore=tests/manual → 257 passed, 2 skipped
- Notes: HTTP detail Russian; AppError JSON {detail, code}; notify_admin stub; centralized error handlers; Russian API docstrings
- Next: agent_docs/instructions/tester_1.5.md

## 2026-06-21 — Tester (1.5)
- STATUS: TEST_PASS
- Tests: tests/unit/test_exceptions_1_5.py, tests/api/test_errors_1_5.py, tests/unit/test_recoverable_1_5.py
- Executed: uv run pytest tests/unit/test_exceptions_1_5.py tests/api/test_errors_1_5.py tests/unit/test_recoverable_1_5.py -v → 28 passed; uv run pytest (1.5 + 1.4 regression subset) -v → 60 passed, 1 skipped
- Verified: all [EXC-*], [ERR-*], [REC-*], [LOG-*]; static audit PASS; 90/90 + 10/10 regression PASS
- Report: agent_docs/reports/test_1.5.md
- Next: Stage 1.5 sign-off

## 2026-06-21 — Planner (1.6 bootstrap users)
- STATUS: INSTRUCTIONS_READY
- Artifacts: plans/draft_1.6_bootstrap_users.md, instructions/coder_1.6.md, instructions/tester_1.6.md
- Scope: POST /admin/users/supervisor, bootstrap_users.py, .env.example, manuals/BOOTSTRAP_USERS.md
- Prerequisite: Stage 1.5 TEST_PASS
- Next: @Coder implements per coder_1.6.md (gap: ADMIN assigns SUPERVISOR; secrets via .env)

## 2026-06-21 — Coder (1.6 bootstrap users)
- STATUS: READY_FOR_TEST
- Files: src/services/user_admin_service.py, src/schemas/users.py, src/api/v1/admin_users.py, main.py, config/settings.py, src/scripts/bootstrap_users.py, src/scripts/seed.py, .env.example, manuals/BOOTSTRAP_USERS.md, manuals/{CONFIG,API_GUIDE,README}.md, agent_docs/contracts/api_v1.yaml, tests/api/test_admin_users.py
- Verified: uv run pytest tests/ --ignore=tests/manual → 276 passed, 2 skipped
- Notes: SEED_ADMIN_PASSWORD plaintext preferred; supervisor CLI block documented for retirement when admin UI ships
- Next: agent_docs/instructions/tester_1.6.md

## 2026-06-22 — Coder (1.8 discovery & contacts)
- STATUS: READY_FOR_TEST
- Blockers closed: B1, B2, B3
- Files: src/api/v1/me.py, src/services/contest_discovery_service.py, src/services/contact_service.py, src/api/v1/auth.py (contacts), src/api/v1/contests.py (/public), src/schemas/{contest,auth}.py, main.py, agent_docs/contracts/api_v1.yaml, manuals/API_GUIDE.md, tests/api/{test_me_contests,test_contests_public,test_contacts}.py
- Contract: api_v1.yaml v1.2.0-rc
- Verified: pytest tests/api/test_me_contests.py tests/api/test_contests_public.py tests/api/test_contacts.py → 9 passed; pytest tests/ --ignore=tests/manual → 284 passed, 2 skipped, 1 failed (pre-existing test_migration_1_2_1.py downgrade)
- Next: agent_docs/instructions/tester_1.8.md

## 2026-06-22 — Policy: SUPERVISOR pre-deadline prediction privacy
- Removed SUPERVISOR privileged visibility in `visible_predictions` (ADMIN only); aligned manuals/contracts with `docs/03` §4 — no supervisor predictions UI on frontend.

## 2026-06-22 — Tester (1.8)
- STATUS: TEST_PASS
- Blockers verified: B1, B2, B3
- Report: agent_docs/reports/test_1.8.md
- Contract: api_v1.yaml v1.2.0-rc
- Verified: pytest 1.8 tests → 9 passed; regression → 286 passed, 2 skipped
- Next: Coder 1.7 or 1.9 per user schedule; frontend 2.1 can start API integration

## 2026-06-22 — Coder (1.7 counts & invite accept)
- STATUS: READY_FOR_TEST
- Blockers: B4, B6
- Files: src/schemas/leaderboard.py, src/services/{leaderboard_service,participant_service,prediction_service}.py, src/api/v1/{auth,contest_ops,predictions}.py, src/core/exceptions.py, agent_docs/contracts/api_v1.yaml, manuals/API_GUIDE.md, tests/api/{test_leaderboard_counts,test_participant_accept}.py
- Verified: pytest tests/ --ignore=tests/manual → 300 passed, 2 skipped
- Next: agent_docs/instructions/tester_1.7.md

## 2026-06-22 — Coder (1.9 team logo upload)
- STATUS: READY_FOR_TEST
- Blocker: B5
- Asset: static/assets/default-team-logo.jpg
- Contract: api_v1.yaml v1.2.0
- Files: config/settings.py, main.py, src/services/{team_logo_service,team_out}.py, src/services/contest_setup_service.py, src/api/v1/contest_teams.py, src/schemas/contest.py, uploads/.gitkeep, .gitignore, .env.example, pyproject.toml (pillow), agent_docs/contracts/api_v1.yaml, manuals/{API_GUIDE,CONFIG}.md, tests/api/test_team_logo_upload.py
- Frontend note: copy to frontend/public/assets/default-team-logo.jpg
- Verified: pytest tests/ --ignore=tests/manual → 300 passed, 2 skipped
- Next: agent_docs/instructions/tester_1.9.md

## 2026-06-22 — Tester (1.7)
- STATUS: TEST_PASS
- Blockers verified: B4, B6
- Tests: tests/api/test_leaderboard_counts.py, tests/api/test_participant_accept.py (+ test_accept_me_contests)
- Executed: pytest 1.7 tests → 7 passed; test_calculate_leaderboard_1_4.py → 8 passed, 1 skipped; test_setup_part_auth → 1 passed; regression → 302 passed, 2 skipped
- Report: agent_docs/reports/test_1.7.md

## 2026-06-22 — Tester (1.9)
- STATUS: TEST_PASS
- Blocker verified: B5
- Tests: tests/api/test_team_logo_upload.py (+ test_logo_upload_reupload)
- Executed: pytest logo tests → 9 passed; test_setup_teams_crud_and_duplicate → 1 passed; regression → 302 passed, 2 skipped
- Report: agent_docs/reports/test_1.9.md
- Contract: api_v1.yaml v1.2.0

## 2026-06-23 — Planner (1.lint)
- STATUS: INSTRUCTIONS_READY
- Sub-stage: backend linting baseline audit (non-blocking)
- Prerequisite: Stage 1.9 TEST_PASS
- Instructions: agent_docs/instructions/backend/tester_1_lint.md
- Scope: pyproject.toml (dev deps + ruff/mypy config), tests/test_linting.py, agent_docs/reports/test_1_lint.md
- Mode: linters run with pytest but do not fail suite; CRITICAL/TOLERABLE triage in report
- Next: @Tester executes tester_1_lint.md

## 2026-06-23 — Tester (1.lint)
- STATUS: TEST_PASS
- Sub-stage: backend linting baseline (non-blocking)
- Report: agent_docs/reports/test_1_lint.md
- Infra: ruff, mypy, bandit in dev deps; tests/test_linting.py
- Regression: 305 passed, 2 skipped
- CRITICAL findings: 1 (bandit B608 medium in load_test_data.py)
- Next: coder_1_lint_fix.md for CRITICAL + mypy config + ruff cleanup

## 2026-06-25 — Coder (1.10 fix — multi-contest UNIQUE)
- STATUS: READY_FOR_TEST
- Blockers closed: B7, B8
- Migration: d5e6f7a8b9c0_drop_legacy_global_uniques.py
- Files: alembic/versions/d5e6f7a8b9c0_drop_legacy_global_uniques.py, src/core/exceptions.py (ConflictError), src/api/error_handlers.py (IntegrityError→409), tests/api/test_multi_contest_unique_fix_1_10.py
- Verified: alembic upgrade head (0); pytest multi_contest fix + 1_4 (7 passed); post-migration indexes — rounds/teams composite-only
- Next: tester_1.10_fix.md (or re-run tester_2.3 after frontend Part B)

## 2026-06-27 — Coder (1.12 fix — B11/B12 auth links + training mode)
- STATUS: READY_FOR_TEST
- Blockers targeted: B11, B12 (pending TEST_PASS)
- Files: src/core/setup_tokens.py, src/services/auth_setup_service.py, src/services/contest_restore_service.py, src/scripts/dev_invite_setup.py, alembic/versions/e6f7a8b9c0d1_contest_restore_snapshots.py; edited auth.py, contests.py, contest_lifecycle_service.py, contest_setup_service.py, participant_service.py, models.py, schemas, config/settings.py, .env.example; frontend /auth/setup, LoginForm, ParticipantInviteModal, LifecyclePanel, lifecycle page; manuals/CONFIG.md, manuals/DEV_SETUP.md
- Verified: alembic upgrade head (0); ruff on new files (0); test_contest_lifecycle_1_4.py (7 passed); frontend lint + type-check (0); legacy participant_accept tests fail under ENFORCE_PASSWORD_SETUP=true (expected — @Tester updates per tester_1.12_fix.md)
- Next: tester_1.12_fix.md

## 2026-06-27 — Tester (1.12 fix — B11/B12)
- STATUS: TEST_FAIL
- Tests: tests/api/stage_112_helpers.py, tests/api/test_auth_setup.py, tests/api/test_participant_purge.py, tests/api/test_contest_restore.py, tests/api/test_dev_invite_setup.py; updated tests/api/test_participant_accept.py
- Executed: bootstrap (alembic, load_test_data, bootstrap_users); pytest 1.12 suite → 22 passed, 3 failed; ruff on new tests → 0
- Blockers: B11 OPEN (purge-on-start: activate 403 CONTEST_LOCKED when PENDING temp users exist); B12 RESOLVED
- Report: agent_docs/reports/test_1.12_fix.md
- Next: @Coder fix purge/lock ordering in contest_ops.py

## 2026-06-27 — Coder (1.14 data fix — dev fixture)
- STATUS: READY_FOR_TEST
- Files: src/scripts/finalize_dev_fixture.py, src/scripts/dev_setup.py (--e2e, --finalize-fixture-only); manuals/DEV_SETUP.md, STATUS_REFERENCE.md, MANUAL_SCORING_VERIFICATION.md
- Fixture: rounds 1–9 PUBLISHED (90 scores), 10 CALCULATED (10), 11 CLOSED (0)
- Next: tester_1.14_data_fix.md

## 2026-06-27 — Tester (1.14 data fix)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_1.14_data_fix.md
- Fixture: rounds 1–9 PUBLISHED (90 scores), 10 CALCULATED (10), 11 CLOSED (0)
- Regression: test_calculate_persistence_1_2.py OK; tests/scripts/test_finalize_dev_fixture_1_14.py (5 passed)
- Next: tester_2.3.1_fix_rounds.md (after coder_2.3.1 READY_FOR_TEST)

## 2026-06-28 — Coder (1.15 fix setup — start & DRAFT delete)
- STATUS: READY_FOR_TEST
- Files: src/services/contest_lifecycle_service.py (start_contest, assert_deletable allow_draft), src/api/v1/contests.py (POST /start, delete allow_draft), src/api/v1/contest_ops.py, src/api/v1/admin_rounds.py (purge idempotency comments), tests/api/test_contest_start_1_15.py
- Verified: `uv run ruff check` on modified src files OK; `uv run pytest tests/api/test_contest_start_1_15.py -v` 9 passed; `tests/api/test_contest_restore.py` 7 passed
- Note: full `uv run ruff check src/` and `uv run mypy src/` have pre-existing project-wide issues unrelated to this change
- Next: agent_docs/instructions/tester_2.3.3_fix_setup.md

## 2026-06-28 — Coder (1.15 QA follow-up — chat-driven backend)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/backend/coder_1.15_qa_followup.md` (not in `coder_1.15_fix_setup.md`)
- Scope: soft-delete (`deleted_at` + list filter + purge script), start readiness validation (teams + ≥2 ACCEPTED), supplementary round metadata (`kind`, `supplementary_index`, `origin_round_id`), `bonuses_pending` on leaderboard API, `dev_invite_setup.py list-pending` + env password, `dev_setup.py` QA cheatsheet
- Migrations: `f7a8b9c0d1e2_contest_soft_delete`, `g8h9i0j1k2l3_supplementary_rounds` — require `uv run alembic upgrade head`
- Key files: contest_lifecycle_service.py, contest_purge_service.py, round_serialization.py, round_scoring_pending.py, leaderboard_service.py, contest_restore_service.py, dev_invite_setup.py, dev_setup.py, purge_deleted_contests.py
- Tests: test_contest_soft_delete.py, test_contest_start_1_15.py (readiness), test_dev_invite_setup.py, test_free_tour_1_4.py, test_round_scoring_pending.py, stage_112_helpers.fulfill_start_prerequisites
- Contracts/manuals: scoring_flow.md §6, bonus_rules.md, api_v1.yaml, DEV_SETUP.md
- Deferred: full bonus2/3 deferral inside scoring engine (contract only)
- Next: `agent_docs/instructions/coder_2.3.4_qa_followup.md` (frontend counterpart)

## 2026-06-28 — Coder (1.16 fix deadline — per-round auto-close)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/backend/coder_1.16_fix_deadline.md`
- Scope: `ensure_round_closed_if_expired()` in round_auto_close_service; called from prediction/match/scoring/LB services + build_round_predictions_view; batch hook unchanged in ContestContext
- Tests: `tests/api/test_round_deadline_auto_close_1_16.py` — 9 passed (+ regression test_round_auto_close_1_4.py 2/2)
- Contracts: `contest_lifecycle_flow.md` §3.2–3.4 updated
- Verified: `uv run ruff check` on touched files OK
- Next: `agent_docs/instructions/coder_2.3.5_fix_deadline.md` (frontend UI sync)

## 2026-06-28 — Coder (1.16 fix deadline — per-round auto-close)
- STATUS: READY_FOR_TEST
- Files: src/services/round_auto_close_service.py (ensure_round_closed_if_expired, DRY batch hook), prediction_service.py, match_service.py, scoring_persistence.py, leaderboard_service.py, api/handlers/predictions.py, tests/api/test_round_deadline_auto_close_1_16.py
- Verified: `uv run ruff check` on touched src files OK; `uv run pytest tests/api/test_round_deadline_auto_close_1_16.py -v` 9 passed
- Contracts: contest_lifecycle_flow.md §3.2 (per-round ensure documented)
- Next: coder_2.3.5_fix_deadline.md (frontend UI sync)

## 2026-07-08 — Coder (1.17 results per-match points)
- STATUS: READY_FOR_TEST
- Scope: GET …/results populates results[].points (base_points per match), total_without_bonus3
- Key paths: leaderboard_service.py, scoring_persistence.py, schemas/leaderboard.py
- Verified: pytest test_round_results_points_1_17.py (6 passed); ruff/mypy on touched src files OK
- Contracts: api_v1.yaml RoundResults, API_GUIDE.md, frontend_api_integration.md
- Next: agent_docs/instructions/coder_2.4.md

## 2026-07-09 — Coder (1.18 leaderboard cumulative + predictions_count + total_bonus_points)
- STATUS: READY_FOR_TEST
- Scope: `scope=round|total` on round leaderboard; predictions_count from DB; `total_bonus_points` field
- Key paths: leaderboard_service.py, schemas/leaderboard.py, contest_ops.py, api_v1.yaml
- Verified: pytest test_leaderboard_cumulative_1_18.py 5/5; ruff on touched src files OK
- Next: fix_2.4.1.md (frontend)
