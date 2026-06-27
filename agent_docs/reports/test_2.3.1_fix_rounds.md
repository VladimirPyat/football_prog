# Test Report — Stage 2.3.1 Fix: Round Statuses, 24h Rule, Public LB Gate

> **Date:** 2026-06-27 (re-verified)  
> **Coder spec:** `agent_docs/instructions/coder_2.3.1_fix.md`  
> **Tester spec:** `agent_docs/instructions/tester_2.3.1_fix_rounds.md`  
> **Verdict:** **TEST_PASS** (unit + backend); E2E **BLOCKED** (global-setup user provisioning)

---

## Executive summary

Разработка **2.3.1 не пустая** — код и тесты на месте. Прерванный subagent не помешал: основная реализация завершена в родительской сессии. Повторная проверка подтвердила **32 backend + 60 frontend unit** тестов. Исправлены: падающий `test_lb_public_published_round_allowed`, ESLint в `admin.ts`, устаревшие E2E-спеки (24h lockout, copy «Тур активен»). E2E не прошли из‑за `playwright.global-setup` (403 `PASSWORD_SETUP_REQUIRED` для provision user) — инфраструктурный блокер, не регресс 2.3.1.

---

## Coder — что сделано (F1–F12)

| ID | Статус | Ключевые файлы |
|----|--------|----------------|
| F1 | ✅ | `format.ts` — `roundStatusHint`, `CLOSED` → «Дедлайн» |
| F2 | ✅ | `round_service.py`, `deadlineRule.ts` — placement vs lockout |
| F3–F5 | ✅ | `deriveAdminUiMode.ts`, `MatchEditorRow.tsx`, activate modal |
| F6–F7 | ✅ | `RoundPhasePanel.tsx`, `RoundLeaderboardPreview.tsx` |
| F8 | ✅ | `AdminPageShell` — `showSetupLockBanner` только на settings |
| F9–F10 | ✅ | `RoundManagementPanel` — «+ Создать тур», DRAFT edit |
| F11 | ✅ | PUBLISHED «Отменить» stub |
| F12 API | ✅ | `leaderboard_service.py` — public `PUBLISHED` only |
| F12 UI public pages | ⚠️ | `roundPublicVisibility.ts` есть, **не подключён** к user LB pages |

**Не сделано (non-blocking):** sync `agent_docs/contracts/*` + `api_v1.yaml`; E2E `supervisor_round_status_panels.spec.ts`.

---

## Automated test results (2026-06-27 re-run)

### Frontend

| Command | Result |
|---------|--------|
| `npm run test:unit` | **60/60 passed** |
| `npm run lint` | **0 errors** |
| `npm run type-check` | **OK** |

### Backend

| Suite | Result |
|-------|--------|
| `test_services_1_2.py -k deadline` | **6/6** |
| `test_deadline_batch_1_2.py` | **12/12** |
| `test_leaderboard_published_only_2_3_1.py` | **5/5** |
| `test_operational_gaps_1_4.py::test_op_24h_rule` | **1/1** |
| `test_calculate_leaderboard_1_4.py` | **8 passed, 1 skipped** |
| **Total** | **32 passed, 1 skipped** |

### E2E Playwright

```text
supervisor_24h_rule / supervisor_active_round / supervisor_create_round
→ BLOCKED at global-setup: Login failed 403 PASSWORD_SETUP_REQUIRED
```

Спеки обновлены под 2.3.1, но прогон не дошёл до тестов.

---

## PASS / FAIL matrix (F1–F12)

| ID | Result | Notes |
|----|--------|-------|
| F1–F11 | **PASS** | unit + backend + code review |
| F12 API | **PASS** | 5 API tests |
| F12 UI stub | **PARTIAL** | helper exists, not wired to public pages |
| E2E 24h / ACTIVE / create | **BLOCKED** | global-setup |
| E2E status panels | **NOT RUN** | spec missing |
| Contracts sync | **OPEN** | deadline semantics |

---

## Fixes applied in this verification pass

1. `test_lb_public_published_round_allowed` — calculate + publish round 1 (loaded DB has CLOSED, not PUBLISHED).
2. `admin.ts` — removed unused `ruleHours`; placement validation via `isDeadlineValid`.
3. E2E: `supervisor_24h_rule.spec.ts` — lockout semantics; `supervisor_active_round.spec.ts` — pre-deadline edit; copy «Тур активен».

---

## Рекомендации

1. **E2E:** починить `playwright.global-setup.ts` / `provisionRegularUser` (подтверждение участника) или использовать `dev_setup --e2e`.
2. **Manual:** `dev_setup --ensure-running-only` + проверить rounds 9/10/11 на `/admin/rounds`.
3. **Coder follow-up:** подключить `isRoundPubliclyVisible` на публичных страницах LB; sync contracts.

---

## Verdict

| Layer | Verdict |
|-------|---------|
| Coder 2.3.1 | **COMPLETE** (minor F12 UI + contracts open) |
| Tester automated | **TEST_PASS** |
| Tester E2E | **BLOCKED** (infra) |
