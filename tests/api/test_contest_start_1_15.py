"""Stage 1.15 — POST /contests/{id}/start and DRAFT lifecycle."""

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
    NEW_SECURE_PASSWORD,
    add_teams,
    apply_env,
    complete_setup,
    create_draft_contest,
    fulfill_start_prerequisites,
    invite_participant,
    participant_status,
    user_exists,
)

from database.models import Contest, ContestLifecycleStatus, ContestRestoreSnapshot, Team


@pytest_asyncio.fixture
async def training_loaded_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    apply_env(monkeypatch)
    async for item in _make_api_client(
        tmp_path, monkeypatch, "start_training.db", instant_delete=True, load_data=True
    ):
        yield item


@pytest_asyncio.fixture
async def no_training_loaded_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    apply_env(monkeypatch, {"SUPERVISOR_TRAINING_MODE": "false"})
    async for item in _make_api_client(
        tmp_path, monkeypatch, "start_no_training.db", instant_delete=True, load_data=True
    ):
        yield item


@pytest_asyncio.fixture
async def stage_112_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    apply_env(monkeypatch)
    async for item in _make_api_client(
        tmp_path, monkeypatch, "start_stage_112.db", instant_delete=False, load_data=False
    ):
        yield item


async def _start_contest(client, contest_id: int, headers: dict[str, str]):
    return await client.post(
        f"/api/v1/contests/{contest_id}/start",
        headers=headers,
    )


async def _get_contest(client, contest_id: int, headers: dict[str, str]) -> dict:
    resp = await client.get(f"/api/v1/contests/{contest_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_start_draft(stage_112_api):
    """[START-DRAFT] POST start on DRAFT → RUNNING, is_locked=true."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Draft")
    await fulfill_start_prerequisites(client, cid, h)

    resp = await _start_contest(client, cid, h)
    assert resp.status_code == 200
    assert resp.json()["status"] == ContestLifecycleStatus.RUNNING.value

    contest = await _get_contest(client, cid, h)
    assert contest["status"] == ContestLifecycleStatus.RUNNING.value
    assert contest["is_locked"] is True


@pytest.mark.asyncio
async def test_start_purge(stage_112_api):
    """[START-PURGE] PENDING removed, ACCEPTED kept on start."""
    client, sf, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Purge")
    await add_teams(client, cid, h)
    pending = await invite_participant(
        client, cid, h, email="start_pending@example.com", login="start_pending_user"
    )
    accepted = await invite_participant(
        client, cid, h, email="start_accepted@example.com", login="start_accepted_user"
    )
    await complete_setup(client, accepted["setup_url"], new_password=NEW_SECURE_PASSWORD)
    accepted2 = await invite_participant(
        client, cid, h, email="start_accepted2@example.com", login="start_accepted_user2"
    )
    await complete_setup(client, accepted2["setup_url"], new_password=NEW_SECURE_PASSWORD)

    resp = await _start_contest(client, cid, h)
    assert resp.status_code == 200

    parts = await client.get(f"/api/v1/contests/{cid}/participants", headers=h)
    assert parts.status_code == 200
    user_ids = {p["user_id"] for p in parts.json()}
    assert pending["user_id"] not in user_ids
    assert accepted["user_id"] in user_ids
    assert await user_exists(sf, pending["user_id"]) is False
    assert await participant_status(sf, cid, accepted["user_id"]) == "ACCEPTED"


@pytest.mark.asyncio
async def test_start_idempotent(stage_112_api):
    """[START-IDEM] POST start twice → 200, no error."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Idem")
    await fulfill_start_prerequisites(client, cid, h)

    first = await _start_contest(client, cid, h)
    assert first.status_code == 200
    second = await _start_contest(client, cid, h)
    assert second.status_code == 200
    assert second.json()["status"] == ContestLifecycleStatus.RUNNING.value


@pytest.mark.asyncio
async def test_start_draft_patch(stage_112_api):
    """[START-DRAFT-PATCH] PATCH structure after start → 403 CONTEST_LOCKED."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Patch")
    await fulfill_start_prerequisites(client, cid, h)
    await _start_contest(client, cid, h)

    patch = await client.patch(
        f"/api/v1/contests/{cid}",
        headers=h,
        json={"total_teams": 15},
    )
    assert patch.status_code == 403
    assert patch.json()["code"] == "CONTEST_LOCKED"


@pytest.mark.asyncio
async def test_start_activate(stage_112_api):
    """[START-ACTIVATE] Start then activate DRAFT round → 200."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Activate")
    tids = await add_teams(client, cid, h)
    await fulfill_start_prerequisites(client, cid, h, skip_teams=True)
    await _start_contest(client, cid, h)

    now = datetime.now(UTC)
    matches = []
    for i in range(8):
        match_at = now + timedelta(days=30 + i)
        matches.append(
            {
                "team1_id": tids[i * 2],
                "team2_id": tids[i * 2 + 1],
                "date_time": match_at.isoformat(),
            }
        )
    earliest = now + timedelta(days=30)
    deadline = (earliest - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        f"/api/v1/contests/{cid}/admin/rounds",
        headers=h,
        json={"number": 1, "deadline": deadline, "matches": matches},
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]

    act = await client.post(
        f"/api/v1/contests/{cid}/admin/rounds/{rid}/activate",
        headers=h,
    )
    assert act.status_code == 200, act.text
    assert act.json()["status"] == "ACTIVE"

    contest = await _get_contest(client, cid, h)
    assert contest["status"] == ContestLifecycleStatus.RUNNING.value
    assert contest["is_locked"] is True


