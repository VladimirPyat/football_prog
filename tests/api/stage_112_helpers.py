"""Shared helpers for Stage 1.12 API tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.api.conftest import (
    API_PREFIX,
    _load_teams_csv,
    api_login,
    auth_header,
    contest_url,
)

from database.models import ContestParticipant, User

STAGE_112_ENV = {
    "ENFORCE_PASSWORD_SETUP": "true",
    "SUPERVISOR_TRAINING_MODE": "true",
    "CONTEST_DELETE_GRACE_SECONDS": "0",
    "CONTEST_RESTORE_WINDOW_SECONDS": "3600",
    "FRONTEND_BASE_URL": "http://127.0.0.1:3000",
}

NEW_SECURE_PASSWORD = "NewSecure1!"


def extract_setup_token(setup_url: str) -> str:
    token = parse_qs(urlparse(setup_url).query).get("token")
    assert token, f"token missing in setup_url: {setup_url}"
    return token[0]


def apply_env(monkeypatch: pytest.MonkeyPatch, overrides: dict[str, str] | None = None) -> None:
    env = {**STAGE_112_ENV, **(overrides or {})}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    from config.settings import get_settings

    get_settings.cache_clear()


async def create_draft_contest(
    client: httpx.AsyncClient,
    *,
    name: str = "Stage 1.12",
    total_teams: int = 16,
) -> tuple[int, dict[str, str]]:
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    created = await client.post(
        f"{API_PREFIX}/contests",
        headers=h,
        json={"name": name, "total_teams": total_teams},
    )
    assert created.status_code == 200, created.text
    return created.json()["id"], h


async def fulfill_start_prerequisites(
    client: httpx.AsyncClient,
    contest_id: int,
    sup_h: dict[str, str],
    *,
    team_count: int | None = None,
    accepted_participants: int = 2,
    skip_teams: bool = False,
) -> None:
    """Add all teams and accepted participants required for POST /start."""
    if not skip_teams:
        if team_count is None:
            contest = await client.get(f"{API_PREFIX}/contests/{contest_id}", headers=sup_h)
            assert contest.status_code == 200, contest.text
            team_count = contest.json()["total_teams"]
        await add_teams(client, contest_id, sup_h, count=team_count)
    for i in range(accepted_participants):
        invited = await invite_participant(
            client,
            contest_id,
            sup_h,
            email=f"start_ready_{contest_id}_{i}@example.com",
            login=f"start_ready_{contest_id}_{i}",
        )
        await complete_setup(client, invited["setup_url"])


async def invite_participant(
    client: httpx.AsyncClient,
    contest_id: int,
    sup_h: dict[str, str],
    *,
    email: str,
    login: str,
    first_name: str = "Test",
    last_name: str = "User",
) -> dict:
    resp = await client.post(
        contest_url(contest_id, "/participants"),
        headers=sup_h,
        json={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "login": login,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def complete_setup(
    client: httpx.AsyncClient,
    setup_url: str,
    *,
    new_password: str = NEW_SECURE_PASSWORD,
) -> dict:
    token = extract_setup_token(setup_url)
    resp = await client.post(
        f"{API_PREFIX}/auth/complete-setup",
        json={"token": token, "new_password": new_password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def add_teams(client: httpx.AsyncClient, contest_id: int, sup_h: dict[str, str], count: int = 16) -> list[int]:
    tids: list[int] = []
    for row in _load_teams_csv()[:count]:
        t = await client.post(
            contest_url(contest_id, "/teams"),
            headers=sup_h,
            json={"name": row["full_name"], "short_name": row["short_name"]},
        )
        assert t.status_code == 200, t.text
        tids.append(t.json()["id"])
    return tids


async def activate_first_round(
    client: httpx.AsyncClient,
    contest_id: int,
    sup_h: dict[str, str],
    tids: list[int],
) -> int:
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
        contest_url(contest_id, "/admin/rounds"),
        headers=sup_h,
        json={"number": 1, "deadline": deadline, "matches": matches},
    )
    assert rnd.status_code == 200, rnd.text
    rid = rnd.json()["round_id"]
    act = await client.post(
        contest_url(contest_id, f"/admin/rounds/{rid}/activate"),
        headers=sup_h,
    )
    assert act.status_code == 200, act.text
    return rid


async def force_contest_running(
    sf: async_sessionmaker[AsyncSession],
    contest_id: int,
    round_id: int,
) -> None:
    """Set round ACTIVE + contest RUNNING without API activate (prediction-guard tests)."""
    from database.models import Contest, ContestLifecycleStatus, Round, RoundStatus

    async with sf() as session:
        async with session.begin():
            contest = await session.get(Contest, contest_id)
            round_ = await session.get(Round, round_id)
            assert contest is not None and round_ is not None
            round_.status = RoundStatus.ACTIVE.value
            contest.is_locked = True
            contest.status = ContestLifecycleStatus.RUNNING.value


async def login_raw(client: httpx.AsyncClient, login: str, password: str) -> httpx.Response:
    return await client.post(
        f"{API_PREFIX}/auth/login",
        json={"login": login, "password": password},
    )


async def participant_status(
    sf: async_sessionmaker[AsyncSession],
    contest_id: int,
    user_id: int,
) -> str | None:
    async with sf() as session:
        row = await session.get(ContestParticipant, (contest_id, user_id))
        return row.status if row else None


async def user_exists(sf: async_sessionmaker[AsyncSession], user_id: int) -> bool:
    async with sf() as session:
        return await session.get(User, user_id) is not None
