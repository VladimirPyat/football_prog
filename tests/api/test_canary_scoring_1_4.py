"""[CANARY-PYTEST-*] Automated oracle verification — scores not hardcoded."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

from tests.api.conftest import DEFAULT_CONTEST_ID, calculate_rounds_via_http
from tests.api.reference_compare import compare_scores_to_expected, load_expected_scores


@pytest.mark.asyncio
async def test_canary_pytest_oracle_fails_on_corrupt_csv(loaded_api, tmp_path):
    """[CANARY-PYTEST-ORACLE] Corrupt expected_total in temp oracle → comparison fails."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)

    oracle = tmp_path / "expected_scores.csv"
    src = Path(__file__).resolve().parents[2] / "docs" / "test_data" / "contracted" / "expected_scores.csv"
    shutil.copy(src, oracle)

    rows = load_expected_scores(oracle)
    rows[0]["expected_total"] = str(int(rows[0]["expected_total"]) + 999)
    with oracle.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    from tests.api.reference_compare import build_score_lookup

    login_to_id, round_num_to_id, score_map = await build_score_lookup(sf, DEFAULT_CONTEST_ID)
    matched, mismatches = compare_scores_to_expected(
        load_expected_scores(oracle),
        login_to_id,
        round_num_to_id,
        score_map,
    )
    assert mismatches, "[CANARY-PYTEST-ORACLE] Expected failure on corrupted oracle"
    assert matched < 90
    assert any("total:" in m for m in mismatches)


@pytest.mark.asyncio
async def test_canary_pytest_revert_passes(loaded_api, tmp_path):
    """[CANARY-PYTEST-REVERT] Restored oracle → comparison passes."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)

    oracle = tmp_path / "expected_scores.csv"
    src = Path(__file__).resolve().parents[2] / "docs" / "test_data" / "contracted" / "expected_scores.csv"
    shutil.copy(src, oracle)

    from tests.api.reference_compare import build_score_lookup

    login_to_id, round_num_to_id, score_map = await build_score_lookup(sf, DEFAULT_CONTEST_ID)
    matched, mismatches = compare_scores_to_expected(
        load_expected_scores(oracle),
        login_to_id,
        round_num_to_id,
        score_map,
    )
    assert not mismatches
    assert matched == 90
