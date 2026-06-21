"""[API-CONTEST-DELETE-*] Stage 1.4.1 contest-scoped lifecycle."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Contest, ContestLifecycleStatus
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round10_match_ids,
    get_round_id,
)


@pytest.mark.asyncio
async def test_contest_finish(loaded_contest_api):
    """[API-CONTEST-FINISH] POST finish → predictions 403; public GET 200."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    h = auth_header(admin)
    await client.post(contest_url(DEFAULT_CONTEST_ID, "/finish"), headers=h)

    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)
    pred = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert pred.status_code == 403

    lb = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    assert lb.status_code == 200


@pytest.mark.asyncio
async def test_contest_finish_idempotent(loaded_contest_api):
    """[API-CONTEST-FINISH-IDEM] second finish → 200 no-op."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    h = auth_header(admin)
    await client.post(contest_url(DEFAULT_CONTEST_ID, "/finish"), headers=h)
    again = await client.post(contest_url(DEFAULT_CONTEST_ID, "/finish"), headers=h)
    assert again.status_code == 200


@pytest.mark.asyncio
async def test_contest_pause_blocks_predictions(loaded_contest_api):
    """[API-CONTEST-PAUSE-BLOCK] predictions while PAUSED → 403."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    user = await api_login(client, "shutov")
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/pause"),
        headers=auth_header(admin),
    )
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contest_delete_rbac(delete_contest_api):
    """[API-CONTEST-DELETE-RBAC] DELETE as SUPERVISOR → 403."""
    client, sf, _ = delete_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/pause"),
        headers=auth_header(admin),
    )
    sup = await api_login(client, "supervisor_api")
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=auth_header(sup),
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contest_delete_no_grace(loaded_contest_api):
    """[API-CONTEST-DELETE-NOGRACE] instant=false → 400 right after pause."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/pause"),
        headers=auth_header(admin),
    )
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=auth_header(admin),
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_contest_delete_bad_confirm(delete_contest_api):
    """[API-CONTEST-DELETE-BADCONFIRM] wrong confirm → 422/400."""
    client, sf, _ = delete_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/pause"),
        headers=auth_header(admin),
    )
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=auth_header(admin),
        json={"confirm": "NOPE"},
    )
    assert resp.status_code in (400, 422), resp.text


@pytest.mark.asyncio
async def test_contest_delete_ok(delete_contest_api):
    """[API-CONTEST-DELETE-OK] pause → DELETE with instant=true → 200; DRAFT."""
    client, sf, _ = delete_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/pause"),
        headers=auth_header(admin),
    )
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=auth_header(admin),
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DRAFT"

    async with sf() as session:
        contest = await session.get(Contest, DEFAULT_CONTEST_ID)
        assert contest is not None
        assert contest.status == ContestLifecycleStatus.DRAFT.value
