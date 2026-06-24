# Отчёт тестирования — Stage 2.1.1

**Дата:** 2026-06-24  
**Вердикт:** `TEST_PASS`  
**Инструкции:** `agent_docs/instructions/tester_2.1.1.md`

## Краткое резюме

Этап 2.1.1 (маршрутизация по ролям, admin stubs, demo user `user/user`) прошёл автоматические проверки. Субагент @Tester упал с `WritableIterable is closed` после создания E2E-спек; пайплайн завершён вручную с доработками E2E-фикстур и двумя минимальными исправлениями реализации (гонка редиректа на `/`, `is_temp_password` у bootstrap admin).

## Результаты

| ID | Result | Notes |
|----|--------|-------|
| `[ENV-DEMO-USER]` | PASS | `POST /auth/login` `user/user` → `access_token` |
| `[UNIT-RESOLVE-TEMP]` | PASS | Vitest `resolvePostLoginPath.test.ts` |
| `[UNIT-RESOLVE-USER]` | PASS | USER → `/profile` |
| `[UNIT-RESOLVE-SUPERVISOR]` | PASS | SUPERVISOR → `/admin/settings/parameters` |
| `[UNIT-RESOLVE-ADMIN]` | PASS | ADMIN → `/admin` |
| `[E2E-USER-LOGIN-PROFILE]` | PASS | Demo user → `/profile`, без `/admin` |
| `[E2E-SUPERVISOR-LOGIN-ADMIN]` | PASS | Supervisor → `/admin/*` |
| `[E2E-ADMIN-LOGIN-ADMIN]` | PASS | Admin → stub dashboard |
| `[E2E-HOME-USER]` | PASS | USER на `/` → participant flow |
| `[E2E-HOME-STAFF]` | PASS | SUPERVISOR на `/` → `/admin` |
| `[E2E-SUPERVISOR-NO-PROFILE]` | PASS | `/profile` → redirect `/admin` |
| `[E2E-USER-PROFILE-OK]` | PASS | Demo user видит «Личный кабинет» |
| `[E2E-STAFF-LOGIN-PAGE]` | PASS | `/staff/login` → `/admin/*` |
| `[LINT-ESLINT]` | PASS | exit 0 |
| `[LINT-TSC]` | PASS | exit 0 |
| `[LINT-PRETTIER]` | PASS | exit 0 |
| `[BUILD]` | PASS | exit 0 |
| `[DOC-UI-PAGES]` | PASS | `/admin` stubs, USER-only `/profile`, `/staff/login` |
| `[DOC-INTEGRATION]` | PASS | §2.4 Post-login routing |
| `[DOC-DEV-SETUP]` | PASS | `user/user` из bootstrap |
| `[DOC-TODO]` | PASS | demo user removal + CONTEST_LOCKED |
| `[DOC-CODER-HANDOFF]` | PASS | Coder 2.1.1 `READY_FOR_TEST` |
| Manual checklist | REMINDER | См. §8 инструкций |

## Команды

| Команда | Результат |
|---------|-----------|
| `npm run test:unit` | 22 passed |
| `npm run lint` | 0 errors |
| `npm run type-check` | 0 errors |
| `npm run format:check` | 0 errors |
| `CI=1 npm run test:e2e` | 18 passed (0 skipped) |
| `npm run build` | exit 0 |

## Созданные/изменённые тесты

- `frontend/e2e/auth_role_routing.spec.ts` — NEW
- `frontend/e2e/auth_profile_user_only.spec.ts` — NEW
- `frontend/e2e/staff_login.spec.ts` — NEW
- `frontend/e2e/fixtures/auth.ts` — role-aware helpers (`loginAsDemoUser`, `loginAsAdmin`, `waitForStaffAuthenticatedHeader`)
- `frontend/e2e/fixtures/credentials.ts` — `DEMO_USER_*`, `ADMIN_*`
- `frontend/e2e/supervisor_contest_picker.spec.ts` — scope picker to `header` (дубль с `AdminTopNav`)

## Доработки при follow-up (после сбоя субагента)

| Файл | Причина |
|------|---------|
| `frontend/src/lib/auth/postLoginNavigation.ts` | Гонка: home `/` перебивал post-login `/profile` |
| `frontend/src/providers/AuthProvider.tsx` | `sessionStorage` skip + `router.replace` |
| `frontend/src/app/page.tsx` | Уважать skip-home-redirect |
| `src/scripts/bootstrap_users.py` | Admin `is_temp_password=False` для dev/E2E |

## Ручная проверка (для разработчика)

> Перед релизом 2.1.1 вручную проверить:
> - [ ] AppShell: USER — «Личный кабинет»; staff — «Управление»
> - [ ] AdminTopNav stub: вкладки disabled / «Скоро 2.3»
> - [ ] Footer «Вход для организаторов»
> - [ ] Temp password → редирект по роли после смены пароля

## Следующий шаг

Разблокированы **2.3** (admin UI) и **2.2** (predictions) по графу `2.1 → 2.1.1 → 2.3 → 2.2 → 2.4`. Invite E2E в 2.3 — только DRAFT contest (`CONTEST_LOCKED` на contest `1`).
