# Stage 2 Progress

## 2026-06-23 — Coder (2.1 foundation & auth)
- STATUS: READY_FOR_TEST
- Scope: frontend scaffold, auth, profile, contest discovery, contacts
- Blockers used: B1, B2, B3 (live API)
- Key paths: frontend/src/app/{page,profile,contests,change-password}, lib/api, providers
- Verified: npm run build (0), npm run lint (0), npm run type-check (0), npm run format:check (0), npm run test:unit (0, 15 tests)
- Docs updated: ui/components.md, ui/pages.md, ui/state_management.md, ui/forms_validation.md, frontend_api_integration.md
- Next: agent_docs/instructions/tester_2.1.md, then coder_2.2.md

## 2026-06-24 — Tester (2.1)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.1.md
- Unit: 18 passed; E2E: 10 passed (0 skipped)
- Build: OK
- Env notes: `[ENV-LOADER-AUTH]` user/user login broken on stock dev_setup — E2E uses API provisioning workaround
- Manual UX checklist: reminded in report §8
- Next: instructions/coder_2.2.md

## 2026-06-24 — Planner (2.1.1 routing hotfix + admin stubs)
- STATUS: INSTRUCTIONS_READY
- Artifacts: instructions/coder_2.1.1.md, instructions/tester_2.1.1.md
- Plan updated: draft_2.md — order 2.1 → 2.1.1 → 2.3 → 2.2 → 2.4
- Prerequisites updated: coder_2.3/tester_2.3 (2.1.1, not 2.2); coder_2.2/tester_2.2 (requires 2.3 TEST_PASS)
- Contracts/UI: frontend_api_integration.md §2.4; pages.md admin stubs + USER-only /profile
- Todo: demo user removal after 2.3; CONTEST_LOCKED invite note
- Next: @Coder → coder_2.1.1.md; then tester_2.1.1.md

