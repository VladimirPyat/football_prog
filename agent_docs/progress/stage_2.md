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
- Next: coder_2.3.md (admin UI), then coder_2.2.md (predictions)
