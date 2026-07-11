# Test Report — Stage 2.3.3 Fix Setup

**Date:** 2026-06-28  
**Coder:** `coder_2.3.3_fix_setup.md` + `backend/coder_1.15_fix_setup.md`  
**Tester instruction:** `tester_2.3.3_fix_setup.md`  
**Environment:** API `:8000` (manual uvicorn), UI `:3000` (Playwright webServer), `SEED_SUPERVISOR_PASSWORD` set, `SUPERVISOR_TRAINING_MODE=true` (backend pytest)

## Summary

Проверен полный автоматизированный контур Stage 2.3.3 + backend 1.15: упрощённая модалка создания, round-robin auto-sync, запуск конкурса через `POST /contests/{id}/start`, удаление DRAFT в training mode и restore через API. **16/16 pytest**, **101/101 Vitest** (добавлены `[UNIT-CREATE-SCHEMA]`, `[UNIT-PARAMS-SCHEMA]`, 16 teams derive), **9/9 Playwright E2E**. Ручные сценарии S1.11 и UI delete/restore, а также E2E activate-copy — не прогонялись (нет spec / требует отдельной env-настройки frontend training mode).

## Results

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-CREATE-SCHEMA]` | PASS | `admin.test.ts`: name only, empty name reject, strips `total_teams` |
| `[UNIT-ROUND-ROBIN-DERIVE]` | PASS | 8/10/16 teams → matches 4/5/8, rounds 14/18/30 |
| `[UNIT-PARAMS-SCHEMA]` | PASS | round-robin valid/invalid + arbitrary mode |
| `[API-START-DRAFT]` | PASS | `test_start_draft`, `test_start_idempotent`, `test_start_draft_patch` |
| `[API-START-PURGE]` | PASS | `test_start_purge` — PENDING removed, ACCEPTED kept |
| `[API-DELETE-DRAFT-TRAIN]` | PASS | `test_delete_draft_train` |
| `[API-RESTORE-WINDOW]` | PASS | `test_restore_after_draft_del`, `test_restore_window` |
| `[E2E-CREATE-MODAL]` | PASS | name + slug only, no teams/tours/round-robin |
| `[E2E-ADMIN-SETUP]` | PASS | parameters save, teams CRUD, invite modal |
| `[E2E-PARAMS-ROUND-ROBIN]` | PASS | auto-fill 10 teams + arbitrary mode save |
| `[E2E-ADMIN-START]` | PASS | UI start → LockBanner; API start → reload locked |
| `[E2E-ADMIN-LOCK]` | PASS | contest id=1 LockBanner + disabled controls |
| `[E2E-ACTIVATE-COPY]` | SKIP | spec not implemented (`admin_setup.spec.ts` has no activate modal test) |
| `[E2E-DELETE-RESTORE]` | SKIP | no `admin_contest_delete_restore.spec.ts`; covered by API pytest |
| `[LINT-ESLINT]` | PASS | `npm run lint` |
| `[LINT-TSC]` | PASS | `npm run type-check` |
| `[LINT-FORMAT]` | FAIL | `format:check` — 7 files (Coder components + `admin.test.ts`); pre-existing |
| `[BUILD]` | SKIP | not run this session |
| `[DOC-SCENARIOS]` | PASS | S0.6, S1.11, S1.12 rows present in `SUPERVISOR_TESTING_SCENARIOS.md` |
| `[DOC-API]` | FAIL | `POST /contests/{id}/start` not listed in `manuals/dev/API_GUIDE.md` contest table |
| `[DOC-LIFECYCLE]` | FAIL | `contest_lifecycle_flow.md` has no DRAFT→RUNNING via `/start` row |
| Manual S1.1–S1.4, S0.6, S1.11 | SKIP | not executed this session |
| BLOCKED.md | OK | no new blockers |

## Execution log

| Command | Result |
|---------|--------|
| `uv run pytest tests/api/test_contest_start_1_15.py -v` | 9 passed |
| `uv run pytest tests/api/test_contest_restore.py -v` | 7 passed |
| `npm run lint && npm run type-check && npm run test:unit` | lint OK, tsc OK, 101 passed |
| `npm run test:e2e -- e2e/admin_setup.spec.ts e2e/admin_setup_locked.spec.ts` | 9 passed (37.9s) |
| `npm run format:check` | 7 files with style warnings |

## Tester changes

| File | Change |
|------|--------|
| `frontend/src/lib/validation/admin.test.ts` | Added `[UNIT-CREATE-SCHEMA]`, `[UNIT-PARAMS-SCHEMA]`, 16-team derive case |

## Defects for @Coder (non-blocking automated PASS)

1. **`[DOC-API]`** — Document `POST /contests/{id}/start` in `manuals/dev/API_GUIDE.md` (SUPERVISOR+, DRAFT→RUNNING, sets `is_locked`, purges PENDING).
2. **`[DOC-LIFECYCLE]`** — Add start transition to `agent_docs/contracts/contest_lifecycle_flow.md`.
3. **`[E2E-ACTIVATE-COPY]`** — Add Playwright test for activate modal copy after contest already locked (T8).
4. **`[E2E-DELETE-RESTORE]`** — Optional UI spec with `NEXT_PUBLIC_SUPERVISOR_TRAINING_MODE=true`.
5. **`[LINT-FORMAT]`** — Run Prettier on Coder-touched frontend files.

## Verdict

**TEST_PASS** (automated scope: pytest 16/16, Vitest 101/101, E2E 9/9). Documentation gaps and skipped manual/optional E2E noted above — recommended follow-up before production sign-off.
