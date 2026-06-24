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
