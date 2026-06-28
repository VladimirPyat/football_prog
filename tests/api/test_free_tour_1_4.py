"""[OP-FREE-*] Stage 1.4 Free Tour — contest-scoped."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from database.models import Match, MatchStatus, Round, RoundStatus
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round_id,
)


@pytest.mark.asyncio
async def test_op_free_tour(loaded_api):
    """[OP-FREE-TOUR] POSTPONED match → free-tour → new round; match removed from source."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(Match.round_id == rid).limit(1)
        )
        mid = match.id
        source_count_before = await session.scalar(
            select(func.count()).select_from(Match).where(Match.round_id == rid)
        )

    await client.patch(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/status"),
        headers=h,
        json={"status": MatchStatus.POSTPONED.value},
    )

    now = datetime.now(timezone.utc)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/admin/rounds/free-tour"),
        headers=h,
        json={
            "deadline": (now + timedelta(days=10)).isoformat(),
            "matches": [
                {"match_id": mid, "new_date_time": (now + timedelta(days=14)).isoformat()}
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    new_round_id = body["round_id"]
    assert body["kind"] == "SUPPLEMENTARY"
    assert body["supplementary_index"] is not None
    assert body["source_round_numbers"] == [10]

    async with sf() as session:
        moved = await session.get(Match, mid)
        assert moved.round_id == new_round_id
        assert moved.origin_round_id == rid
        new_round = await session.get(Round, new_round_id)
        assert new_round is not None
        assert new_round.kind == "SUPPLEMENTARY"
        assert new_round.supplementary_index is not None

    listed = await client.get(contest_url(DEFAULT_CONTEST_ID, "/rounds"), headers=h)
    assert listed.status_code == 200
    free_round = next(r for r in listed.json() if r["id"] == new_round_id)
    assert free_round["kind"] == "SUPPLEMENTARY"
    assert free_round["source_round_numbers"] == [10]

    async with sf() as session:
        source_count_after = await session.scalar(
            select(func.count()).select_from(Match).where(Match.round_id == rid)
        )
        source_round = await session.get(Round, rid)
        assert source_count_after == source_count_before - 1
        assert source_round.matches_count == source_count_after
