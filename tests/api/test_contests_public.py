"""Stage 1.8 — GET /contests/public (B2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from database.models import ContestLifecycleStatus
from tests.api.conftest import (
    API_PREFIX,
    _load_teams_csv,
    api_login,
    auth_header,
    contest_url,
)


async def _create_contest(client, headers, name: str) -> int:
    resp = await client.post(
        f"{API_PREFIX}/contests",
        headers=headers,
        json={"name": name, "total_teams": 16},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


async def _activate_contest(client, headers, contest_id: int) -> None:
    teams = await client.get(contest_url(contest_id, "/teams"), headers=headers)
    if not teams.json():
        for row in _load_teams_csv()[:2]:
            await client.post(
                contest_url(contest_id, "/teams"),
                headers=headers,
                json={"name": row["full_name"], "short_name": row["short_name"]},
            )
        teams = await client.get(contest_url(contest_id, "/teams"), headers=headers)
    tids = [t["id"] for t in teams.json()[:2]]
    now = datetime.now(timezone.utc)
    match_at = now + timedelta(days=7)
    deadline = (match_at - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(contest_id, "/admin/rounds"),
        headers=headers,
        json={
            "number": 1,
            "deadline": deadline,
            "matches": [
                {
                    "team1_id": tids[0],
                    "team2_id": tids[1],
                    "date_time": match_at.isoformat(),
                }
            ],
        },
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    activated = await client.post(
        contest_url(contest_id, f"/admin/rounds/{rid}/activate"),
        headers=headers,
    )
    assert activated.status_code == 200, activated.text


@pytest.mark.asyncio
async def test_public_list(empty_api):
    """[PUBLIC-LIST] Only RUNNING contests appear in public list."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    admin = await api_login(client, "admin_api")
    h_sup = auth_header(sup)
    h_admin = auth_header(admin)

    cid_draft = await _create_contest(client, h_sup, "Contest Draft")
    cid_running = await _create_contest(client, h_sup, "Contest Running")
    cid_paused = await _create_contest(client, h_sup, "Contest Paused")
    cid_finished = await _create_contest(client, h_sup, "Contest Finished")

    await _activate_contest(client, h_sup, cid_running)
    await _activate_contest(client, h_sup, cid_paused)
    await client.post(contest_url(cid_paused, "/pause"), headers=h_admin)
    await _activate_contest(client, h_sup, cid_finished)
    await client.post(contest_url(cid_finished, "/finish"), headers=h_admin)

    resp = await client.get(f"{API_PREFIX}/contests/public")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert cid_running in ids
    assert cid_draft not in ids
    assert cid_paused not in ids
    assert cid_finished not in ids
    for item in resp.json():
        assert item["status"] == ContestLifecycleStatus.RUNNING.value
        assert "name" in item


@pytest.mark.asyncio
async def test_public_no_auth(empty_api):
    """[PUBLIC-NO-AUTH] Public list works without Bearer token."""
    client, _, _ = empty_api
    resp = await client.get(f"{API_PREFIX}/contests/public")
    assert resp.status_code == 200
