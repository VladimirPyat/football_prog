# Отчёт тестирования — Этап 1.1: Scoring Engine Cross-check

**Дата:** 2026-06-11  
**Вердикт:** ✅ PASS  
**Команда запуска:** `uv run pytest tests/scoring/ -v`  
**Результат:** 18 passed, 0 failed, 0 errors (0.09s)

---

## Результаты по группам

### [SC-COUNTS] Safety Gate
- Все 90 строк `expected_scores.csv` удовлетворяют условию `16·count_exact_high + 12·count_exact + 8·count_diff + 4·count_outcome == expected_base_pts`.
- Ворота не заблокировали выполнение → проверки счётчиков активированы.

### Per-round (expected_scores.csv — 90 строк, раунды 1–9)

| TEST-ID | Описание | Результат |
|---------|----------|-----------|
| [SC-BASE] | engine.base_points == expected_base_pts | **90/90 PASS** |
| [SC-B1B2] | engine.bonus1+bonus2 == expected_bonus1, expected_bonus2==0 | **90/90 PASS** |
| [SC-B3] | engine.bonus3 == expected_bonus3 | **90/90 PASS** |
| [SC-TOTAL] | engine.total_with_bonus3 == expected_total | **90/90 PASS** |
| [SC-RANK] | engine.round_rank == expected_rank (dense) | **90/90 PASS** |
| [SC-COUNTS] | count_exact_high/exact/diff/outcome | **90/90 PASS** |

**Дополнительно:** serov в раунде 4 — отсутствие предсказаний подтверждено: base=0, все бонусы=0, per_match пустой, ранг корректен. ✅

### Global leaderboard (leaderboard.csv — 10 пользователей)

| TEST-ID | Описание | Результат |
|---------|----------|-----------|
| [LB-COUNT] | Σ count_exact_high/exact/diff/outcome | **10/10 PASS** |
| [LB-TOTALS] | Σ base, bonuses, total_points, total_predictions | **10/10 PASS** |
| [LB-RANK] | Порядок и ранги build_standings() | **10/10 PASS** |

Проверены тай-брейки:
- shutov (320 pts, exact_scores=7) → rank 4, выше kurakov (320 pts, exact_scores=5) → rank 5 ✅
- volchenko (232 pts, exact_scores=5) → rank 9, выше serov (232 pts, exact_scores=4) → rank 10 ✅
- serov: total_predictions=64 (нет раунда 4) ✅
- остальные 9 пользователей: total_predictions=72 ✅

### Edge / boundary cases

| TEST-ID | Описание | Результат |
|---------|----------|-----------|
| [EDGE-NULL] | Отсутствующее предсказание → 0 очков (даже при результате 0:0) | **PASS** |
| [EDGE-ZERO] | 0:0 vs 0:0 → EXACT (12 pts), не EXACT_HIGH | **PASS** |
| [EDGE-TIE] | 3 игрока с равным итогом → одинаковый dense rank; tiebreak по exact_scores_count | **PASS** |
| [EDGE-VOID] | is_scorable=False → 0 очков всем, матч не в per_match | **PASS** |

---

## Файлы тестов

- `tests/scoring/__init__.py`
- `tests/scoring/conftest.py` — загрузка CSV, запуск движка для раундов 1–9, standings
- `tests/scoring/test_contracted_scores.py` — 18 тестов, все группы assertions

---

## Итог

Движок `src/scoring/` воспроизводит контрактные данные **с нулевым расхождением** по всем 90 строкам per-round и 10 строкам leaderboard. Граничные случаи также покрыты и подтверждены.
