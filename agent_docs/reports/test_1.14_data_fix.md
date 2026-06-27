# Отчёт тестирования — Stage 1.14: Dev Fixture Data Fix

**Дата:** 2026-06-27  
**Вердикт:** `TEST_PASS`  
**Coder spec:** `agent_docs/instructions/coder_1.14_data_fix.md`

## Краткое резюме

Реализованы `src/scripts/finalize_dev_fixture.py` и расширен `dev_setup.py` (флаги `--e2e`, `--finalize-fixture-only`). После `load_test_data --reset` + `bootstrap_users` + `dev_setup --ensure-running-only` конкурс `id=1` содержит туры 1–9 `PUBLISHED` (90 очков ≡ CSV), тур 10 `CALCULATED` (10 очков), тур 11 `CLOSED` (0 очков). Регресс pytest и изолированные тесты скрипта — зелёные. E2E-профиль (`--e2e`) восстанавливает тур 10 `ACTIVE` без finalize.

**Замечание при реализации:** `bootstrap_users` добавляет `admin`/`user` в участники; finalize переводит их в `PENDING`, чтобы в `scores` оставалось ровно 10 строк на тур (контрактные пользователи).

## Таблица результатов

| ID | Result | Notes |
|----|--------|-------|
| `[FIXTURE-1-9-PUBLISHED]` | PASS | SQL + pytest: status=PUBLISHED, 10 scores each |
| `[FIXTURE-10-CALCULATED]` | PASS | status=CALCULATED, 10 scores, deadline 2026-06-26T12:00Z |
| `[FIXTURE-11-CLOSED]` | PASS | 8 SCHEDULED matches, 0 scores |
| `[FIXTURE-11-DEADLINE]` | PASS | deadline 2026-06-27T08:00Z < now; kickoffs afternoon 27.06 |
| `[FIXTURE-10-NOT-PUBLISHED]` | PASS | Round 10 ≠ PUBLISHED |
| `[FIXTURE-TOTAL-SCORES]` | PASS | count=100 |
| `[FIXTURE-SCORES-1-9]` | PASS | 90/90 vs expected_scores.csv |
| `[FIXTURE-SCORES-10]` | PASS | 10 rows, totals non-null |
| `[REGRESS-CALC-PERSIST]` | PASS | 5 passed |
| `[REGRESS-CALC-LB]` | PASS | 8 passed, 1 skipped |
| `[REGRESS-SCORING-CONTRACT]` | PASS | 18 passed |
| `[SCRIPT-FINALIZE-IDEMPOTENT]` | PASS | Double finalize → still 100 rows |
| `[SCRIPT-FINALIZE-PROFILE-MANUAL]` | PASS | tests/scripts/test_finalize_dev_fixture_1_14.py |
| `[SCRIPT-FINALIZE-PROFILE-E2E]` | PASS | Round 10 ACTIVE, 0 scores, no round 11 |
| `[API-ROUNDS-LIST]` | PASS | 11 rounds, statuses match fixture |
| `[API-GLOBAL-LB]` | PASS | 200, leaderboard length=10 |
| `[API-ROUND-10-SUPERVISOR]` | PASS | 200 with supervisor JWT (preview) |
| `[API-ROUND-11-CLOSED]` | PASS | Public round LB → 403 |
| `[E2E-PROFILE-ACTIVE-R10]` | PASS | Verified via pytest E2E profile fixture |
| `[E2E-TEARDOWN]` | SKIP | Playwright E2E subset not run (profile covered by pytest) |
| `[DOC-DEV-SETUP]` | PASS | Table 1–9/10/11 documented |
| `[DOC-STATUS-REF]` | PASS | §2.3 dev fixture table added |
| `[DOC-MANUAL-SCORING]` | PASS | Note: 100 score rows after dev finalize |

## Команды

```bash
uv run pytest tests/integration/test_calculate_persistence_1_2.py \
  tests/api/test_calculate_leaderboard_1_4.py \
  tests/scoring/test_contracted_scores.py -v
# → 31 passed, 1 skipped

uv run pytest tests/scripts/test_finalize_dev_fixture_1_14.py -v
# → 5 passed

uv run python src/scripts/dev_setup.py --ensure-running-only
# manual profile on shared dev DB
```

## Следующий шаг

Manual QA на `/admin/rounds`, `/admin/results`, публичный leaderboard → `tester_2.3.1_fix_rounds.md` (после `coder_2.3.1` READY_FOR_TEST).
