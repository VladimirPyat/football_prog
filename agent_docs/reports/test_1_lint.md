# Отчёт тестирования — Stage 1.lint: Backend Linting Baseline

**Дата:** 2026-06-23  
**Вердикт:** **TEST_PASS**

## Краткое резюме

Baseline-аудит ruff/mypy/bandit в режиме non-blocking. Dev-зависимости и конфигурация установлены; `tests/test_linting.py` выполняет три линтера через pytest с предупреждениями без падения. Полный регрессионный прогон: **305 passed, 2 skipped** (+3 lint-теста к предыдущим 302). Нарушения линтеров зафиксированы для будущего `coder_1_lint_fix.md`.

## Режим non-blocking

Pytest-тесты `[LINT-RUFF]`, `[LINT-MYPY]`, `[LINT-BANDIT]` вызывают линтеры через `subprocess` + `uv run`. При `exit != 0` эмитируется `warnings.warn()`, тест **всегда проходит**. Строгий режим (fail on violations) — после `coder_1_lint_fix.md`.

## Результаты

| ID | Result | Notes |
|----|--------|-------|
| `[LINT-RUFF]` | PASS | exit=1, findings=75 |
| `[LINT-MYPY]` | PASS | exit=2, errors=1 (config blocker, scan incomplete) |
| `[LINT-BANDIT]` | PASS | exit=1, medium+=1 |
| `[LINT-REG-FULL]` | PASS | 305 passed, 2 skipped |
| `[LINT-REG-LINT-ONLY]` | PASS | 3 passed, 3 warnings |

## Сводка находок

| Tool | Exit | Total | CRITICAL | TOLERABLE |
|------|------|-------|----------|-----------|
| ruff | 1 | 75 | 0 | 75 |
| mypy | 2 | 1 | 0 | 1 |
| bandit | 1 | 1 (medium+) | 1 | 0 |

## CRITICAL (требует coder_1_lint_fix.md)

| File:line | Rule | Описание | Fix scope |
|-----------|------|----------|-----------|
| `src/scripts/load_test_data.py:92` | B608 (bandit) | `text(f"DELETE FROM {table}")` — Medium severity, Low confidence. Имена таблиц из жёстко заданного кортежа (не user input), но bandit `-ll` срабатывает. | Добавить `# nosec B608` с комментарием или переписать на `delete()` ORM/SQLAlchemy Core без f-string; документировать в coder_1_lint_fix |

## TOLERABLE (отложить на cleanup)

### ruff (75 findings, exit=1)

| Code | Count | Категория |
|------|-------|-----------|
| UP017 | 28 | `datetime.UTC` alias — pyupgrade style |
| I001 | 23 | Import sort/format (isort) |
| E402 | 20 | Module import not at top of file |
| F401 | 2 | Unused imports |
| B008 | 1 | `File(...)` default в `contest_teams.py:56` — идиоматичный FastAPI upload; не баг, suppress или per-file ignore |
| UP036 | 1 | Deprecated typing annotation |

53 из 75 автоисправимы через `ruff check --fix`.

### mypy (1 error, exit=2 — scan blocked)

- `src/scoring/engine.py` — duplicate module path: `"scoring.engine"` vs `"src.scoring.engine"`. Конфликт `mypy_path = ["src", "."]` + `files = ["src"]`. Полный type-check не выполнен; требуется настройка package bases в coder pass (без изменения логики `src/`).

### bandit

- Low severity (3 шт.) — не попадают в `-ll` отчёт; игнорируются на baseline.

## Выполненные команды

```bash
uv add --dev ruff mypy bandit
# → ruff 0.15.18, mypy 2.1.0, bandit 1.9.4 pinned in pyproject.toml

uv run pytest tests/test_linting.py -v
# → 3 passed, 3 warnings in 1.25s

uv run pytest tests/ --ignore=tests/manual -v
# → 305 passed, 2 skipped, 3 warnings in 372.22s

uv run ruff check src/
# → Found 75 errors, exit: 1

uv run mypy src/
# → 1 error (duplicate module), exit: 2

uv run bandit -r src/ -ll
# → 1 Medium (B608), exit: 1
```

## Изменённые файлы

| Файл | Назначение |
|------|------------|
| `pyproject.toml` | dev deps (ruff, mypy, bandit) + `[tool.ruff]`, `[tool.mypy]`, marker `lint_audit` |
| `tests/test_linting.py` | non-blocking lint smoke: `[LINT-RUFF]`, `[LINT-MYPY]`, `[LINT-BANDIT]` |

## Следующий шаг

Planner/Coder: создать `coder_1_lint_fix.md` — устранить **1 CRITICAL** (bandit B608), настроить mypy package resolution, bulk-fix ruff TOLERABLE (I001/UP017/E402). После исправлений — повторный аудит и переход к strict mode.
