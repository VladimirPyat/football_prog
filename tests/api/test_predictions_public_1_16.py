"""[API-PRED-VISITOR-*] Public predictions access after deadline (Stage 1.16 fix)."""

from __future__ import annotations

import pytest
from tests.api.conftest import API_PREFIX, get_round_id


@pytest.mark.asyncio
async def test_pred_visitor_pre_deadline(loaded_api):
    """[API-PRED-VISITOR-PRE] Anonymous GET before deadline → 403 PREDICTIONS_NOT_PUBLIC."""
    client, sf, _ = loaded_api
    rid = await get_round_id(sf, 10)
    resp = await client.get(f"{API_PREFIX}/rounds/{rid}/predictions")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("code") == "PREDICTIONS_NOT_PUBLIC"


@pytest.mark.asyncio
async def test_pred_visitor_post_deadline(loaded_api):
    """[API-PRED-VISITOR-POST] Anonymous GET after deadline → 200 full table."""
    client, sf, _ = loaded_api
    rid = await get_round_id(sf, 9)
    resp = await client.get(f"{API_PREFIX}/rounds/{rid}/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deadline_passed"] is True
    for entry in data["entries"]:
        if entry["submitted"]:
            assert entry["predictions"] is not None


@pytest.mark.asyncio
async def test_pred_visitor_post_deadline_shim(loaded_api):
    """[API-PRED-VISITOR-POST-SHIM] Legacy GET /rounds/{id}/predictions, no token → 200."""
    client, sf, _ = loaded_api
    rid = await get_round_id(sf, 9)
    resp = await client.get(f"/api/v1/rounds/{rid}/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deadline_passed"] is True


@pytest.mark.asyncio
async def test_pred_post_no_token(loaded_api):
    """[API-PRED-POST-AUTH] POST predictions without token → 401."""
    client, sf, _ = loaded_api
    rid = await get_round_id(sf, 10)
    resp = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        json={"predictions": [{"match_id": 1, "score1": 1, "score2": 0}]},
    )
    assert resp.status_code == 401
