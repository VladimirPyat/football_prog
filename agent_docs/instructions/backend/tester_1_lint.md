# Tester Instructions — Stage 1.lint: Backend Linting Baseline Audit

> **Status gate:** No Coder handoff required. **Prerequisite:** Backend Stage 1.9 at `TEST_PASS` (full regression ~302 passed).
> **Policy source:** `.cursorrules` → LINTING STANDARDS (Python).
> **Mode:** **Non-blocking baseline** — linters RUN with pytest but must NOT fail the suite yet. Findings are triaged in the report for a future `coder_1_lint_fix.md` pass.

---

## 1. Objective

Introduce backend linting toolchain and capture a **baseline audit** without blocking CI or regression:

1. Add dev dependencies: `ruff`, `mypy`, `bandit` (pinned in `pyproject.toml`).
2. Add minimal linter config to `pyproject.toml` (sensible defaults for FastAPI / SQLAlchemy / Pydantic v2).
3. Create `tests/test_linting.py` that invokes all three linters during pytest and **reports findings without failing**.
4. Run full regression to confirm existing tests still pass.
5. Run each linter standalone; capture raw output for the report.
6. Produce Russian triage report `agent_docs/reports/test_1_lint.md`.

**Non-goals:**

- Fixing issues in `src/` (Coder task later).
- Enforcing zero violations in this sub-stage.
- Frontend linting (see `agent_docs/instructions/tester_2.1.md`).

---

## 2. Scope — files you may create/modify

```
pyproject.toml                          # dev deps + [tool.ruff], [tool.mypy], pytest marker
tests/test_linting.py                   # NEW — non-blocking lint smoke tests
agent_docs/reports/test_1_lint.md       # NEW — Russian baseline report
agent_docs/progress/stage_1.md          # append TEST_PASS / TEST_FAIL entry only
```

**Do NOT modify:** `src/`, `docs/`, application tests under `tests/api/` etc.

Read-only inspection of `src/` for triage (grep, line references) is allowed.

---

## 3. Dependencies

From repo root:

```bash
uv add --dev ruff mypy bandit
```

Verify `pyproject.toml`:

- Packages appear under `[dependency-groups] dev = [...]` with **pinned** lower bounds (uv default, e.g. `ruff>=0.x.y`).
- Do not use `pip install`.

---

## 4. `pyproject.toml` — minimal linter config

Append/update sections below. Adjust only if a tool refuses to start; document deviations in the report.

### 4.1 Pytest marker (required)

Under `[tool.pytest.ini_options]` add:

```toml
markers = [
    "lint_audit: non-blocking backend linter baseline (ruff, mypy, bandit)",
]
```

