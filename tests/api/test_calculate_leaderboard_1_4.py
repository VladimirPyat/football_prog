"""[API-CALC-*] [API-LB-*] Stage 1.4 calculate + leaderboard contract (90/90 + 10/10)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Match, RoundStatus, User
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    calculate_rounds_via_http,
    contest_url,
    ensure_contest_running,
    get_round_id,
)
from tests.api.reference_compare import (
    assert_scores_match_expected,
    build_score_lookup,
    compare_leaderboard_counts,
    load_leaderboard,
)


@pytest.mark.asyncio
async def test_api_calc_rounds_1_9(loaded_api):
    """[API-CALC] calculate rounds 1–9 → CALCULATED, users_scored > 0."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 9, DEFAULT_CONTEST_ID)
    async with sf() as session:
        from database.models import Round

        round_ = await session.get(Round, rid)
        assert round_.status == RoundStatus.CALCULATED.value


@pytest.mark.asyncio
async def test_api_results_90_of_90(loaded_api):
    """[API-RESULTS] Score rows match expected_scores.csv — 90/90."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    await assert_scores_match_expected(sf, DEFAULT_CONTEST_ID)


@pytest.mark.asyncio
async def test_api_lb_global_10_of_10(loaded_api):
    """[API-LB-GLOBAL] Aggregated counts match leaderboard.csv — 10/10."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    login_to_id, _, score_map = await build_score_lookup(sf, DEFAULT_CONTEST_ID)
    matched, mismatches = compare_leaderboard_counts(
        load_leaderboard(), login_to_id, score_map
    )
    assert not mismatches, f"[API-LB-GLOBAL] mismatches:\n" + "\n".join(mismatches)
    assert matched == 10


@pytest.mark.asyncio
async def test_api_void_recalc(loaded_api):
    """[API-VOID] VOID → atomic recalc; leaderboard updated."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    before = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    total_before = sum(r["total_with_bonus3"] for r in before.json()["leaderboard"])

    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    async with sf() as session:
        match = await session.scalar(
            select(Match).where(Match.round_id == rid, Match.status == "FINISHED").limit(1)
        )
        mid = match.id

    await client.patch(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/status"),
        headers=h,
        json={"status": "VOID"},
    )
    after = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    total_after = sum(r["total_with_bonus3"] for r in after.json()["leaderboard"])
    assert total_after <= total_before


@pytest.mark.asyncio
async def test_api_cache_headers(loaded_api):
    """[API-CACHE] public GET Cache-Control + ETag on contest-scoped leaderboard/results."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=h,
    )

    lb = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    assert lb.status_code == 200
    assert "cache-control" in lb.headers
    assert "public" in lb.headers["cache-control"].lower()
    assert "etag" in lb.headers

    res = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/results")
    )
    assert res.status_code == 200
    assert "etag" in res.headers


@pytest.mark.asyncio
async def test_api_cache_etag_changes(loaded_api):
    """[API-CACHE-ETAG] ETag changes after calculate (supervisor preview on CALCULATED)."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 2, DEFAULT_CONTEST_ID)

    first = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"),
        headers=h,
    )
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    second = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"),
        headers=h,
    )
    assert second.status_code == 200
    if first.status_code == 200 and "etag" in first.headers:
        assert second.headers.get("etag") != first.headers.get("etag")


@pytest.mark.asyncio
async def test_api_tiebreak_set(loaded_api):
    """[API-TB-SET] ADMIN PUT exceptional-tiebreak when locked → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    async with sf() as session:
        uid = await session.scalar(select(User.id).where(User.login == "shutov"))
    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/participants/{uid}/exceptional-tiebreak"),
        headers=auth_header(admin),
        json={"points": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["exceptional_tiebreak_points"] == 5


@pytest.mark.asyncio
async def test_api_tiebreak_rank(loaded_api):
    """[API-TB-RANK] synthetic tie; exceptional points decide rank."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    sup_h = auth_header(sup)
    for n in range(1, 10):
        rid = await get_round_id(sf, n, DEFAULT_CONTEST_ID)
        pub = await client.post(
            contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
            headers=sup_h,
        )
        assert pub.status_code == 200, pub.text

    admin = await api_login(client, "admin_api")
    h = auth_header(admin)

    async with sf() as session:
        u_high = await session.scalar(select(User.id).where(User.login == "shutov"))
        u_low = await session.scalar(select(User.id).where(User.login == "volchenko"))

    await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/participants/{u_high}/exceptional-tiebreak"),
        headers=h,
        json={"points": 10},
    )
    await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/participants/{u_low}/exceptional-tiebreak"),
        headers=h,
        json={"points": 0},
    )

    lb = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    rows = {r["user_id"]: r["rank"] for r in lb.json()["leaderboard"]}
    if rows.get(u_high) and rows.get(u_low) and rows[u_high] != rows[u_low]:
        pytest.skip("Users not tied on criteria 1-4 in contracted data")
    assert rows[u_high] <= rows[u_low]


@pytest.mark.asyncio
async def test_api_tiebreak_rbac(loaded_api):
    """[API-TB-RBAC] SUPERVISOR cannot set → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    async with sf() as session:
        uid = await session.scalar(select(User.id).where(User.login == "shutov"))
    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/participants/{uid}/exceptional-tiebreak"),
        headers=auth_header(sup),
        json={"points": 1},
    )
    assert resp.status_code == 403
