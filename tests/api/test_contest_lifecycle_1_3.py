"""[API-CS-*] [API-TB-*] [API-CONTEST-*] immutability, tie-break, lifecycle."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from database.models import Contest, ContestLifecycleStatus, Match, Round, User
from tests.api.conftest import (
    API_PREFIX,
    DEFAULT_CONTEST_ID,
    api_login,
    auth_header,
    contest_url,
    ensure_contest_running,
    get_round_id,
    reset_contest_unlocked,
    set_round_draft,
)


@pytest.mark.asyncio
async def test_contest_settings_get(loaded_api):
    """[API-CS-GET] SUPERVISOR GET settings → status, is_locked."""
    client, _, _ = loaded_api
    sup = await api_login(client, "supervisor_api")
    resp = await client.get(
        f"{API_PREFIX}/admin/contest-settings",
        headers=auth_header(sup),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "is_locked" in data


@pytest.mark.asyncio
async def test_contest_patch_unlocked(loaded_api):
    """[API-CS-PATCH-UNLOCKED] PATCH rules before activate → 200."""
    client, sf, _ = loaded_api
    await reset_contest_unlocked(sf)
    sup = await api_login(client, "supervisor_api")
    resp = await client.patch(
        f"{API_PREFIX}/admin/contest-settings",
        headers=auth_header(sup),
        json={"total_teams": 16},
    )
    assert resp.status_code == 200
    assert resp.json()["total_teams"] == 16


@pytest.mark.asyncio
async def test_contest_patch_locked(loaded_api):
    """[API-CS-PATCH-LOCKED] after activate PATCH → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    resp = await client.patch(
        f"{API_PREFIX}/admin/contest-settings",
        headers=auth_header(sup),
        json={"total_teams": 15},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contest_activate_locks(loaded_api):
    """[API-CS-ACTIVATE] first activate → is_locked, RUNNING."""
    client, sf, _ = loaded_api
    await set_round_draft(sf, 10)
    await reset_contest_unlocked(sf)
    sup = await api_login(client, "supervisor_api")
    rid = await get_round_id(sf, 10)
    resp = await client.post(
        f"{API_PREFIX}/admin/rounds/{rid}/activate",
        headers=auth_header(sup),
    )
    assert resp.status_code == 200

    settings = await client.get(
        f"{API_PREFIX}/admin/contest-settings",
        headers=auth_header(sup),
    )
    assert settings.json()["is_locked"] is True
    assert settings.json()["status"] == ContestLifecycleStatus.RUNNING.value


@pytest.mark.asyncio
async def test_tiebreak_set_and_locked(loaded_api):
    """[API-TB-SET] [API-TB-LOCKED] ADMIN set points when locked → 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")

    async with sf() as session:
        uid = (
            await session.scalar(select(User.id).where(User.login == "shutov"))
        )

    resp = await client.put(
        f"{API_PREFIX}/admin/users/{uid}/exceptional-tiebreak",
        headers=auth_header(admin),
        json={"points": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["exceptional_tiebreak_points"] == 5


@pytest.mark.asyncio
async def test_tiebreak_rbac(loaded_api):
    """[API-TB-RBAC] SUPERVISOR cannot set → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    async with sf() as session:
        uid = await session.scalar(select(User.id).where(User.login == "shutov"))
    resp = await client.put(
        f"{API_PREFIX}/admin/users/{uid}/exceptional-tiebreak",
        headers=auth_header(sup),
        json={"points": 1},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_tiebreak_display_on_leaderboard(loaded_api):
    """[API-TB-DISPLAY] leaderboard includes exceptional_tiebreak_points."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    sup = await api_login(client, "supervisor_api")
    admin = await api_login(client, "admin_api")
    sup_h = auth_header(sup)
    rid = await get_round_id(sf, 1)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/calculate"),
        headers=sup_h,
    )
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, f"/admin/rounds/{rid}/publish"),
        headers=sup_h,
    )
    async with sf() as session:
        uid = await session.scalar(select(User.id).where(User.login == "shutov"))
    await client.put(
        contest_url(DEFAULT_CONTEST_ID, f"/participants/{uid}/exceptional-tiebreak"),
        headers=auth_header(admin),
        json={"points": 3},
    )
    lb = await client.get(contest_url(DEFAULT_CONTEST_ID, "/leaderboard"))
    assert lb.status_code == 200
    row = next(r for r in lb.json()["leaderboard"] if r["user_id"] == uid)
    assert row["exceptional_tiebreak_points"] == 3


@pytest.mark.asyncio
async def test_tiebreak_rank_synthetic(stage_112_api):
    """[API-TB-RANK] higher exceptional points rank above on synthetic tie."""
    from datetime import UTC, datetime, timedelta

    from database.models import Round

    from tests.api.stage_112_helpers import (
        NEW_SECURE_PASSWORD,
        activate_first_round,
        add_teams,
        complete_setup,
        create_draft_contest,
        invite_participant,
    )
    from tests.api.test_contest_start_1_15 import _start_contest

    client, sf, _ = stage_112_api
    cid, sup_h = await create_draft_contest(client, name="Tiebreak Synthetic")
    tids = await add_teams(client, cid, sup_h)

    inv_a = await invite_participant(
        client, cid, sup_h, email="tie_a@example.com", login="tie_user_a"
    )
    inv_b = await invite_participant(
        client, cid, sup_h, email="tie_b@example.com", login="tie_user_b"
    )
    await complete_setup(client, inv_a["setup_url"])
    await complete_setup(client, inv_b["setup_url"])

    await _start_contest(client, cid, sup_h)
    rid = await activate_first_round(client, cid, sup_h, tids)

    async with sf() as session:
        matches = (
            await session.scalars(
                select(Match).where(Match.round_id == rid).order_by(Match.id)
            )
        ).all()
        mids = [m.id for m in matches]

    preds = [{"match_id": mid, "score1": 1, "score2": 0} for mid in mids]
    for login in ("tie_user_a", "tie_user_b"):
        token = await api_login(client, login, NEW_SECURE_PASSWORD)
        resp = await client.post(
            contest_url(cid, f"/rounds/{rid}/predictions"),
            headers=auth_header(token),
            json={"predictions": preds},
        )
        assert resp.status_code == 200, resp.text

    async with sf() as session:
        async with session.begin():
            round_ = await session.get(Round, rid)
            assert round_ is not None
            round_.deadline = datetime.now(UTC) - timedelta(hours=1)

    close = await client.post(
        contest_url(cid, f"/admin/rounds/{rid}/close"),
        headers=sup_h,
    )
    assert close.status_code == 200

    for mid in mids:
        res = await client.put(
            contest_url(cid, f"/admin/matches/{mid}/result"),
            headers=sup_h,
            json={"score1": 1, "score2": 0},
        )
        assert res.status_code == 200

    calc = await client.post(
        contest_url(cid, f"/admin/rounds/{rid}/calculate"),
        headers=sup_h,
    )
    assert calc.status_code == 200

    pub = await client.post(
        contest_url(cid, f"/admin/rounds/{rid}/publish"),
        headers=sup_h,
    )
    assert pub.status_code == 200

    admin = await api_login(client, "admin_api")
    admin_h = auth_header(admin)
    await client.put(
        contest_url(cid, f"/participants/{inv_a['user_id']}/exceptional-tiebreak"),
        headers=admin_h,
        json={"points": 10},
    )
    await client.put(
        contest_url(cid, f"/participants/{inv_b['user_id']}/exceptional-tiebreak"),
        headers=admin_h,
        json={"points": 0},
    )

    lb = await client.get(contest_url(cid, "/leaderboard"))
    assert lb.status_code == 200
    rows = {r["user_id"]: r["rank"] for r in lb.json()["leaderboard"]}
    assert rows[inv_a["user_id"]] < rows[inv_b["user_id"]]


@pytest.mark.asyncio
async def test_contest_pause_resume(loaded_api):
    """[API-CONTEST-PAUSE] [API-CONTEST-RESUME] lifecycle transitions."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    headers = auth_header(admin)

    pause = await client.post(f"{API_PREFIX}/admin/contest/pause", headers=headers)
    assert pause.status_code == 200
    assert pause.json()["status"] == ContestLifecycleStatus.PAUSED.value
    assert pause.json()["paused_at"] is not None

    resume = await client.post(f"{API_PREFIX}/admin/contest/resume", headers=headers)
    assert resume.status_code == 200
    assert resume.json()["status"] == ContestLifecycleStatus.RUNNING.value


@pytest.mark.asyncio
async def test_contest_pause_blocks_predictions(loaded_api):
    """[API-CONTEST-PAUSE-BLOCK] predictions while PAUSED → 403."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    user = await api_login(client, "shutov")
    await client.post(f"{API_PREFIX}/admin/contest/pause", headers=auth_header(admin))

    from tests.api.conftest import get_round10_match_ids

    rid = await get_round_id(sf, 10)
    mids = await get_round10_match_ids(sf)
    resp = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 1, "score2": 0} for m in mids]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contest_finish(loaded_api):
    """[API-CONTEST-FINISH] finish → predictions 403; public GET 200."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    await client.post(f"{API_PREFIX}/admin/contest/finish", headers=auth_header(admin))

    user = await api_login(client, "shutov")
    rid = await get_round_id(sf, 10)
    from tests.api.conftest import get_round10_match_ids

    mids = await get_round10_match_ids(sf)
    pred = await client.post(
        f"{API_PREFIX}/rounds/{rid}/predictions",
        headers=auth_header(user),
        json={"predictions": [{"match_id": m, "score1": 0, "score2": 0} for m in mids]},
    )
    assert pred.status_code == 403

    lb = await client.get(f"{API_PREFIX}/leaderboard")
    assert lb.status_code == 200


@pytest.mark.asyncio
async def test_contest_finish_idempotent(loaded_api):
    """[API-CONTEST-FINISH-IDEM] second finish → 200 no-op."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    h = auth_header(admin)
    await client.post(f"{API_PREFIX}/admin/contest/finish", headers=h)
    again = await client.post(f"{API_PREFIX}/admin/contest/finish", headers=h)
    assert again.status_code == 200


@pytest.mark.asyncio
async def test_contest_delete_rbac(delete_api):
    """[API-CONTEST-DELETE-RBAC] SUPERVISOR DELETE → 403."""
    client, sf, _ = delete_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    await client.post(f"{API_PREFIX}/admin/contest/pause", headers=auth_header(admin))

    sup = await api_login(client, "supervisor_api")
    resp = await client.request(
        "DELETE",
        f"{API_PREFIX}/admin/contest",
        headers=auth_header(sup),
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contest_delete_no_grace(loaded_api):
    """[API-CONTEST-DELETE-NOGRACE] instant=false → 400 right after pause."""
    client, sf, _ = loaded_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    await client.post(f"{API_PREFIX}/admin/contest/pause", headers=auth_header(admin))

    resp = await client.request(
        "DELETE",
        f"{API_PREFIX}/admin/contest",
        headers=auth_header(admin),
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_contest_delete_bad_confirm(delete_api):
    """[API-CONTEST-DELETE-BADCONFIRM] wrong confirm → 400/422."""
    client, sf, _ = delete_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    await client.post(f"{API_PREFIX}/admin/contest/pause", headers=auth_header(admin))
    resp = await client.request(
        "DELETE",
        f"{API_PREFIX}/admin/contest",
        headers=auth_header(admin),
        json={"confirm": "NOPE"},
    )
    assert resp.status_code in (400, 422), resp.text


@pytest.mark.asyncio
async def test_contest_delete_ok(delete_api):
    """[API-CONTEST-DELETE-OK] soft-delete → DELETED response; DB DRAFT + deleted_at; data wiped."""
    from sqlalchemy import func

    from database.models import ContestParticipant, Team

    client, sf, _ = delete_api
    await ensure_contest_running(sf, client)
    admin = await api_login(client, "admin_api")
    admin_h = auth_header(admin)
    await client.post(
        contest_url(DEFAULT_CONTEST_ID, "/pause"),
        headers=admin_h,
    )
    resp = await client.request(
        "DELETE",
        contest_url(DEFAULT_CONTEST_ID, ""),
        headers=admin_h,
        json={"confirm": "DELETE"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "DELETED"
    assert body["deleted"] is True

    async with sf() as session:
        contest = await session.get(Contest, DEFAULT_CONTEST_ID)
        assert contest is not None
        assert contest.status == ContestLifecycleStatus.DRAFT.value
        assert contest.deleted_at is not None
        assert contest.is_locked is False
        round_count = await session.scalar(
            select(func.count()).select_from(Round).where(Round.contest_id == DEFAULT_CONTEST_ID)
        )
        team_count = await session.scalar(
            select(func.count()).select_from(Team).where(Team.contest_id == DEFAULT_CONTEST_ID)
        )
        part_count = await session.scalar(
            select(func.count())
            .select_from(ContestParticipant)
            .where(ContestParticipant.contest_id == DEFAULT_CONTEST_ID)
        )
        assert round_count == 0
        assert team_count == 0
        assert part_count == 0

    deleted = await client.get(f"{API_PREFIX}/contests/deleted", headers=admin_h)
    assert deleted.status_code == 200
    assert any(row["id"] == DEFAULT_CONTEST_ID for row in deleted.json())
