"""[FIX-B7/B8] Stage 1.10 — per-contest UNIQUE isolation after legacy index drop."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.api.conftest import (
    API_PREFIX,
    _load_teams_csv,
    api_login,
    auth_header,
    contest_url,
)


async def _create_running_contest_with_teams(client, h, *, name: str) -> tuple[int, list[int]]:
    """Create contest, add two teams, activate round 1 → RUNNING."""
    resp = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": name, "total_teams": 16},
    )
    assert resp.status_code == 200, resp.text
    cid = resp.json()["id"]

    teams: list[int] = []
    for row in _load_teams_csv()[:2]:
        tr = await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )
        assert tr.status_code == 200, tr.text
        teams.append(tr.json()["id"])

    now = datetime.now(UTC)
    match_at = now + timedelta(days=7)
    deadline = (match_at - timedelta(hours=25)).isoformat()
    rnd = await client.post(
        contest_url(cid, "/admin/rounds"),
        headers=h,
        json={
            "number": 1,
            "deadline": deadline,
            "matches": [
                {
                    "team1_id": teams[0],
                    "team2_id": teams[1],
                    "date_time": match_at.isoformat(),
                }
            ],
        },
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    act = await client.post(contest_url(cid, f"/admin/rounds/{rid}/activate"), headers=h)
    assert act.status_code == 200, act.text
    return cid, teams


@pytest.mark.asyncio
async def test_fix_b7_round_cross_contest(empty_api):
    """[FIX-B7-ROUND] Round number=1 allowed in contest B when contest A has number=1."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    await _create_running_contest_with_teams(client, h, name="Contest A")
    cid_b, _ = await _create_running_contest_with_teams(client, h, name="Contest B")
    assert cid_b > 1


@pytest.mark.asyncio
async def test_fix_b7_dup_in_contest(empty_api):
    """[FIX-B7-DUP-IN-CONTEST] Duplicate round number in same contest → 400."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    cid, teams = await _create_running_contest_with_teams(client, h, name="Contest Dup Round")

    now = datetime.now(UTC)
    match_at = now + timedelta(days=14)
    deadline = (match_at - timedelta(hours=25)).isoformat()
    dup = await client.post(
        contest_url(cid, "/admin/rounds"),
        headers=h,
        json={
            "number": 1,
            "deadline": deadline,
            "matches": [
                {
                    "team1_id": teams[0],
                    "team2_id": teams[1],
                    "date_time": match_at.isoformat(),
                }
            ],
        },
    )
    assert dup.status_code == 400, dup.text
    assert dup.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_fix_b8_team_cross_contest(empty_api):
    """[FIX-B8-TEAM] Same team name allowed in contest B when contest A has it."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    ca = await client.post(f"{API_PREFIX}/contests", headers=h, json={"name": "Contest A"})
    cb = await client.post(f"{API_PREFIX}/contests", headers=h, json={"name": "Contest B"})
    cid_a, cid_b = ca.json()["id"], cb.json()["id"]

    team_name = "E2E Team 1"
    ta = await client.post(
        contest_url(cid_a, "/teams"),
        headers=h,
        json={"name": team_name, "short_name": "E2E1"},
    )
    assert ta.status_code == 200, ta.text

    tb = await client.post(
        contest_url(cid_b, "/teams"),
        headers=h,
        json={"name": team_name, "short_name": "E2E1"},
    )
    assert tb.status_code == 200, tb.text
    assert tb.json()["name"] == team_name


@pytest.mark.asyncio
async def test_fix_b8_dup_in_contest(empty_api):
    """[FIX-B8-DUP-IN-CONTEST] Duplicate team name in same contest → 400."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)

    c = await client.post(f"{API_PREFIX}/contests", headers=h, json={"name": "Contest Dup Team"})
    cid = c.json()["id"]

    team_name = "Duplicate FC"
    first = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": team_name, "short_name": "DUP"},
    )
    assert first.status_code == 200, first.text

    dup = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": team_name, "short_name": "DUP2"},
    )
    assert dup.status_code == 400, dup.text
    assert dup.json()["code"] == "VALIDATION_ERROR"
