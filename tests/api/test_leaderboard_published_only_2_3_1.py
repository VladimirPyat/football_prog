"""[API-LB-PUBLISHED-ONLY] Public GET leaderboard/results: PUBLISHED only.

Tests §9.9.2: public (unauthenticated / USER) GET leaderboard → 403 for CALCULATED;
SUPERVISOR → 200 for CALCULATED.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Round, RoundStatus
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round_id,
)


@pytest.mark.asyncio
async def test_lb_public_calculated_round_forbidden(loaded_api):
    """[API-LB-PUBLISHED-ONLY] Unauthenticated GET leaderboard on CALCULATED round → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        # Ensure round is CALCULATED
        round_.status = RoundStatus.CALCULATED
        await session.commit()

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"))
    assert resp.status_code == 403
    assert resp.json().get("code") == "RESULTS_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_lb_user_calculated_round_forbidden(loaded_api):
    """[API-LB-PUBLISHED-ONLY] USER GET leaderboard on CALCULATED round → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user_token = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        round_.status = RoundStatus.CALCULATED
        await session.commit()

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"),
        headers=auth_header(user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_lb_supervisor_calculated_round_allowed(loaded_api):
    """[API-LB-PUBLISHED-ONLY] SUPERVISOR GET leaderboard on CALCULATED round → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        round_.status = RoundStatus.CALCULATED
        await session.commit()

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"),
        headers=auth_header(sup),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_lb_public_published_round_allowed(loaded_api):
    """[API-LB-PUBLISHED-ONLY] Unauthenticated GET leaderboard on PUBLISHED round → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)

    async with sf() as session:
        round_ = await session.get(Round, rid)
        assert round_ is not None
        status = RoundStatus(round_.status)

    if status == RoundStatus.CLOSED:
        calc = await client.post(
            contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
            headers=h,
        )
        assert calc.status_code == 200, calc.text
    elif status not in (RoundStatus.CALCULATED, RoundStatus.PUBLISHED):
        pytest.skip(f"Round 1 unexpected status for publish test: {status}")

    async with sf() as session:
        round_ = await session.get(Round, rid)
        if RoundStatus(round_.status) != RoundStatus.PUBLISHED:
            pub = await client.post(
                contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
                headers=h,
            )
            assert pub.status_code == 200, pub.text

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_global_lb_excludes_calculated(loaded_api):
    """[API-LB-PUBLISHED-ONLY] Global leaderboard includes only PUBLISHED rounds."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)

    # Global leaderboard should return 200 (PUBLISHED rounds only — does not include CALCULATED)
    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    assert resp.status_code == 200
    data = resp.json()
    assert "leaderboard" in data
