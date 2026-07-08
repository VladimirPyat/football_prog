"""Stage 1.18 — cumulative round leaderboard, predictions_count, total_bonus_points."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Prediction, Round, RoundStatus, Score, User
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    calculate_rounds_via_http,
    contest_url,
    get_round_id,
    publish_rounds_via_http,
)
from tests.api.reference_compare import load_leaderboard


@pytest.fixture
async def published_through_round_9(loaded_api):
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID)
    await publish_rounds_via_http(client, sf, DEFAULT_CONTEST_ID, round_numbers=range(1, 10))
    return client, sf


@pytest.mark.asyncio
async def test_lb_scope_total_matches_csv(published_through_round_9):
    client, sf = published_through_round_9
    rid9 = await get_round_id(sf, 9, DEFAULT_CONTEST_ID)

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid9}/leaderboard"),
        params={"scope": "total"},
    )
    assert resp.status_code == 200
    rows_by_login: dict[str, dict] = {}
    async with sf() as session:
        users = (await session.scalars(select(User))).all()
        login_by_id = {u.id: u.login.strip() for u in users}
    for row in resp.json()["leaderboard"]:
        login = login_by_id[row["user_id"]]
        rows_by_login[login] = row

    for csv_row in load_leaderboard():
        login = csv_row["user_login"].strip()
        api_row = rows_by_login[login]
        assert api_row["rank"] == int(csv_row["rank"])
        assert api_row["predictions_count"] == int(csv_row["total_predictions"])
        assert api_row["points_base"] == int(csv_row["total_without_bonuses"])
        assert api_row["total_bonus_points"] == int(csv_row["total_bonuses"])
        assert api_row["total_with_bonus3"] == int(csv_row["total_points"])
        assert api_row["count_exact_high"] == int(csv_row["exact_high_count"])
        assert api_row["count_exact"] == int(csv_row["exact_count"])
        assert api_row["count_diff"] == int(csv_row["diff_count"])
        assert api_row["count_outcome"] == int(csv_row["outcome_count"])


@pytest.mark.asyncio
async def test_lb_scope_total_mid_round(published_through_round_9):
    client, sf = published_through_round_9
    rid5 = await get_round_id(sf, 5, DEFAULT_CONTEST_ID)

    async with sf() as session:
        rounds_1_5 = (
            await session.scalars(
                select(Round).where(
                    Round.contest_id == DEFAULT_CONTEST_ID,
                    Round.number <= 5,
                    Round.status == RoundStatus.PUBLISHED.value,
                )
            )
        ).all()
        round_ids = [r.id for r in rounds_1_5]
        scores = (
            await session.scalars(select(Score).where(Score.round_id.in_(round_ids)))
        ).all()
        expected_by_user: dict[int, int] = {}
        pred_expected: dict[int, int] = {}
        for s in scores:
            expected_by_user[s.user_id] = (
                expected_by_user.get(s.user_id, 0) + s.total_with_bonus3
            )
        preds = (
            await session.scalars(
                select(Prediction).where(Prediction.round_id.in_(round_ids))
            )
        ).all()
        for p in preds:
            pred_expected[p.user_id] = pred_expected.get(p.user_id, 0) + 1

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid5}/leaderboard"),
        params={"scope": "total"},
    )
    assert resp.status_code == 200
    for row in resp.json()["leaderboard"]:
        assert row["total_with_bonus3"] == expected_by_user[row["user_id"]]
        assert row["predictions_count"] == pred_expected[row["user_id"]]


@pytest.mark.asyncio
async def test_lb_scope_round_single_round_and_predictions(published_through_round_9):
    client, sf = published_through_round_9
    rid9 = await get_round_id(sf, 9, DEFAULT_CONTEST_ID)

    resp_default = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid9}/leaderboard"),
    )
    resp_round = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid9}/leaderboard"),
        params={"scope": "round"},
    )
    assert resp_default.status_code == 200
    assert resp_round.json() == resp_default.json()

    rows = resp_default.json()["leaderboard"]
    assert rows
    for row in rows:
        assert row["predictions_count"] == 8
        assert row["total_bonus_points"] == row["bonus1"] + row["bonus2"] + row["bonus3"]

    async with sf() as session:
        larin = await session.scalar(select(User).where(User.login == "larin"))
        assert larin is not None
    larin_row = next(r for r in rows if r["user_id"] == larin.id)
    assert larin_row["total_with_bonus3"] != 436


@pytest.mark.asyncio
async def test_lb_global_predictions_and_bonus_totals(published_through_round_9):
    client, sf = published_through_round_9
    resp = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    assert resp.status_code == 200

    for csv_row in load_leaderboard():
        name_key = csv_row["user_login"].strip()
        async with sf() as session:
            user = await session.scalar(select(User).where(User.login == name_key))
        assert user is not None
        api_row = next(r for r in resp.json()["leaderboard"] if r["user_id"] == user.id)
        assert api_row["predictions_count"] == int(csv_row["total_predictions"])
        assert api_row["total_bonus_points"] == int(csv_row["total_bonuses"])
        assert api_row["total_bonus_points"] == (
            api_row["bonus1"] + api_row["bonus2"] + api_row["bonus3"]
        )


@pytest.mark.asyncio
async def test_lb_scope_total_rejects_calculated_for_public(loaded_api):
    client, sf, _ = loaded_api
    await calculate_rounds_via_http(client, sf, DEFAULT_CONTEST_ID, round_numbers=range(1, 10))
    rid10 = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)

    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid10}/leaderboard"),
        params={"scope": "total"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "RESULTS_NOT_AVAILABLE"