## 2026-06-24 — Coder (2.1.1 routing hotfix + demo user + admin stubs)
- STATUS: READY_FOR_TEST
- Scope: resolvePostLoginPath, role guards, /admin stubs, bootstrap demo user
- Key paths: frontend/src/lib/auth/resolvePostLoginPath.ts, app/admin/*, bootstrap_users.py
- Verified: dev_setup.py (0); user/user API login 200; npm run test:unit (22 passed); lint (0); type-check (0); format:check (0); build (0)
- Docs updated: ui/pages.md, ui/components.md, ui/state_management.md, DEV_SETUP.md, frontend_api_integration.md (verified §2.4)
- Next: agent_docs/instructions/tester_2.1.1.md

## 2026-06-24 — Tester (2.1.1)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.1.1.md
- Unit: 22 passed; E2E: 18 passed (0 skipped)
- Bootstrap: user/user API login OK
- Follow-up: completed after Tester subagent crash; routing race + admin bootstrap temp flag fixed
- Next: coder_2.2.md (predictions)

## 2026-06-24 — Coder (2.3 supervisor admin UI)
- STATUS: READY_FOR_TEST
- Scope: /admin settings, rounds, results, lifecycle, B5 logo upload
- UI rules: is_locked readonly, ACTIVE round restrictions, 24h, newsletter stub
- Verified: npm run build (0), npm run test:unit (36 passed)
- Docs updated: ui/*, frontend_api_integration.md, manuals/FRONTEND_REFERENCE.md §2.3
- Next: agent_docs/instructions/tester_2.3.md

## 2026-06-25 — Tester (2.3)
- STATUS: TEST_FAIL
- Report: agent_docs/reports/test_2.3.md
- Unit: 36 passed; E2E (2.3 specs): 1 passed / 15 failed
- Build: OK; Lint/TSC: OK; Prettier: FAIL (18 files)
- Blockers: B7 (`rounds.number` global UNIQUE), B8 (`teams.name` global UNIQUE) — `agent_docs/reports/BLOCKED.md`
- Tests: frontend/e2e/admin_*.spec.ts, supervisor_*.spec.ts, fixtures/adminApi.ts
- Env: `load_test_data.py --reset` + `bootstrap_users.py` + `dev_setup.py --ensure-running-only` required
- Manual UX checklist: reminded in report §10
- Next: @Coder fix B7/B8, VOID UX, Prettier; re-run tester_2.3.md

## 2026-06-25 — Coder (1.10 fix — 2.3 unblock)
- STATUS: READY_FOR_RETEST
- Frontend: canVoidMatch on PUBLISHED, MatchResultRow scoresReadonly/canVoid split, prettier on admin files
- Backend: B7/B8 resolved — see stage_1 handoff
- Verified: npm run test:unit (37 passed), format:check (0), lint (0), build (0); type-check fails on pre-existing e2e/*.spec.ts TS errors (out of scope)
- Next: re-run agent_docs/instructions/tester_2.3.md

## 2026-06-25 — Retest (2.3 after 1.10 fix)
- STATUS: TEST_FAIL (partial)
- Blockers B7/B8: RESOLVED ✅ — pytest 7/7; BLOCKED.md updated
- Unit: 37 passed; Prettier/build/lint: OK; TSC: fail (e2e/*.spec.ts pre-existing)
- E2E 2.3: 4 passed / 13 failed (E2E spec bugs + PAUSED contest teardown, not migration)
- Bootstrap order fix: load_test_data --reset → bootstrap_users → dev_setup --ensure-running-only
- Report: agent_docs/reports/test_2.3.md § Retest
- Next: tester fixes E2E helpers + re-run tester_2.3.md

## 2026-06-25 — Planner (2.3.1 E2E fix instructions)
- STATUS: INSTRUCTIONS_READY
- Artifact: agent_docs/instructions/tester_2.3.1_fix.md
- Scope: E2E fixtures T1–T9, bootstrap order, type-check green, full tester_2.3 re-run
- Prerequisite: Coder 1.10 fix (B7/B8 RESOLVED)
- Next: @Tester → tester_2.3.1_fix.md

## 2026-06-25 — Planner (2.3.2 E2E fix + .env credentials)
- STATUS: INSTRUCTIONS_READY
- Artifact: agent_docs/instructions/tester_2.3.2_fix.md
- Scope: U1–U9 loaded contest reset, round id helpers, .env-only passwords, create-round API workaround
- Next: @Tester → tester_2.3.2_fix.md

## 2026-06-25 — Tester (2.3.1 fix)
- STATUS: TEST_FAIL (partial improvement)
- Report: agent_docs/reports/test_2.3.md § Retest 2.3.1
- Fixed: T1–T9 (adminApi adminToken, imports, TS, selectors, setup team limit, global-setup passwords, tester_2.3 bootstrap)
- Unit: 37 passed; Lint/TSC/Prettier/Build: OK
- E2E 2.3: **8 passed / 9 failed** (was 4/17)
- BLOCKED.md: B7/B8 confirmed RESOLVED
- Next: second E2E fix pass (contest context, round labels, credentials) or Coder if UI defect

## 2026-06-25 — Tester (2.3.2 fix)
- STATUS: TEST_PASS ✅
- Report: agent_docs/reports/test_2.3.md § Retest 2.3.2
- Fixed: U1–U9; dev_setup round-10 date shift (auto-close root cause); UI login for E2E sessions; locked/pause assertions (`not.toBeVisible` for hidden save buttons)
- Unit: 37 passed; Lint/TSC/Prettier/Build: OK
- E2E 2.3: **17 passed / 0 failed** (was 8/17)
- Credentials: root `.env` `SEED_*` only (no `E2E_*` in Playwright)
- BLOCKED.md: B7/B8 RESOLVED; B9 not required
- Next: @Coder → agent_docs/instructions/coder_2.4.md

## 2026-06-27 — Coder (2.3.1 fix rounds/status/24h/LB gate)
- STATUS: READY_FOR_TEST
- Scope: F1–F12 — 24h policy (placement vs lockout), per-status round panels, pre-deadline ACTIVE edit, LockBanner scope, create-tour CTA, DRAFT edit, public LB PUBLISHED-only
- Key paths: `round_service.py`, `leaderboard_service.py`, `deadlineRule.ts`, `deriveAdminUiMode.ts`, `RoundManagementPanel.tsx`, `RoundPhasePanel.tsx`, settings `showSetupLockBanner`
- Tests updated: `deadlineRule.test.ts`, `deriveAdminUiMode.test.ts`, `test_deadline_batch_1_2.py`, `test_services_1_2.py`, `test_leaderboard_published_only_2_3_1.py`, `test_calculate_leaderboard_1_4.py`
- Verified: frontend unit 46 passed; lint/tsc 0; backend deadline + LB pytest green
- Next: `agent_docs/instructions/tester_2.3.1_fix_rounds.md`

## 2026-06-27 — Tester (2.3.1 fix rounds)
- STATUS: TEST_PASS (automated); E2E SKIP (API :8000 down)
- Report: `agent_docs/reports/test_2.3.1_fix_rounds.md`
- Unit: 46 passed; backend: deadline batch 20/20, LB gate 3/3, calculate regression 8/8 (1 skip)
- E2E: not run — connection refused; manual 1.14 matrix not spot-checked
- Gaps: new E2E specs for status panels / public LB gate; contracts sync
- Next: run E2E with stack up; optional `coder_2.4` / supervisor rename queue

## 2026-06-27 — Re-verify 2.3.1 (interrupted dev check)
- Coder code: present (F1–F12); contracts + public LB UI stub wiring still open
- Automated: frontend 60/60, backend 32/32 (+1 skip), lint/tsc OK
- Fixed: `test_lb_public_published_round_allowed`, `admin.ts` lint, E2E spec semantics (24h/active/copy)
- E2E: BLOCKED — global-setup `PASSWORD_SETUP_REQUIRED` for provision user
- Report refreshed: `agent_docs/reports/test_2.3.1_fix_rounds.md`

## 2026-06-27 — Coder (2.3.2 backend calculated edit)
- STATUS: READY_FOR_TEST
- Files: `src/services/match_service.py` (set_result CLOSED|CALCULATED + auto recalc), `tests/api/test_results_calculated_edit_2_3_2.py`, `manuals/API_GUIDE.md`, `manuals/STATUS_REFERENCE.md`
- Verified: `pytest tests/api/test_results_calculated_edit_2_3_2.py -q` 4/4; `pytest tests/api/test_calculate_leaderboard_1_4.py -q` 8/8 (+1 skip); `ruff check src/services/match_service.py` OK
- Tag: [API-RESULT-CALCULATED]
- Next: @Tester → `agent_docs/instructions/tester_2.3.2_fix_tours.md` or `tester_2.3.2_backend_calculated_edit.md`; frontend B3 unlock (`coder_2.3.2_fix_tours.md` §5)

## 2026-06-27 — Coder (2.3.2 frontend tours/results UX)
- STATUS: READY_FOR_TEST
- Scope: T1–T12 + B3 unlock (matchResultsGating, deriveAdminUiMode, RoundPhasePanel, ResultsEntryPanel, MatchResultRow)
- Key paths: `frontend/src/lib/admin/matchResultsGating.ts`, `deriveAdminUiMode.ts`, `RoundPhasePanel.tsx`, `ResultsEntryPanel.tsx`, E2E specs (tours_phase_panels, results_kickoff, results_preview)
- Verified: Vitest 82/82; lint/tsc OK; format fixed
- Next: `agent_docs/instructions/tester_2.3.2_fix_tours.md`

## 2026-06-27 — Tester (2.3.2 fix tours + backend calculated edit)
- STATUS: TEST_PASS (automated); E2E SKIP (UI :3000 down)
- Report: `agent_docs/reports/test_2.3.2_fix_tours.md`
- Unit: 82 passed; backend: calculated edit 4/4, calculate regression 8/8 (+1 skip), LB gate 5/5
- E2E: specs created, not run — UI connection refused; API :8000 up
- Next: `dev_setup.py --run-only` + `npm run test:e2e`; manual 1.14 matrix QA

## 2026-06-28 — Coder (1.15 fix setup — backend)
- STATUS: READY_FOR_TEST
- Files: `contest_lifecycle_service.py` (start_contest, assert_deletable allow_draft), `contests.py` (POST /start), tests/api/test_contest_start_1_15.py
- Verified: pytest 9/9 start+delete; restore regression 7/7

## 2026-06-28 — Coder (2.3.3 fix setup — frontend)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/coder_2.3.3_fix_setup.md`
- Files:
  - `CreateContestForm.tsx` — name + slug only
  - `AdminTopNav.tsx` — slim create payload, setup hint flag
  - `lib/validation/admin.ts` — slim schema, `deriveRoundRobinStructure`
  - `ContestParametersForm.tsx` — round-robin sync, help, hint
  - `ContestLifecycleActions.tsx` — start + delete CTAs
  - `lib/api/endpoints.ts` — `contests.start`
  - `app/admin/settings/parameters/page.tsx` — lifecycle callbacks
  - `LifecyclePanel.tsx` — DRAFT delete copy
  - `RoundManagementPanel.tsx` — activate modal when locked
  - `lib/validation/admin.test.ts` — round-robin derive tests
  - `e2e/admin_setup.spec.ts` — E2E-ADMIN-START, CREATE-MODAL, PARAMS-ROUND-ROBIN
  - `e2e/fixtures/adminApi.ts` — `startContest()`, flexible `createDraftContest`
  - `manuals/SUPERVISOR_TESTING_SCENARIOS.md` — S1.11, S0.6/S0.7, S1.12
- Verified: lint/tsc OK; Vitest 94/94

## 2026-06-28 — Tester (2.3.3 fix setup)
- STATUS: TEST_PASS (automated)
- Report: `agent_docs/reports/test_2.3.3_fix_setup.md`
- API: 16/16; Unit: 94/94; E2E: 9/9 (admin_setup + admin_setup_locked)
- Skip: E2E delete/restore UI, manual S1.11, E2E activate copy
- Fix during test: `adminApi.startContest` → GET contest after POST /start

## 2026-06-28 — Tester (2.3.3 fix setup — re-verify)
- STATUS: TEST_PASS
- Report: `agent_docs/reports/test_2.3.3_fix_setup.md` (updated)
- Unit: 101 passed (+7 schema tests in `admin.test.ts`); API: 16/16; E2E: 9/9
- Contest start from Parameters + lock verified (S1.12, S1.4 via E2E)
- Delete/restore: API OK; UI E2E skipped (training mode frontend env)
- Skip: manual S1.11, `[E2E-ACTIVATE-COPY]`, `[LINT-FORMAT]` (7 Coder files)
- Next: @Coder — document `POST /start` in API_GUIDE; optional activate-copy + delete/restore E2E

## 2026-06-28 — Coder (2.3.4 QA follow-up — chat-driven frontend)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/coder_2.3.4_qa_followup.md` (not in `coder_2.3.3_fix_setup.md`)
- Backend dependency: `agent_docs/instructions/backend/coder_1.15_qa_followup.md`
- Scope: contest context fix (ContestProvider), RulesEditorPanel + rules_json PATCH + auto-save before start, start readiness panel (variant 2), ДопТур labels (roundLabel.ts), bonuses_pending UI notes, contest-setup-changed events; removed ContestSetupDebugBar
- Key files: RulesEditorPanel.tsx, rulesEditor.ts, ContestStartReadinessPanel.tsx, useContestStartReadiness.ts, contestStartReadiness.ts, roundLabel.ts, roundScoringPending.ts, RoundLeaderboardPreview.tsx, ResultsEntryPanel.tsx, RoundManagementPanel.tsx, FreeTourModal.tsx, ContestLifecycleActions.tsx, useTeams.ts, useParticipants.ts, types/api.ts (RoundOut)
- E2E: admin_setup.spec.ts, adminApi.ts (`fulfillStartPrerequisites`, `inviteParticipant`)
- Verified: lint/tsc OK; Vitest 101+ (incl. rulesEditor, roundLabel, contestStartReadiness tests)
- Manuals: SUPERVISOR_TESTING_SCENARIOS.md — S1.2, S2.23
- Next: optional tester pass for 2.3.4; scoring engine bonus deferral (backend follow-up)

## 2026-06-28 — Coder (2.3.5 fix deadline — UI sync)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/coder_2.3.5_fix_deadline.md`
- Backend dependency: `coder_1.16_fix_deadline.md`
- Scope: `roundEffectiveStatus.ts`, `useRoundMatches` onDeadlinePassed → refetch rounds, phase panel routing, Results eligible rounds, removed manual «Закрыть тур» UX; `deriveAdminUiMode` uses effective status
- Key files: roundEffectiveStatus.ts, useRoundMatches.ts, admin/rounds/page.tsx, admin/results/page.tsx, RoundManagementPanel.tsx, RoundStatusSidebar.tsx, ResultsEntryPanel.tsx, deriveAdminUiMode.ts
- Verified: lint/tsc OK; Vitest 118/118
- Next: tester pass for deadline transition (optional E2E)

## 2026-06-28 — Coder (2.2 predictions & privacy)
- STATUS: READY_FOR_TEST
- Scope: PredictionForm, PredictionsMatrix, deadline UX, privacy helpers, PublicTabs, RoundSelector
- UI rules: batch-only, 0..maxScore, **empty≠0 (no coerce)**, NULL≠0, 24h warning, privacy pre/post deadline
- Key paths: `frontend/src/components/predictions/*`, `frontend/src/app/contest/[contestId]/*`, `frontend/src/lib/privacy/*`, `frontend/src/lib/validation/{score,prediction}.ts`
- Verified: npm run test:unit (150 passed), lint/tsc OK; prettier fixed
- Docs updated: ui/*, frontend_api_integration.md, manuals/FRONTEND_REFERENCE.md §2.2
- Next: agent_docs/instructions/tester_2.2.md

## 2026-06-28 — Planner (2.2.1 visitor public predictions)
- STATUS: INSTRUCTIONS_READY
- Artifacts: `backend/coder_1.16_fix_public_predictions.md`, `coder_2.2.1.md`, `tester_2.2.1.md`
- Goal: align `docs/03_user_scenarios.md` §4 — Visitor sees full predictions post-deadline without login (reverts 2.2 §5.4 login-prompt deviation)
- Order: backend 1.16 public predictions → frontend 2.2.1 → tester 2.2.1
- Note: distinct from `coder_1.16_fix_deadline.md` (auto-close, already shipped)

## 2026-06-28 — Coder (1.16 public predictions — backend)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/backend/coder_1.16_fix_public_predictions.md`
- Scope: OptionalUser on GET predictions; 403 `PREDICTIONS_NOT_PUBLIC` pre-deadline anonymous; full table post-deadline; legacy shim aligned
- Key files: contest_ops.py, predictions.py, handlers/predictions.py, prediction_service.py, test_predictions_public_1_16.py
- Contracts: api_v1.yaml, frontend_api_integration.md §5.4, contest_lifecycle_flow.md §3.3, manuals/API_GUIDE.md
- Verified: pytest predictions 9/9; ruff on touched files

## 2026-06-28 — Coder (2.2.1 visitor public predictions — frontend)
- STATUS: READY_FOR_TEST
- Instruction: `agent_docs/instructions/coder_2.2.1.md`
- Scope: guest post-deadline public matrix; deadline gate via `isDeadlinePassedNow`; removed PredictionsLoginPrompt; `prediction-score` testid; apiFetch 401 fix for tokenless callers
- Key files: contest/[contestId]/page.tsx, PredictionsMatrix.tsx, lib/contest/deadline.ts, lib/api/client.ts
- Verified: lint/tsc/format/build OK; Vitest 151/151

## 2026-06-28 — Tester (2.2.1)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_2.2.1.md
- E2E: visitor stub + public, privacy, batch, user predict — 6/6 PASS
- Note: full pytest 368 pass / 15 fail (pre-existing, out of 2.2.1 scope)

## 2026-06-28 — Tester (1.16 fix — pytest regression cleanup)
- STATUS: TEST_PASS
- Report: agent_docs/reports/test_1.16_fix.md
- Instruction: agent_docs/instructions/tester_1.16_fix.md
- Scope: 15 stale tests updated (password setup, ETag, tiebreak, LB counts, soft-delete, auto-close)
- Verified: full pytest 383 passed / 1 skipped / 0 failed
