# Отчёт тестирования — Stage 2.1 (Foundation, Auth & Profile Shell)

**Дата:** 2026-06-24  
**Исполнитель:** Tester  
**Вердикт:** `TEST_PASS` (с замечаниями по окружению — см. §Дефекты окружения)

---

## Резюме

Фронтенд Stage 2.1 прошёл полный цикл автоматической верификации: 18 unit-тестов (Vitest), 10 E2E smoke (Playwright), lint/type-check/prettier/build — все с exit code 0. UI auth, discovery, profile/contacts, RBAC guards, temp-password gate и supervisor contest picker работают против live API на `:8000`.

**Важно:** документированный логин `user/user` из `manuals/DEV_SETUP.md` **не работает** на стандартном `dev_setup.py` (см. дефект `[ENV-LOADER-AUTH]`). E2E используют provisioning через API (global setup) — это не ослабление assertions, а обход бага данных.

---

## Таблица результатов

| ID | Result | Notes |
|----|--------|-------|
| `[UNIT-LOGIN-SCHEMA]` | PASS | 3 tests in `login.test.ts` |
| `[UNIT-CONTACTS-SCHEMA]` | PASS | 3 tests in `contacts.test.ts` |
| `[UNIT-CHANGE-PW]` | PASS | 3 tests in `changePassword.test.ts` (добавлен Tester) |
| `[UNIT-DEFAULT-CONTEST]` | PASS | 4 tests in `resolveDefaultContestId.test.ts` |
| `[UNIT-API-ERROR]` | PASS | `parseErrorDetail` + `AppError` in `client.test.ts` |
| `[UNIT-401-EVENT]` | PASS | `fp:unauthorized` dispatch in `client.test.ts` |
| `[E2E-LOGIN-PROFILE]` | PASS | provisioning user via global setup |
| `[E2E-LOGOUT]` | PASS | header «Выйти» |
| `[E2E-401-LOGOUT]` | PASS | invalid JWT → visitor state |
| `[E2E-TEMP-PASSWORD]` | PASS | invite на новый DRAFT contest (не id=1 locked) |
| `[E2E-VISITOR-DISCOVERY]` | PASS | public list + navigate `/contest/{id}` |
| `[E2E-USER-CONTESTS]` | PASS | `/contests` enrolled list |
| `[E2E-SUPERVISOR-PICKER]` | PASS | `ContestPicker` + `fp_active_contest_id` |
| `[E2E-PROFILE-CONTACTS]` | PASS | PATCH vk_id + reload persistence |
| `[E2E-RBAC-GUARDS]` | PASS | visitor blocked; user allowed |
| `[E2E-CORS-SMOKE]` | PASS | no CORS console errors during login |
| `[LINT-ESLINT]` | PASS | exit 0, warnings: 0 |
| `[LINT-TSC]` | PASS | exit 0 |
| `[LINT-PRETTIER]` | PASS | exit 0 |
| `[BUILD]` | PASS | exit 0, 8 routes |
| `[DOC-UI-COMPONENTS]` | PASS | `agent_docs/ui/components.md` — 2.1 ✅ |
| `[DOC-UI-PAGES]` | PASS | `agent_docs/ui/pages.md` — `/`, `/contests`, `/profile`, `/change-password` ✅ |
| `[DOC-INTEGRATION]` | PASS | `frontend_api_integration.md` update log 2026-06-23 |
| `[DOC-CODER-HANDOFF]` | PASS | `stage_2.md` READY_FOR_TEST |
| Manual checklist | REMINDER | §8 ниже |

---

## Выполненные команды

| Команда | Exit code |
|---------|-----------|
| `uv run python src/scripts/dev_setup.py` | 0 |
| `uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000` | 0 (background) |
| `cd frontend && npm run test:unit` | 0 (18 passed) |
| `cd frontend && npm run lint` | 0 |
| `cd frontend && npm run type-check` | 0 |
| `cd frontend && npm run format:check` | 0 |
| `cd frontend && npm run build` | 0 |
| `cd frontend && npm run test:e2e` | 0 (10 passed) |

---

## Созданные / изменённые тестовые артефакты

| Файл | Назначение |
|------|------------|
| `frontend/playwright.config.ts` | Playwright + webServer |
| `frontend/playwright.global-setup.ts` | Provisioning E2E USER через API |
| `frontend/e2e/fixtures/{auth,credentials}.ts` | Shared helpers |
| `frontend/e2e/*.spec.ts` | 9 E2E smoke specs |
| `frontend/src/lib/validation/changePassword.test.ts` | `[UNIT-CHANGE-PW]` |
| `frontend/vitest.config.ts` | exclude `e2e/**` from Vitest |
| `frontend/package.json` | `@playwright/test` devDependency |

---

## Дефекты окружения (для @Coder, не блокируют frontend sign-off)

### `[ENV-LOADER-AUTH]` — loader users cannot login

- **Expected:** после `dev_setup.py --full` логин `shutov`/`user` с паролем `user` (per `manuals/DEV_SETUP.md`) → 200 + JWT.
- **Actual:** `POST /api/v1/auth/login` с `user/user` → `{"detail":"Неверный логин или пароль"}`; `shutov/user` → `500 INTERNAL_ERROR` (bcrypt verify on placeholder hash `test-data-placeholder-hash-not-for-auth`).
- **Root cause:** `src/scripts/load_test_data.py` sets `_PLACEHOLDER_PASSWORD_HASH` for all CSV users; login `user` отсутствует в `docs/test_data/contracted/users.csv`.
- **Action:** в `load_test_data.py` или `dev_setup.py` — хешировать пароль `user` для loader users; исправить `manuals/DEV_SETUP.md` (логин `shutov`, не `user`).

### `[ENV-LOCKED-INVITE]` — invite on contest id=1 fails

- **Expected:** supervisor может пригласить участника на RUNNING contest (или docs уточняют ограничение).
- **Actual:** `POST /contests/1/participants` → 403 `CONTEST_LOCKED` (contest `is_locked=true` после dev_setup).
- **Action:** документировать или ослабить для dev; E2E temp-password создаёт новый DRAFT contest.

---

## §8 — Manual checklist (для разработчика)

> Разработчик должен вручную проверить перед релизом 2.1:
> - [ ] Визуальное соответствие header/footer скринам `user_*.jpg` (brand, кнопки, footer)
> - [ ] Навигация: все ссылки профиля кликабельны или помечены как stub
> - [ ] Ошибки форм login/contacts отображаются под полями / toast
> - [ ] Состояния кнопок (disabled Save при readonly contacts)
> - [ ] Мобильная ширина ~375px — header не ломается, списки читаемы

---

## Следующий шаг

Stage 2.1 frontend готов для **2.2** (predictions). Рекомендуется параллельно исправить `[ENV-LOADER-AUTH]` в `dev_setup`/`load_test_data` для out-of-box E2E без global provisioning.
