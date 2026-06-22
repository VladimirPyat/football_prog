"""Informational baseline lint audits for the backend.

These tests are **informational baseline audits**. They do not fail pytest when
linters report issues. A future stage will switch to strict mode after
``coder_1_lint_fix.md``.
"""

from __future__ import annotations

import re
import subprocess
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_TAIL_LIMIT = 2000


def _count_findings(tool: str, output: str) -> int:
    if tool == "ruff":
        return len(re.findall(r"^src/", output, flags=re.MULTILINE))
    if tool == "mypy":
        return len(re.findall(r": error:", output))
    if tool == "bandit":
        return len(re.findall(r">> Issue:", output))
    return 0


def _run_linter(
    request: pytest.FixtureRequest,
    tool: str,
    cmd: list[str],
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    finding_count = _count_findings(tool, combined)
    raw_tail = combined[-RAW_TAIL_LIMIT:] if len(combined) > RAW_TAIL_LIMIT else combined
    if len(combined) > RAW_TAIL_LIMIT:
        raw_tail = f"...{raw_tail}"

    metadata = {
        "tool": tool,
        "exit_code": result.returncode,
        "finding_count": finding_count,
        "raw_tail": raw_tail,
    }
    request.node.user_properties.append((f"lint_{tool}", metadata))

    if result.returncode != 0:
        summary = (
            f"[{tool}] exit={result.returncode}, findings≈{finding_count}: "
            f"{combined[:RAW_TAIL_LIMIT]}"
        )
        if len(combined) > RAW_TAIL_LIMIT:
            summary += "..."
        warnings.warn(summary, UserWarning, stacklevel=2)

    return result


@pytest.mark.lint_audit
def test_lint_ruff_check(request: pytest.FixtureRequest) -> None:
    """[LINT-RUFF] Run ruff check on src/ (non-blocking baseline)."""
    _run_linter(request, "ruff", ["uv", "run", "ruff", "check", "src/"])


@pytest.mark.lint_audit
def test_lint_mypy(request: pytest.FixtureRequest) -> None:
    """[LINT-MYPY] Run mypy on src/ (non-blocking baseline)."""
    _run_linter(request, "mypy", ["uv", "run", "mypy", "src/"])


@pytest.mark.lint_audit
def test_lint_bandit(request: pytest.FixtureRequest) -> None:
    """[LINT-BANDIT] Run bandit -ll on src/ (non-blocking baseline)."""
    _run_linter(request, "bandit", ["uv", "run", "bandit", "-r", "src/", "-ll"])
