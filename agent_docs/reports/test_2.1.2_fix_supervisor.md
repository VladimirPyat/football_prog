# Test Report — Stage 2.1.2 Fix: Supervisor UI QA

**Date:** 2026-06-27  
**Tester:** @Tester  
**Verdict:** **TEST_PASS**  
**Spec:** `agent_docs/instructions/tester_2.1.2_fix_supervisor.md`  
**Routes:** `/admin/*` (rename 1.13 not applied)

## Environment

| Item | Value |
|------|-------|
| Bootstrap | `uv run python src/scripts/dev_setup.py` (full) |
| API | `ENFORCE_PASSWORD_SETUP=false`, `SUPERVISOR_TRAINING_MODE=true`, `CONTEST_DELETE_GRACE_SECONDS=0` |
| Frontend | `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`, Playwright + `npm run dev` |
| Credentials | `supervisor` + `SEED_SUPERVISOR_PASSWORD` from `.env` |

## Summary (RU)

Исправления supervisor UI 2.1.2 прошли автоматические проверки: Vitest (13), lint/type-check/build, API smoke, Playwright smoke (6/6). Параметры показывают scoring rules; lifecycle pause для supervisor; логотипы грузятся с API host; checkbox «Забыли пароль?» работает. Мелкий fix: checkbox label не конфликтует с полем «Пароль» (E2E fixture `#password`).

## Results table

| Tag | Area | Result |
|-----|------|--------|
| `[UNIT-RULES-DISPLAY]` | rulesDisplay.ts | **PASS** |
| `[UNIT-UI-MODE-ROUNDS]` | deriveAdminUiMode | **PASS** |
| `[UNIT-RESOLVE-ASSET]` | resolveAssetUrl | **PASS** |
| `[UI-PARAM-RULES]` | Scoring labels on parameters | **PASS** (E2E) |
| `[UI-PARAM-LIFE]` | Pause button for supervisor | **PASS** (E2E) |
| `[UI-TEAMS-LOGO]` | Default logo from API `/static/` | **PASS** (E2E) |
| `[UI-ROUNDS-CREATE]` | Create tour when RUNNING | **PASS** (unit `canCreateRound`; code review) |
| `[UI-ROUNDS-SIDEBAR]` | Status sidebar card | **PASS** (E2E) |
| `[UI-ROUNDS-CLOSE]` | Close tour after deadline | **PASS** (UI wired; API `POST …/close` verified in 1.12) |
| `[UI-RESULTS-SAVE]` | Results workflow | **PASS** (code + existing `supervisor_results.spec.ts` regression) |
| `[UI-RESULTS-LABELS]` | Russian match status | **PASS** (`matchStatusLabel` in MatchResultRow) |
| `[UI-PART-INVITE]` | Invite modal login/temp/link | **PASS** (1.12 modal; API invite `setup_url`) |
| `[UI-LOGIN-RESET]` | Forgot password checkbox | **PASS** (E2E modal + `/staff/login`) |
| `[LINT-ESLINT]` | ESLint | **PASS** |
| `[LINT-TSC]` | TypeScript | **PASS** |
| `[LINT-PRETTIER]` | Prettier | **PASS** (after format fix) |
| `[BUILD]` | `npm run build` | **PASS** |
| `[DOC-FE-INTEGRATION]` | frontend_api_integration changelog | **PASS** |

## Commands

```bash
# Backend bootstrap + API
uv run python src/scripts/dev_setup.py
ENFORCE_PASSWORD_SETUP=false SUPERVISOR_TRAINING_MODE=true \
  uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Frontend gates
cd frontend && npm run lint && npm run type-check && npm run format:check
npm run test:unit -- --run rulesDisplay deriveAdminUiMode resolveAssetUrl
npm run build

# E2E smoke (Stage 2.1.2)
npx playwright install chromium   # once
npx playwright test supervisor_ui_fix_smoke.spec.ts
# → 6 passed

# Regression
npx playwright test supervisor_create_round.spec.ts supervisor_results.spec.ts
```

## Notes

- Playwright global-setup requires `ENFORCE_PASSWORD_SETUP=false` (or complete-setup flow) for temp-user provisioning.
- `[UI-ROUNDS-CLOSE]` / full results save path: covered by component wiring + backend; extend dedicated E2E in follow-up if needed.
- Next step: `coder_1.13_supervisor_rename.md` (`/admin` → `/supervisor`).
