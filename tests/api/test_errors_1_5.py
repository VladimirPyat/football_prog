"""Stage 1.5: HTTP error matrix [ERR-*]."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from database.models import Match
from tests.api.conftest import (
    API_PREFIX,
    DEFAULT_CONTEST_ID,
    _load_teams_csv,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round10_match_ids,
    get_round_id,
)


def assert_app_error(resp, *, status: int, code: str, detail_substr: str | None = None) -> dict:
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body.get("code") == code, body
    assert "detail" in body
    if detail_substr:
        assert detail_substr.lower() in body["detail"].lower()
    return body


@pytest.mark.asyncio
async def test_err_404_contest(loaded_contest_api):
    """[ERR-404-CONTEST] missing contest."""
    client, _, _ = loaded_contest_api
    sup = await api_login(client, "supervisor_api")
    resp = await client.get(contest_url(99999, ""), headers=auth_header(sup))
    assert_app_error(resp, status=404, code="NOT_FOUND")


@pytest.mark.asyncio
async def test_err_404_round_predictions(loaded_contest_api):
    """[ERR-404-ROUND] missing round."""
    client, _, _ = loaded_contest_api
    user = await api_login(client, "shutov")
    resp = await client.get(
        contest_url(DEFAULT_CONTEST_ID, "/rounds/99999/predictions"),
        headers=auth_header(user),
    )
    assert_app_error(resp, status=404, code="NOT_FOUND")


@pytest.mark.asyncio
async def test_err_401_no_auth(loaded_contest_api):
    """[ERR-401-NOAUTH] mutating without token."""
    client, _, _ = loaded_contest_api
    resp = await client.post(contest_url(DEFAULT_CONTEST_ID, "/admin/recalculate"))
    assert resp.status_code == 401
    assert "code" not in resp.json()


@pytest.mark.asyncio
async def test_err_403_pause_blocks_predictions(loaded_contest_api):
    """[ERR-403-PAUSE] predictions while PAUSED."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    user = await api_login(client, "shutov")
    await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=auth_header(admin))
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 403
    assert resp.json().get("code") in ("CONTEST_NOT_RUNNING", "CONTEST_RULE_VIOLATION")



@pytest.mark.asyncio
async def test_err_400_partial_batch(loaded_contest_api):
    """[ERR-400-BATCH] incomplete predictions."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": 1, "score1": 0, "score2": 0}]},
    )
    assert_app_error(resp, status=400, code="VALIDATION_ERROR")


@pytest.mark.asyncio
async def test_err_422_pydantic(loaded_contest_api):
    """[ERR-422-PYDANTIC] malformed body."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": 1}]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_err_400_grace_delete(loaded_contest_api):
    """[ERR-400-GRACE] delete without grace."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    admin = await api_login(client, "admin_api")
    h = auth_header(admin)
    await client.post(contest_url(DEFAULT_CONTEST_ID, "/pause"), headers=h)
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=h,
        json={"confirm": "DELETE"},
    )
    assert_app_error(resp, status=400, code="GRACE_PERIOD_ACTIVE")


@pytest.mark.asyncio
async def test_err_403_rbac_user_admin_endpoint(loaded_contest_api):
    """[ERR-403-RBAC] USER calls admin-only endpoint → 403, no code."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user = await api_login(client, "shutov")
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/admin/recalculate"),
        headers=auth_header(user),
    )
    assert resp.status_code == 403
    assert "code" not in resp.json()


@pytest.mark.asyncio
async def test_err_403_lock_post_team_after_activate(empty_api):
    """[ERR-403-LOCK] POST team after first activate → 403 CONTEST_LOCKED."""
    client, _, _ = empty_api
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": "Lock Teams 1.5", "total_teams": 16},
    )
    assert created.status_code == 200, created.text
    cid = created.json()["id"]
    for row in _load_teams_csv()[:16]:
        resp = await client.post(
            contest_url(cid, "/teams"),
            headers=h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )
        assert resp.status_code == 200, resp.text

    teams_resp = await client.get(contest_url(cid, "/teams"), headers=h)
    team_ids = [t["id"] for t in teams_resp.json()[:2]]
    now = datetime.now(timezone.utc)
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
                    "team1_id": team_ids[0],
                    "team2_id": team_ids[1],
                    "date_time": match_at.isoformat(),
                }
            ],
        },
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    await client.post(contest_url(cid, f"/admin/rounds/{rid}/activate"), headers=h)

    locked = await client.post(
        contest_url(cid, "/teams"),
        headers=h,
        json={"name": "Extra", "short_name": "XTR"},
    )
    assert_app_error(locked, status=403, code="CONTEST_LOCKED")


@pytest.mark.asyncio
async def test_err_422_score_out_of_range(loaded_contest_api):
    """[ERR-422-SCORE] PUT match result score=99 → 422 SCORE_OUT_OF_RANGE."""
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)

    async with sf() as session:
        match = await session.scalar(
            select(Match).where(
                Match.round_id == rid,
                Match.status == "FINISHED",
            ).limit(1)
        )
        assert match is not None
        mid = match.id

    resp = await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/matches/{mid}/result"),
        headers=h,
        json={"score1": 99, "score2": 0},
    )
    assert_app_error(resp, status=422, code="SCORE_OUT_OF_RANGE")


@pytest.mark.asyncio
async def test_err_409_lifecycle_pause_draft(empty_api):
    """[ERR-409-LIFECYCLE] pause DRAFT contest → 409 ILLEGAL_TRANSITION."""
    client, _, _ = empty_api
    admin = await api_login(client, "admin_api")
    h = auth_header(admin)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=auth_header(await api_login(client, "supervisor_api")),
        json={"name": "Lifecycle 1.5"},
    )
    assert created.status_code == 200, created.text
    cid = created.json()["id"]
    resp = await client.post(contest_url(cid, "/pause"), headers=h)
    assert_app_error(resp, status=409, code="ILLEGAL_TRANSITION")


@pytest.mark.asyncio
async def test_log_info_predictions(caplog, loaded_contest_api):
    """[LOG-INFO-PRED] successful POST predictions emits INFO log."""
    caplog.set_level(logging.INFO)
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10, DEFAULT_CONTEST_ID)
    mids = await get_round10_match_ids(sf, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/rounds/{rid}/predictions"),
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 200, resp.text
    assert any(r.levelname == "INFO" for r in caplog.records)


@pytest.mark.asyncio
async def test_log_info_calculate(caplog, loaded_contest_api):
    """[LOG-INFO-CALC] successful calculate round emits INFO log."""
    caplog.set_level(logging.INFO)
    client, sf, _ = loaded_contest_api
    await ensure_contest_running(sf, client, DEFAULT_CONTEST_ID)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    rid = await get_round_id(sf, 1, DEFAULT_CONTEST_ID)
    resp = await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    assert any(r.levelname == "INFO" for r in caplog.records)