### 4.2 Ruff

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
]
ignore = [
    "E501",  # line length — defer to formatter / cleanup pass
]
```

Scope for commands and tests: **`src/` only** (matches `.cursorrules`).

### 4.3 Mypy

```toml
[tool.mypy]
python_version = "3.12"
plugins = ["pydantic.mypy"]
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
check_untyped_defs = true
ignore_missing_imports = true
namespace_packages = true
explicit_package_bases = true
mypy_path = ["src", "."]
files = ["src"]
```

**Note:** SQLAlchemy 2.0 typing may produce noise on first pass — classify as TOLERABLE unless it hides a real bug. Do **not** add `sqlalchemy` mypy plugin unless mypy fails to start; if added, document in report.

### 4.4 Bandit

Bandit is configured via CLI flags (no required `[tool.bandit]` block). Standard invocation:

```bash
uv run bandit -r src/ -ll
```

`-ll` = report **medium** severity and above (per `.cursorrules`).

---

## 5. `tests/test_linting.py` — implementation spec

### 5.1 Non-blocking pattern (mandatory)

**Chosen approach:** `@pytest.mark.lint_audit` + subprocess invocation + **`warnings.warn()`** on violations + **no failing assertions**.

Rationale:

| Approach | Why / why not |
|----------|----------------|
| `pytest.fail()` on violations | ❌ Blocks suite — forbidden in this sub-stage |
| `@pytest.mark.xfail(strict=False)` | ❌ Shows as XFAIL in summary; confusing for baseline |
| `@pytest.mark.skip` on failure | ❌ Hides that linter ran |
| **warn + always pass** | ✅ Visible in pytest output (`-rw` or default warnings summary); suite stays green |

Each test MUST:

1. Run the linter via `subprocess.run(..., capture_output=True, text=True, check=False)`.
2. Use repo root as `cwd` (resolve with `Path(__file__).resolve().parents[1]`).
3. Invoke through `uv run` for consistency:
   - `["uv", "run", "ruff", "check", "src/"]`
   - `["uv", "run", "mypy", "src/"]`
   - `["uv", "run", "bandit", "-r", "src/", "-ll"]`
4. If `returncode != 0`, emit `warnings.warn(summary, UserWarning, stacklevel=2)` where `summary` includes exit code and **first ~2000 chars** of combined stdout+stderr (truncate with `...`).
5. Attach structured metadata via `request.node.user_properties.append(("lint_ruff", {...}))` (or mypy/bandit keys) with at least: `tool`, `exit_code`, `finding_count` (best-effort parse), `raw_tail`.
6. End without `assert result.returncode == 0` — test passes regardless.

Optional helper (recommended):

```python
def _run_linter(request, tool: str, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    ...
```

### 5.2 Test functions & IDs

| Test function | ID | Linter |
|---------------|-----|--------|
| `test_lint_ruff_check` | `[LINT-RUFF]` | ruff check |
| `test_lint_mypy` | `[LINT-MYPY]` | mypy |
| `test_lint_bandit` | `[LINT-BANDIT]` | bandit -ll |

All three decorated with `@pytest.mark.lint_audit`.

### 5.3 Docstring requirement

Module docstring must state explicitly:

> These tests are **informational baseline audits**. They do not fail pytest when linters report issues. A future stage will switch to strict mode after `coder_1_lint_fix.md`.

### 5.4 Parsing hints (for counts in report)

- **Ruff:** count lines matching `^src/` in stdout (typical format `src/path.py:line:col: CODE message`).
- **Mypy:** count lines containing `: error:`.
- **Bandit:** count `>> Issue:` blocks or lines with `Severity: Medium` / `High` (medium+ only with `-ll`).

Exact counts are best-effort; raw output in report is authoritative.

---

## 6. Standalone linter runs (for report appendix)

Run and save output (copy into report or `agent_docs/reports/` snippets):

```bash
uv run ruff check src/ 2>&1 | tee /tmp/ruff_baseline.txt; echo "exit: $?"
uv run mypy src/ 2>&1 | tee /tmp/mypy_baseline.txt; echo "exit: $?"
uv run bandit -r src/ -ll 2>&1 | tee /tmp/bandit_baseline.txt; echo "exit: $?"
```

Record exit codes even when non-zero.

---

## 7. Regression

| ID | Check |
|----|-------|
| `[LINT-REG-FULL]` | Full suite green: `uv run pytest tests/ --ignore=tests/manual -v` |
| `[LINT-REG-LINT-ONLY]` | Lint tests execute: `uv run pytest tests/test_linting.py -v` (3 passed, 0 failed; warnings expected if findings exist) |

**Verdict rule for this sub-stage:** `TEST_PASS` if infra is installed, config present, `test_linting.py` runs, and **full regression passes**. Lint violations do **not** cause `TEST_FAIL`.

---

## 8. Triage categories (report body)

Classify every finding (or aggregate when >50 identical class):

### CRITICAL

- Bandit **Medium** or **High** (any `-ll` hit).
- Ruff **B** codes that imply likely bugs (e.g. `B008` callable default in FastAPI deps — evaluate case-by-case).
- Mypy errors on security-sensitive modules (`src/core/security.py`, `src/api/deps.py`, auth flows) if clearly unsafe.

For each CRITICAL item:

```
file:line — rule/id — one-line description — proposed fix scope
→ defer to agent_docs/instructions/coder_1_lint_fix.md (not yet created)
```

### TOLERABLE

- Style/import ordering (ruff E/W/I).
- Minor mypy `note` / missing annotation on internal helpers.
- `ignore_missing_imports` noise on third-party stubs.

Document **counts by rule/code**; no per-line listing required if >20 items.

---

## 9. Report (`agent_docs/reports/test_1_lint.md`)

Russian language. Follow structure of `agent_docs/reports/test_1.9.md`.

### Template

```markdown
# Отчёт тестирования — Stage 1.lint: Backend Linting Baseline

**Дата:** YYYY-MM-DD
**Вердикт:** **TEST_PASS** / **TEST_FAIL**

## Краткое резюме

Baseline-аудит ruff/mypy/bandit; режим non-blocking. Инфраструктура установлена; регрессия …

## Режим non-blocking

Кратко: pytest-тесты предупреждают (warnings), но не падают. Строгий режим — после coder_1_lint_fix.

## Результаты

| ID | Result | Notes |
|----|--------|-------|
| `[LINT-RUFF]` | PASS | exit=N, findings=M |
| `[LINT-MYPY]` | PASS | exit=N, errors=M |
| `[LINT-BANDIT]` | PASS | exit=N, medium+=M |
| `[LINT-REG-FULL]` | PASS/FAIL | X passed, Y skipped |
| `[LINT-REG-LINT-ONLY]` | PASS/FAIL | 3 passed |

## Сводка находок

| Tool | Exit | Total | CRITICAL | TOLERABLE |
|------|------|-------|----------|-----------|
| ruff | | | | |
| mypy | | | | |
| bandit | | | | |

## CRITICAL (требует coder_1_lint_fix.md)

| File:line | Rule | Описание | Fix scope |
|-----------|------|----------|-----------|
| | | | |

(или «не обнаружено»)

## TOLERABLE (отложить на cleanup)

- ruff: …
- mypy: …

## Выполненные команды

(блоки bash как в test_1.9.md)

## Изменённые файлы

| Файл | Назначение |
|------|------------|
| pyproject.toml | dev deps + ruff/mypy config + marker |
| tests/test_linting.py | non-blocking lint smoke |

## Следующий шаг

При наличии CRITICAL — Planner/Coder: `coder_1_lint_fix.md`. После исправлений — повторный аудит и переход к strict mode (отдельная инструкция).
```

---

## 10. Progress update

Append to `agent_docs/progress/stage_1.md` (append-only):

```
## YYYY-MM-DD — Tester (1.lint)
- STATUS: TEST_PASS | TEST_FAIL
- Sub-stage: backend linting baseline (non-blocking)
- Report: agent_docs/reports/test_1_lint.md
- Infra: ruff, mypy, bandit in dev deps; tests/test_linting.py
- Regression: N passed, M skipped
- CRITICAL findings: <count or none>
- Next: coder_1_lint_fix.md if CRITICAL > 0; else optional strict-mode instruction
```

---

## 11. Definition of done

- [ ] `uv add --dev ruff mypy bandit` — deps pinned in `pyproject.toml`
- [ ] `[tool.ruff]` and `[tool.mypy]` sections present; pytest `lint_audit` marker registered
- [ ] `tests/test_linting.py` implements `[LINT-RUFF]`, `[LINT-MYPY]`, `[LINT-BANDIT]` with warn-not-fail pattern
- [ ] `uv run pytest tests/test_linting.py -v` — 3 tests **passed** (warnings OK)
- [ ] `uv run pytest tests/ --ignore=tests/manual -v` — full regression **passed** (`[LINT-REG-FULL]`)
- [ ] Standalone linter outputs captured in report
- [ ] `agent_docs/reports/test_1_lint.md` — Russian, triage CRITICAL vs TOLERABLE
- [ ] `agent_docs/progress/stage_1.md` appended
- [ ] `src/` untouched

---

## 12. Execution order

1. Confirm Stage 1.9 `TEST_PASS` in `agent_docs/progress/stage_1.md`.
2. Add dev dependencies (`§3`).
3. Update `pyproject.toml` config (`§4`).
4. Implement `tests/test_linting.py` (`§5`).
5. Run lint-only pytest (`§7`).
6. Run full regression (`§7`).
7. Run standalone linters (`§6`); triage output (`§8`).
8. Write report (`§9`); append progress (`§10`).

---

## 13. OUT OF SCOPE

- Modifying production code in `src/`
- Pre-commit hooks / CI gate enforcement
- `uv run ruff format` / auto-fix
- Blocking pytest on lint violations (future stage)
