"""Fix 1.20 — contest structure validation and match short names in API."""

from __future__ import annotations

import pytest

from tests.api.conftest import (
    API_PREFIX,
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    calculate_rounds_via_http,
    contest_url,
    get_round_id,
    publish_rounds_via_http,
)


@pytest.mark.asyncio
async def test_patch_contest_rejects_odd_round_robin(empty_api) -> None:
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    created = await client.post(f"{API_PREFIX}/contests", headers=h, json={"name": "Odd RR"})
    assert created.status_code == 200
    cid = created.json()["id"]

    resp = await client.patch(
        contest_url(cid, ""),
        headers=h,
        json={
            "total_teams": 15,
            "matches_per_round": 7,
            "total_rounds": 28,
            "is_round_robin": True,
        },
    )
    assert resp.status_code == 400
    assert "чётное" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_predictions_match_includes_short_names(loaded_api) -> None:
    client, sf, _ = loaded_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    cid = DEFAULT_CONTEST_ID
    rid = await get_round_id(sf, 1, cid)

    teams = (await client.get(contest_url(cid, "/teams"), headers=h)).json()
    spartak = next(t for t in teams if t["short_name"] == "Спа")
    assert spartak["name"] == "Спартак"

    resp = await client.get(contest_url(cid, f"/rounds/{rid}/predictions"), headers=h)
    assert resp.status_code == 200
    matches = resp.json()["matches"]
    assert matches
    sample = next(
        m for m in matches if m.get("team1_short") == "Спа" or m.get("team2_short") == "Спа"
    )
    if sample.get("team1_short") == "Спа":
        assert sample["team1"] == spartak["name"]
    else:
        assert sample["team2"] == spartak["name"]


@pytest.mark.asyncio
async def test_round_results_match_includes_short_names(loaded_api) -> None:
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID, round_numbers=[1])
    await publish_rounds_via_http(client, sf, DEFAULT_CONTEST_ID, round_numbers=[1])
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    cid = DEFAULT_CONTEST_ID
    rid = await get_round_id(sf, 1, cid)

    resp = await client.get(contest_url(cid, f"/rounds/{rid}/results"), headers=h)
    assert resp.status_code == 200
    matches = resp.json()["matches"]
    assert matches
    assert all("team1_short" in m and "team2_short" in m for m in matches)
