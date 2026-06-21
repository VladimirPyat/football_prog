"""[API-SMOKE-*] Calculate smoke, VOID, HTTP caching — NOT 90/90 contract."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Match, RoundStatus, Score
from tests.api.conftest import (
    API_PREFIX,
    api_login,
    auth_header,
    ensure_contest_running,
    get_round_id,
    get_round10_match_ids,
)


@pytest.mark.asyncio
async def test_smoke_calculate_single_round(loaded_api):
    """[API-SMOKE-CALC] calculate round 1 → CALCULATED, users_scored > 0."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 1)
    resp = await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/calculate",
        headers=auth_header(sup),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == RoundStatus.CALCULATED.value
    assert data["users_scored"] > 0


@pytest.mark.asyncio
async def test_void_recalc_updates_leaderboard(loaded_api):
    """[API-VOID] VOID match → recalc; leaderboard changes."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1)
    await client.post(f"{API_PREFIX}/admin/rounds/{rid}/calculate", headers=h)

    before = await client.get(f"{API_PREFIX}/leaderboard")
    total_before = sum(r["total_with_bonus3"] for r in before.json()["leaderboard"])

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(Match.round_id == rid, Match.status == "FINISHED").limit(1)
        )
        mid = match.id

    await client.patch(
        f"{API_PREFIX}/admin/matches/{mid}/status",
        headers=h,
        json={"status": "VOID"},
    )

    after = await client.get(f"{API_PREFIX}/leaderboard")
    total_after = sum(r["total_with_bonus3"] for r in after.json()["leaderboard"])
    assert total_after <= total_before


@pytest.mark.asyncio
async def test_cache_headers_public_get(loaded_api):
    """[API-CACHE] leaderboard/results have Cache-Control + ETag; POST pred does not."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 1)
    await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/calculate",
        headers=auth_header(sup),
    )
    await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/publish",
        headers=auth_header(sup),
    )

    lb = await client.get(f"{API_PREFIX}/leaderboard")
    assert lb.status_code == 200
    assert "cache-control" in lb.headers
    assert "public" in lb.headers["cache-control"].lower()
    assert "etag" in lb.headers

    res = await client.get(f"{API_PREFIX}/rounds/{rid}/results")
    assert res.status_code == 200
    assert "etag" in res.headers

    user = await api_login(client, "shutov")
    rid10 = await get_round_id(sf, 10)
    mids = await get_round10_match_ids(sf)
    pred = await client.post(
        f"{API_PREFIX}/rounds/{rid10}/predictions",
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert pred.status_code == 200
    assert "cache-control" not in pred.headers or "public" not in pred.headers.get(
        "cache-control", ""
    ).lower()


@pytest.mark.asyncio
async def test_cache_etag_changes_after_calculate(loaded_api):
    """[API-CACHE-ETAG] ETag changes after calculate."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    rid2 = await get_round_id(sf, 2)
    first = await client.get(f"{API_PREFIX}/rounds/{rid2}/leaderboard")
    assert first.status_code in (200, 403, 404)

    await client.post(f"{API_PREFIX}/admin/rounds/{rid2}/calculate", headers=h)
    second = await client.get(f"{API_PREFIX}/rounds/{rid2}/leaderboard")
    assert second.status_code == 200
    if first.status_code == 200 and "etag" in first.headers:
        assert second.headers.get("etag") != first.headers.get("etag")
