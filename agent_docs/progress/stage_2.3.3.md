# Stage 2.3.3 — Contest Setup UX Fix

## 2026-06-28 — Coder
- STATUS: READY_FOR_TEST
- Files:
  - `frontend/src/components/admin/CreateContestForm.tsx` — name + slug only
  - `frontend/src/components/admin/AdminTopNav.tsx` — slim create payload, setup hint flag
  - `frontend/src/lib/validation/admin.ts` — slim schema, `deriveRoundRobinStructure`
  - `frontend/src/components/admin/ContestParametersForm.tsx` — round-robin sync, help, hint
  - `frontend/src/components/admin/ContestLifecycleActions.tsx` — start + delete CTAs
  - `frontend/src/lib/api/endpoints.ts` — `contests.start`
  - `frontend/src/app/admin/settings/parameters/page.tsx` — lifecycle callbacks
  - `frontend/src/components/admin/LifecyclePanel.tsx` — DRAFT delete copy
  - `frontend/src/components/admin/RoundManagementPanel.tsx` — activate modal when locked
  - `frontend/src/lib/validation/admin.test.ts` — round-robin derive tests
  - `frontend/e2e/admin_setup.spec.ts` — E2E-ADMIN-START, CREATE-MODAL, PARAMS-ROUND-ROBIN
  - `frontend/e2e/fixtures/adminApi.ts` — `startContest()`, flexible `createDraftContest`
  - `manuals/SUPERVISOR_TESTING_SCENARIOS.md` — S1.11, S0.6/S0.7, S1.12
- Verified: `cd frontend && npm run lint && npm run type-check && npm run test:unit` — all pass (94 tests)
