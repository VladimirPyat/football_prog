"""[API-PRED-*] Prediction batch, deadline, privacy over HTTP."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from database.models import Match, Round, RoundStatus
from tests.api.conftest import (
    API_PREFIX,
    api_login,
    auth_header,
    get_round10_match_ids,
    get_round_id,
)


@pytest.mark.asyncio
async def test_pred_partial_rejected(loaded_api):
    """[API-PRED-PARTIAL] 7/8 → 400."""
    client, sf, _ = loaded_api
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10)
    match_ids = await get_round10_match_ids(sf)

    resp = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={
            "predictions": [
                {"match_id": mid, "score1": 1, "score2": 0}
                for mid in match_ids[:7]
            ]
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_pred_full_batch(loaded_api):
    """[API-PRED-FULL] 8/8 ACTIVE before deadline → 200."""
    client, sf, _ = loaded_api
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10)
    match_ids = await get_round10_match_ids(sf)

    resp = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={
            "predictions": [
                {"match_id": mid, "score1": 0, "score2": 0} for mid in match_ids
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["saved_count"] == 8


@pytest.mark.asyncio
async def test_pred_range_validation(loaded_api):
    """[API-PRED-RANGE] score 21 → 422; 0 accepted."""
    client, sf, _ = loaded_api
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10)
    match_ids = await get_round10_match_ids(sf)

    bad = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={
            "predictions": [
                {"match_id": match_ids[0], "score1": 21, "score2": 0},
                *[{"match_id": mid, "score1": 1, "score2": 1} for mid in match_ids[1:]],
            ]
        },
    )
    assert bad.status_code == 422

    ok = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={
            "predictions": [
                {"match_id": mid, "score1": 0, "score2": 0} for mid in match_ids
            ]
        },
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_pred_deadline_and_status(loaded_api):
    """[API-PRED-DEADLINE] past deadline / non-ACTIVE → 403."""
    client, sf, _ = loaded_api
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10)
    match_ids = await get_round10_match_ids(sf)
    payload = {
        "predictions": [{"match_id": mid, "score1": 1, "score2": 1} for mid in match_ids]
    }

    async with sf() as session:
        async with session.begin():
            round_ = await session.get(Round, rid)
            round_.deadline = datetime.now(timezone.utc) - timedelta(hours=1)

    past = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json=payload,
    )
    assert past.status_code == 403

    async with sf() as session:
        async with session.begin():
            round_ = await session.get(Round, rid)
            round_.deadline = datetime.now(timezone.utc) + timedelta(days=5)
            round_.status = RoundStatus.CLOSED.value

    closed = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json=payload,
    )
    assert closed.status_code == 403


@pytest.mark.asyncio
async def test_pred_privacy_before_and_after_deadline(loaded_api):
    """[API-PRED-PRIVACY] pre-deadline hide others; post-deadline full table."""
    client, sf, _ = loaded_api
    shutov = await api_login(client, "shutov")
    volchenko = await api_login(client, "volchenko")
    rid = await get_round_id(sf, 10)
    match_ids = await get_round10_match_ids(sf)

    await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(shutov),
        json={
            "predictions": [
                {"match_id": mid, "score1": 2, "score2": 1} for mid in match_ids
            ]
        },
    )

    before = await client.get(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(volchenko),
    )
    assert before.status_code == 200
    data = before.json()
    assert data["deadline_passed"] is False
    for entry in data["entries"]:
        if entry["user_id"] != (await _user_id(sf, "volchenko")):
            assert entry["predictions"] is None
            assert entry["submitted"] in (True, False)

    async with sf() as session:
        async with session.begin():
            round_ = await session.get(Round, rid)
            round_.deadline = datetime.now(timezone.utc) - timedelta(days=1)
            if round_.deadline.tzinfo is None:
                round_.deadline = round_.deadline.replace(tzinfo=timezone.utc)

    after = await client.get(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(volchenko),
    )
    assert after.status_code == 200
    assert after.json()["deadline_passed"] is True
    for entry in after.json()["entries"]:
        if entry["submitted"]:
            assert entry["predictions"] is not None


async def _user_id(sf, login: str) -> int:
    from database.models import User

    async with sf() as session:
        user = await session.scalar(select(User).where(User.login == login))
        assert user
        return user.id
