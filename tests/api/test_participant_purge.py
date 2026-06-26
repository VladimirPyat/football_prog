"""Stage 1.12 — purge unconfirmed participants on contest start."""

from __future__ import annotations

import pytest
from tests.api.stage_112_helpers import (
    NEW_SECURE_PASSWORD,
    activate_first_round,
    add_teams,
    complete_setup,
    create_draft_contest,
    invite_participant,
    participant_status,
    user_exists,
)

from database.models import Contest, ContestLifecycleStatus


@pytest.mark.asyncio
async def test_purge_on_start(stage_112_api):
    """[PURGE-ON-START] PENDING unconfirmed removed; ACCEPTED kept when contest goes RUNNING."""
    client, sf, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Purge Flow")
    pending = await invite_participant(
        client, cid, h, email="pending@example.com", login="pending_user"
    )
    accepted = await invite_participant(
        client, cid, h, email="accepted@example.com", login="accepted_user"
    )
    await complete_setup(client, accepted["setup_url"], new_password=NEW_SECURE_PASSWORD)

    tids = await add_teams(client, cid, h)
    await activate_first_round(client, cid, h, tids)

    parts = await client.get(f"/api/v1/contests/{cid}/participants", headers=h)
    assert parts.status_code == 200
    user_ids = {p["user_id"] for p in parts.json()}
    assert pending["user_id"] not in user_ids
    assert accepted["user_id"] in user_ids
    accepted_row = next(p for p in parts.json() if p["user_id"] == accepted["user_id"])
    assert accepted_row["status"] == "ACCEPTED"

    assert await user_exists(sf, pending["user_id"]) is False
    assert await user_exists(sf, accepted["user_id"]) is True

    async with sf() as session:
        contest = await session.get(Contest, cid)
        assert contest is not None
        assert contest.status == ContestLifecycleStatus.RUNNING.value


@pytest.mark.asyncio
async def test_purge_pending_temp(stage_112_api):
    """[PURGE-PENDING-TEMP] PENDING + is_temp_password participant is removed."""
    client, sf, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Purge Pending")
    pending = await invite_participant(
        client, cid, h, email="pt@example.com", login="pt_user"
    )
    tids = await add_teams(client, cid, h)
    await activate_first_round(client, cid, h, tids)

    assert await participant_status(sf, cid, pending["user_id"]) is None
    assert await user_exists(sf, pending["user_id"]) is False


@pytest.mark.asyncio
async def test_purge_accepted_kept(stage_112_api):
    """[PURGE-ACCEPTED] ACCEPTED participant survives contest start."""
    client, sf, _ = stage_112_api
    cid, h = await create_draft_contest(client, name="Purge Accepted")
    accepted = await invite_participant(
        client, cid, h, email="keep@example.com", login="keep_user"
    )
    await complete_setup(client, accepted["setup_url"], new_password=NEW_SECURE_PASSWORD)
    tids = await add_teams(client, cid, h)
    await activate_first_round(client, cid, h, tids)

    status = await participant_status(sf, cid, accepted["user_id"])
    assert status == "ACCEPTED"
    assert await user_exists(sf, accepted["user_id"]) is True


@pytest.mark.asyncio
async def test_purge_multi_contest(stage_112_api):
    """[PURGE-MULTI-CONTEST] PENDING in C1 removed; user kept when ACCEPTED in C2."""
    from database.models import ContestParticipant, ParticipantStatus

    client, sf, _ = stage_112_api
    c1, h = await create_draft_contest(client, name="Contest One")
    c2, _ = await create_draft_contest(client, name="Contest Two")

    c2_invite = await invite_participant(
        client, c2, h, email="multi@example.com", login="multi_user"
    )
    await complete_setup(client, c2_invite["setup_url"], new_password=NEW_SECURE_PASSWORD)

    async with sf() as session:
        async with session.begin():
            session.add(
                ContestParticipant(
                    contest_id=c1,
                    user_id=c2_invite["user_id"],
                    status=ParticipantStatus.PENDING,
                )
            )

    pending_only = await invite_participant(
        client, c1, h, email="solo@example.com", login="solo_pending"
    )

    tids = await add_teams(client, c1, h)
    await activate_first_round(client, c1, h, tids)

    assert await participant_status(sf, c1, c2_invite["user_id"]) is None
    assert await participant_status(sf, c2, c2_invite["user_id"]) == "ACCEPTED"
    assert await user_exists(sf, c2_invite["user_id"]) is True

    assert await participant_status(sf, c1, pending_only["user_id"]) is None
    assert await user_exists(sf, pending_only["user_id"]) is False
