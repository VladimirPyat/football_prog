"""Soft-delete visibility, admin restore list, purge candidates."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.api.conftest import _make_api_client, api_login, auth_header, contest_url
from tests.api.stage_112_helpers import apply_env, create_draft_contest

from database.models import Contest


@pytest_asyncio.fixture
async def soft_delete_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    apply_env(monkeypatch, {"SUPERVISOR_TRAINING_MODE": "false"})
    async for item in _make_api_client(
        tmp_path, monkeypatch, "soft_delete.db", instant_delete=True, load_data=False
    ):
        yield item


@pytest.mark.asyncio
async def test_deleted_hidden_from_list(soft_delete_api):
    """Soft-deleted contests are excluded from GET /contests."""
    client, sf, _ = soft_delete_api
    cid, sup_h = await create_draft_contest(client, name="Hidden After Delete")

    deleted = await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )
    assert deleted.status_code == 200

    listed = await client.get("/api/v1/contests", headers=sup_h)
    assert listed.status_code == 200
    assert cid not in [c["id"] for c in listed.json()]


@pytest.mark.asyncio
async def test_list_deleted_admin_only(soft_delete_api):
    """GET /contests/deleted requires ADMIN."""
    client, _, _ = soft_delete_api
    cid, sup_h = await create_draft_contest(client, name="Admin Deleted List")
    await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )

    sup_list = await client.get("/api/v1/contests/deleted", headers=sup_h)
    assert sup_list.status_code == 403

    admin_h = auth_header(await api_login(client, "admin_api"))
    admin_list = await client.get("/api/v1/contests/deleted", headers=admin_h)
    assert admin_list.status_code == 200
    ids = [c["id"] for c in admin_list.json()]
    assert cid in ids
    row = next(c for c in admin_list.json() if c["id"] == cid)
    assert row["restore_available"] is True


@pytest.mark.asyncio
async def test_restore_supervisor_forbidden(soft_delete_api):
    """POST /restore is ADMIN-only."""
    client, _, _ = soft_delete_api
    cid, sup_h = await create_draft_contest(client, name="Restore RBAC")
    await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )

    denied = await client.post(contest_url(cid, "/restore"), headers=sup_h)
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_purge_retention(soft_delete_api):
    """Purge service removes contests past retention window."""
    from services.contest_purge_service import purge_deleted_contests  # noqa: PLC0415

    client, sf, _ = soft_delete_api
    cid, sup_h = await create_draft_contest(client, name="Purge Me")
    await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=sup_h,
        json={"confirm": "DELETE"},
    )

    async with sf() as session:
        contest = await session.get(Contest, cid)
        assert contest is not None
        contest.deleted_at = datetime.now(UTC) - timedelta(days=31)
        await session.commit()

        purged = await purge_deleted_contests(session, dry_run=False)
        await session.commit()
        assert cid in purged

        gone = await session.get(Contest, cid)
        assert gone is None