@pytest.mark.asyncio
async def test_start_forbidden(no_training_loaded_api):
    """[START-FORBIDDEN] start on PAUSED/FINISHED → 409."""
    client, sf, _ = no_training_loaded_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup_h = auth_header(await api_login(client, "supervisor_api"))

    pause = await client.post(
        f"/api/v1/contests/{DEFAULT_CONTEST_ID}/pause",
        headers=sup_h,
    )
    assert pause.status_code == 200
    paused_start = await _start_contest(client, DEFAULT_CONTEST_ID, sup_h)
    assert paused_start.status_code == 409

    await client.post(f"/api/v1/contests/{DEFAULT_CONTEST_ID}/resume", headers=sup_h)
    admin_h = auth_header(await api_login(client, "admin_api"))
    finish = await client.post(
        f"/api/v1/contests/{DEFAULT_CONTEST_ID}/finish",
        headers=admin_h,
    )
    assert finish.status_code == 200
    finished_start = await _start_contest(client, DEFAULT_CONTEST_ID, sup_h)
    assert finished_start.status_code == 409


@pytest.mark.asyncio
async def test_delete_draft_train(training_loaded_api):
    """[DELETE-DRAFT-TRAIN] SUPERVISOR + training mode deletes DRAFT contest."""
    client, sf, _ = training_loaded_api

    cid, h = await create_draft_contest(client, name="Draft Delete Train")
    await add_teams(client, cid, h, count=4)

    resp = await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=h,
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"

    async with sf() as session:
        teams = (await session.scalars(select(Team).where(Team.contest_id == cid))).all()
        snap = await session.get(ContestRestoreSnapshot, cid)
        contest = await session.get(Contest, cid)
        assert len(teams) == 0
        assert snap is not None
        assert contest is not None
        assert contest.deleted_at is not None
        assert contest.status == ContestLifecycleStatus.DRAFT.value


@pytest.mark.asyncio
async def test_delete_draft_prod(no_training_loaded_api):
    """[DELETE-DRAFT-PROD] SUPERVISOR can soft-delete DRAFT without training mode."""
    client, sf, _ = no_training_loaded_api

    cid, h = await create_draft_contest(client, name="Draft Delete Prod")
    resp = await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=h,
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"

    listed = await client.get("/api/v1/contests", headers=h)
    assert listed.status_code == 200
    assert cid not in [c["id"] for c in listed.json()]

    async with sf() as session:
        contest = await session.get(Contest, cid)
        assert contest is not None
        assert contest.deleted_at is not None


@pytest.mark.asyncio
async def test_restore_after_draft_del(training_loaded_api):
    """[RESTORE-AFTER-DRAFT-DEL] delete DRAFT → restore within window."""
    client, sf, _ = training_loaded_api

    cid, h = await create_draft_contest(client, name="Draft Restore")
    tids = await add_teams(client, cid, h, count=8)
    team_count = len(tids)

    deleted = await client.request(
        "DELETE",
        contest_url(cid, ""),
        headers=h,
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
        assert len(teams_restored) == team_count


@pytest.mark.asyncio
async def test_patch_rules_json_before_start(stage_112_api):
    """[PATCH-RULES-JSON] Custom scoring rules persist and survive start."""
    client, sf, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Rules Persist")

    get0 = await _get_contest(client, cid, h)
    rules = get0["rules_json"]
    rules["scoring_rules"]["base_points"]["exact_score"] = 99
    rules["scoring_rules"]["bonuses"]["bonus_1_unique_multiplier_pct"] = 150

    patched = await client.patch(
        f"/api/v1/contests/{cid}",
        headers=h,
        json={"rules_json": rules},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["rules_json"]["scoring_rules"]["base_points"]["exact_score"] == 99

    await fulfill_start_prerequisites(client, cid, h)
    started = await _start_contest(client, cid, h)
    assert started.status_code == 200

    after = await _get_contest(client, cid, h)
    assert after["is_locked"] is True
    assert after["rules_json"]["scoring_rules"]["base_points"]["exact_score"] == 99
    assert after["rules_json"]["scoring_rules"]["bonuses"]["bonus_1_unique_multiplier_pct"] == 150

    async with sf() as session:
        row = await session.get(Contest, cid)
        assert row is not None
        assert row.rules_json["scoring_rules"]["base_points"]["exact_score"] == 99


@pytest.mark.asyncio
async def test_start_teams_incomplete(stage_112_api):
    """[START-TEAMS] start blocked when team count != total_teams."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Teams", total_teams=4)
    await add_teams(client, cid, h, count=1)
    await fulfill_start_prerequisites(client, cid, h, skip_teams=True)

    resp = await _start_contest(client, cid, h)
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "команд" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_start_participants_insufficient(stage_112_api):
    """[START-PARTICIPANTS] start blocked when fewer than 2 accepted participants."""
    client, _, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Start Parts", total_teams=4)
    await add_teams(client, cid, h, count=4)
    invited = await invite_participant(
        client, cid, h, email="only_one@example.com", login="only_one_user"
    )
    await complete_setup(client, invited["setup_url"], new_password=NEW_SECURE_PASSWORD)

    resp = await _start_contest(client, cid, h)
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert "участник" in resp.json()["detail"].lower()
