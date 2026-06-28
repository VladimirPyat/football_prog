"""Stage 1.12 — B12 lifecycle training mode, pause/resume, restore."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.api.conftest import (
    DEFAULT_CONTEST_ID,
    _make_api_client,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
)
from tests.api.stage_112_helpers import (
    activate_first_round,
    add_teams,
    apply_env,
    create_draft_contest,
)

from database.models import ContestRestoreSnapshot, Round, Team


@pytest_asyncio.fixture
async def training_loaded_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    apply_env(monkeypatch)
    async for item in _make_api_client(
        tmp_path, monkeypatch, "training_loaded.db", instant_delete=True, load_data=True
    ):
        yield item


@pytest_asyncio.fixture
async def no_training_loaded_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    apply_env(monkeypatch, {"SUPERVISOR_TRAINING_MODE": "false"})
    async for item in _make_api_client(
        tmp_path, monkeypatch, "no_training_loaded.db", instant_delete=True, load_data=True
    ):
        yield item


@pytest.mark.asyncio
async def test_life_pause_sup(no_training_loaded_api):
    """[LIFE-PAUSE-SUP] Supervisor pause/resume; USER forbidden."""
    client, sf, _ = no_training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    sup_h = auth_header(sup)
    user = await api_login(client, "shutov")
    user_h = auth_header(user)

    pause = await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=sup_h)
    assert pause.status_code == 200

    resume = await client.post(contest_url(DEFAULT_CONTEST_ID, "/resume"), headers=sup_h)
    assert resume.status_code == 200

    user_pause = await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=user_h)
    assert user_pause.status_code == 403
    user_resume = await client.post(contest_url(DEFAULT_CONTEST_ID, "/resume"), headers=user_h)
    assert user_resume.status_code == 403


@pytest.mark.asyncio
async def test_life_finish_supervisor_denied(no_training_loaded_api):
    """[LIFE-FINISH-TRAIN] supervisor finish forbidden when training mode off."""
    client, sf, _ = no_training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup_h = auth_header(await api_login(client, "supervisor_api"))
    resp = await client.post(contest_url(DEFAULT_CONTEST_ID, "/finish"), headers=sup_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_life_finish_admin_allowed(no_training_loaded_api):
    """[LIFE-FINISH-TRAIN] admin finish allowed when training mode off."""
    client, sf, _ = no_training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin_h = auth_header(await api_login(client, "admin_api"))
    resp = await client.post(contest_url(DEFAULT_CONTEST_ID, "/finish"), headers=admin_h)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_life_finish_supervisor_training(training_loaded_api):
    """[LIFE-FINISH-TRAIN] supervisor finish allowed when training mode on."""
    client, sf, _ = training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup_h = auth_header(await api_login(client, "supervisor_api"))
    resp = await client.post(contest_url(DEFAULT_CONTEST_ID, "/finish"), headers=sup_h)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_life_delete_supervisor_allowed(no_training_loaded_api):
    """[LIFE-DELETE] supervisor can delete PAUSED contest (instant delete in test env)."""
    client, sf, _ = no_training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup_h = auth_header(await api_login(client, "supervisor_api"))
    await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=sup_h)
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


@pytest.mark.asyncio
async def test_life_delete_supervisor_training(training_loaded_api):
    """[LIFE-DELETE-TRAIN] supervisor delete allowed when training mode on."""
    client, sf, _ = training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup_h = auth_header(await api_login(client, "supervisor_api"))
    await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=sup_h)
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


@pytest.mark.asyncio
async def test_restore_window(training_loaded_api):
    """[RESTORE-WINDOW] delete snapshot restore within window; consumed after use."""
    client, sf, _ = training_loaded_api
    cid, sup_h = await create_draft_contest(client, name="Restore Test")
    tids = await add_teams(client, cid, sup_h, count=16)
    await activate_first_round(client, cid, sup_h, tids)

    async with sf() as session:
        teams_before = (await session.scalars(select(Team).where(Team.contest_id == cid))).all()
        rounds_before = (await session.scalars(select(Round).where(Round.contest_id == cid))).all()
        team_count = len(teams_before)
        round_count = len(rounds_before)
        assert team_count == 16
        assert round_count >= 1

    await client.post(contest_url(cid, "/pause"), headers=sup_h)
    deleted = await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )
    assert deleted.status_code == 200

    async with sf() as session:
        teams_after = (await session.scalars(select(Team).where(Team.contest_id == cid))).all()
        assert len(teams_after) == 0

    restore = await client.post(
        contest_url(cid, "/restore"),
        headers=auth_header(await api_login(client, "admin_api")),
    )
    assert restore.status_code == 200
    assert restore.json()["restored"] is True

    async with sf() as session:
        teams_restored = (await session.scalars(select(Team).where(Team.contest_id == cid))).all()
        rounds_restored = (await session.scalars(select(Round).where(Round.contest_id == cid))).all()
        assert len(teams_restored) == team_count
        assert len(rounds_restored) == round_count

    again = await client.post(
        contest_url(cid, "/restore"),
        headers=auth_header(await api_login(client, "admin_api")),
    )
    assert again.status_code in (404, 410)

    await client.post(contest_url(cid, "/pause"), headers=sup_h)
    await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )

    async with sf() as session:
        snap = await session.get(ContestRestoreSnapshot, cid)
        assert snap is not None
        snap.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    expired = await client.post(
        contest_url(cid, "/restore"),
        headers=auth_header(await api_login(client, "admin_api")),
    )
    assert expired.status_code == 410
