"""Stage 1.17 — round results per-match points API tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Round, RoundStatus, Score
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    calculate_rounds_via_http,
    contest_url,
    ensure_contest_running,
    get_round_id,
    publish_rounds_via_http,
)


async def _prepare_round_9_published(client, sf) -> int:
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID, round_numbers=range(1, 10))
    await publish_rounds_via_http(client, sf, DEFAULT_CONTEST_ID, round_numbers=range(1, 10))
    return await get_round_id(sf, 9, DEFAULT_CONTEST_ID)


@pytest.mark.asyncio
async def test_results_points_len(loaded_api):
    """[API-RESULTS-POINTS-LEN] PUBLISHED round 9 → 200; len(results[0].points) == len(matches)."""
    client, sf, _ = loaded_api
    rid = await _prepare_round_9_published(client, sf)

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"]
    assert data["matches"]
    assert len(data["results"][0]["points"]) == len(data["matches"])


@pytest.mark.asyncio
async def test_results_points_nonempty(loaded_api):
    """[API-RESULTS-POINTS-NONEMPTY] At least one user has base_points > 0 on loaded fixture."""
    client, sf, _ = loaded_api
    rid = await _prepare_round_9_published(client, sf)

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results"))
    assert resp.status_code == 200
    data = resp.json()

    any_positive = any(
        p.get("base_points") is not None and p["base_points"] > 0
        for row in data["results"]
        for p in row["points"]
    )
    assert any_positive


@pytest.mark.asyncio
async def test_results_points_order(loaded_api):
    """[API-RESULTS-POINTS-ORDER] points[i].match_id == matches[i].id for all i."""
    client, sf, _ = loaded_api
    rid = await _prepare_round_9_published(client, sf)

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results"))
    assert resp.status_code == 200
    data = resp.json()
    match_ids = [m["id"] for m in data["matches"]]

    for row in data["results"]:
        assert len(row["points"]) == len(match_ids)
        for i, point in enumerate(row["points"]):
            assert point["match_id"] == match_ids[i]


@pytest.mark.asyncio
async def test_results_total_without_bonus3(loaded_api):
    """[API-RESULTS-TOTAL-WO-B3] Row includes total_without_bonus3 matching scores table."""
    client, sf, _ = loaded_api
    rid = await _prepare_round_9_published(client, sf)

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results"))
    assert resp.status_code == 200
    data = resp.json()

    async with sf() as session:
        scores = (await session.scalars(select(Score).where(Score.round_id == rid))).all()
        score_map = {s.user_id: s.total_without_bonus3 for s in scores}

    for row in data["results"]:
        assert "total_without_bonus3" in row
        assert row["total_without_bonus3"] == score_map[row["user_id"]]


@pytest.mark.asyncio
async def test_results_not_published(loaded_api):
    """[API-RESULTS-NOT-PUBLISHED] ACTIVE round → 403 RESULTS_NOT_AVAILABLE."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        round_.status = RoundStatus.ACTIVE
        await session.commit()

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results"))
    assert resp.status_code == 403
    assert resp.json().get("code") == "RESULTS_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_results_calc_staff(loaded_api):
    """[API-RESULTS-CALC-STAFF] SUPERVISOR on CALCULATED round → 200 with points."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")

    # Round 9 is CLOSED in loader; calculate → CALCULATED with scores (dev fixture uses round 10).
    await calculate_rounds_via_http(
        client, sf, DEFAULT_CONTEST_ID, round_numbers=range(9, 10)
    )
    rid = await get_round_id(sf, 9, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        assert round_.status == RoundStatus.CALCULATED.value

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results"),
        headers=auth_header(sup),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matches"]
    assert data["results"]
    assert len(data["results"][0]["points"]) == len(data["matches"])
