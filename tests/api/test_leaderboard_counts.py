"""Stage 1.7 — leaderboard count_* fields on round and global standings."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import RoundStatus, Score, User
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    calculate_rounds_via_http,
    contest_url,
    get_round_id,
    publish_rounds_via_http,
)
from tests.api.reference_compare import load_leaderboard


@pytest.mark.asyncio
async def test_lb_counts_round(loaded_api):
    """[LB-COUNTS-ROUND] Published round leaderboard exposes count_* fields."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=h,
    )

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"))
    assert resp.status_code == 200
    rows = resp.json()["leaderboard"]
    assert rows

    count_keys = ("count_exact_high", "count_exact", "count_diff", "count_outcome")
    has_non_zero = False
    for row in rows:
        for key in count_keys:
            assert key in row
            assert isinstance(row[key], int)
            assert row[key] >= 0
        if any(row[k] > 0 for k in count_keys):
            has_non_zero = True

    assert has_non_zero, "Expected at least one user with non-zero count_* on contracted data"

    first = rows[0]
    async with sf() as session:
        score = await session.scalar(
            select(Score).where(Score.round_id == rid, Score.user_id == first["user_id"])
        )
        assert score is not None
        assert first["count_exact_high"] == score.count_exact_high
        assert first["count_exact"] == score.count_exact
        assert first["count_diff"] == score.count_diff
        assert first["count_outcome"] == score.count_outcome


@pytest.mark.asyncio
async def test_lb_counts_global(loaded_api):
    """[LB-COUNTS-GLOBAL] Global leaderboard count_* match StandingRow aggregates."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    await publish_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    assert resp.status_code == 200
    rows = {r["user_id"]: r for r in resp.json()["leaderboard"]}

    csv_rows = {r["user_login"]: r for r in load_leaderboard()}
    async with sf() as session:
        larin = await session.scalar(select(User).where(User.login == "larin"))
        assert larin is not None

    larin_row = rows[larin.id]
    csv = csv_rows["larin"]
    assert larin_row["count_exact_high"] == int(csv["exact_high_count"])
    assert larin_row["count_exact"] == int(csv["exact_count"])
    assert larin_row["count_diff"] == int(csv["diff_count"])
    assert larin_row["count_outcome"] == int(csv["outcome_count"])


@pytest.mark.asyncio
async def test_lb_counts_zero_user_omitted(loaded_api):
    """[LB-COUNTS-ZERO] User without score row is omitted from round leaderboard."""
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=h,
    )

    async with sf() as session:
        from database.models import Round

        round_ = await session.get(Round, rid)
        assert round_.status == RoundStatus.PUBLISHED.value
        scored_user_ids = {
            s.user_id
            for s in (await session.scalars(select(Score).where(Score.round_id == rid))).all()
        }
        all_users = (await session.scalars(select(User))).all()
        unscored = [u for u in all_users if u.id not in scored_user_ids]

    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/leaderboard"))
    lb_user_ids = {r["user_id"] for r in resp.json()["leaderboard"]}
    for user in unscored:
        assert user.id not in lb_user_ids
