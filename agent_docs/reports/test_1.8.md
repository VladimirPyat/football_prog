# Отчёт тестирования — Stage 1.8: Contest Discovery & User Contacts

**Дата:** 2026-06-22  
**Вердикт:** **TEST_PASS**

## Краткое резюме

Проверены блокеры B1–B3 (discovery + contacts), контракт `api_v1.yaml` v1.2.0-rc, документация и полный регрессионный прогон. Все обязательные тесты зелёные.

## Результаты

| ID | Result | Notes |
|----|--------|-------|
| `[ME-CONTESTS-USER]` | PASS | invitee → 1 contest, `participant_status=PENDING`, `role=USER`, `status=DRAFT` |
| `[ME-CONTESTS-EMPTY]` | PASS | `temp_user` без enroll → `[]` |
| `[ME-CONTESTS-RBAC]` | PASS | без Bearer → 401 |
| `[PUBLIC-LIST]` | PASS | только RUNNING в public list (DRAFT/PAUSED/FINISHED исключены) |
| `[PUBLIC-NO-AUTH]` | PASS | без Bearer → 200 |
| `[CONTACTS-GET-DEFAULT]` | PASS | null defaults при отсутствии row |
| `[CONTACTS-PATCH]` | PASS | partial PATCH + email upsert |
| `[CONTACTS-INVITE]` | PASS | email из invite в contacts |
| `[CONTACTS-TEMP-PW]` | PASS | GET/PATCH при `is_temp_password=true` → 200 |
| `[DOC-CONTRACT]` | PASS | `api_v1.yaml` v1.2.0-rc; paths `/me/contests`, `/contests/public`, `/auth/me/contacts` |
| `[DOC-API-GUIDE]` | PASS | секции B1–B3 + note temp-password для contacts |
| `[DOC-BLOCKED]` | PASS | B1–B3 в BLOCKED.md (ожидаемо до bundle 1.7–1.9) |
| Regression | PASS | 286 passed, 2 skipped |
| Smoke (1.4 + 1.6) | PASS | 10 passed |

## Выполненные команды

```bash
uv run pytest tests/api/test_me_contests.py tests/api/test_contests_public.py tests/api/test_contacts.py -v
uv run pytest tests/api/test_setup_phase_1_4.py tests/api/test_admin_users.py -q
uv run pytest tests/ --ignore=tests/manual -q
```

## Для frontend (Stage 2.1)

- B1/B2/B3 готовы к интеграции.
- Public list = **только RUNNING** (PAUSED/FINISHED не включаются).
- `/me/contests` отдаёт глобальный `role`, не per-contest role.

## Не в scope

- B4 (leaderboard counts), B6 (invite accept), B5 (logo upload)
- Playwright / E2E frontend
- Обновление BLOCKED.md → RESOLVED (ждём 1.7–1.9 или запрос)
