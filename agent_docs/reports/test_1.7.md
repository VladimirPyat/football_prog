# Отчёт тестирования — Stage 1.7: Leaderboard Counts & Invite Accept

**Дата:** 2026-06-22  
**Вердикт:** **TEST_PASS**

## Краткое резюме

Проверены блокеры B4 (поля `count_*` в leaderboard) и B6 (accept invite + prediction guard). Контракт и документация обновлены. Полный регрессионный прогон зелёный.

## Результаты

| ID | Result | Notes |
|----|--------|-------|
| `[LB-COUNTS-ROUND]` | PASS | `test_lb_counts_round`: 4 ключа, `int >= 0`, cross-check с `scores` через `sf` |
| `[LB-COUNTS-GLOBAL]` | PASS | `test_lb_counts_global`: агрегаты совпадают с `leaderboard.csv` (larin) |
| `[LB-COUNTS-REG]` | PASS | `test_calculate_leaderboard_1_4.py` → 8 passed, 1 skipped; rank/ETag без регрессии |
| `[ACCEPT-INVITE]` | PASS | `change-password` → `participants.status == ACCEPTED` |
| `[ACCEPT-PRED-GUARD]` | PASS | PENDING invitee → `POST .../predictions` → 403, `PARTICIPANT_NOT_ACCEPTED` |
| `[ACCEPT-REG]` | PASS | `test_setup_part_auth` → 1 passed; `test_accept_reg_predictions` → 200 |
| `[ACCEPT-ME-CONTESTS]` | PASS | optional (1.8 merged): `test_accept_me_contests` → `participant_status=ACCEPTED` |
| `[DOC-CONTRACT]` | PASS | `api_v1.yaml` `ScoreDetail`: `count_exact_high/exact/diff/outcome` |
| `[DOC-API-GUIDE]` | PASS | Temp-password flow, prediction guard, count fields documented |
| Regression | PASS | 302 passed, 2 skipped |

## Выполненные команды

```bash
uv run pytest tests/api/test_leaderboard_counts.py tests/api/test_participant_accept.py -v
# → 7 passed

uv run pytest tests/api/test_calculate_leaderboard_1_4.py -q
# → 8 passed, 1 skipped

uv run pytest tests/api/test_operational_gaps_1_4.py::test_setup_part_auth -q
# → 1 passed

uv run pytest tests/ --ignore=tests/manual -q
# → 302 passed, 2 skipped
```

## Созданные/изменённые тесты

| Файл | Назначение |
|------|------------|
| `tests/api/test_leaderboard_counts.py` | [LB-COUNTS-ROUND/GLOBAL/ZERO] — без изменений |
| `tests/api/test_participant_accept.py` | [ACCEPT-*] + новый `test_accept_me_contests` |

## Блокеры

- **B4** — закрыт: `count_*` в round/global leaderboard.
- **B6** — закрыт: accept на `change-password`, guard до accept.

## Следующий шаг

Stage 1.7 sign-off. Frontend 2.4 может использовать `count_*` колонки.
