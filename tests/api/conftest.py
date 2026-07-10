"""Fixtures for Stage 1.3/1.4 HTTP API tests (loader DB + empty DB + E2E helpers)."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for _p in (str(_ROOT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.security import hash_password
from database.base import Base
from database.models import (
    Contest,
    ContestLifecycleStatus,
    Match,
    Round,
    RoundStatus,
    User,
    UserRole,
)
from scripts.load_test_data import run_load

TEST_PASSWORD = "testpass123"
API_PREFIX = "/api/v1"
DEFAULT_CONTEST_ID = 1
PROJECT_ROOT = _ROOT
CONTRACTED = PROJECT_ROOT / "docs" / "test_data" / "contracted"
CONTEST_DEFAULTS = PROJECT_ROOT / "docs" / "test_data" / "config" / "contest_defaults.json"
DT_FORMAT = "%d.%m.%Y|%H:%M"


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def contest_url(contest_id: int, path: str) -> str:
    base = f"{API_PREFIX}/contests/{contest_id}"
    if not path or path == "/":
        return f"{base}/"
    if not path.startswith("/"):
        path = f"/{path}"
    return base + path


async def api_login(client: httpx.AsyncClient, login: str, password: str = TEST_PASSWORD) -> str:
    resp = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"login": login, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def get_contest_id(sf: async_sessionmaker[AsyncSession], contest_id: int = DEFAULT_CONTEST_ID) -> int:
    async with sf() as session:
        contest = await session.get(Contest, contest_id)
        assert contest is not None, f"Contest {contest_id} missing"
        return contest.id


async def _seed_test_users(sf: async_sessionmaker[AsyncSession]) -> None:
    async with sf() as session:
        async with session.begin():
            all_users = (await session.scalars(select(User))).all()
            for user in all_users:
                user.password_hash = hash_password(TEST_PASSWORD)

            for login, role in [("admin_api", UserRole.SUPPORT), ("supervisor_api", UserRole.SUPERVISOR)]:
                existing = await session.scalar(select(User).where(User.login == login))
                if existing is None:
                    session.add(
                        User(
                            login=login,
                            password_hash=hash_password(TEST_PASSWORD),
                            role=role.value,
                            first_name="",
                            last_name=login,
                            is_temp_password=False,
                        )
                    )
                else:
                    existing.role = role.value

            temp = await session.scalar(select(User).where(User.login == "temp_user"))
            if temp is None:
                session.add(
                    User(
                        login="temp_user",
                        password_hash=hash_password(TEST_PASSWORD),
                        role=UserRole.USER.value,
                        first_name="",
                        last_name="temp",
                        is_temp_password=True,
                    )
                )
            else:
                temp.is_temp_password = True


async def _shift_round10_forward(sf: async_sessionmaker[AsyncSession], contest_id: int = DEFAULT_CONTEST_ID) -> None:
    async with sf() as session:
        async with session.begin():
            round_ = await session.scalar(
                select(Round).where(Round.contest_id == contest_id, Round.number == 10)
            )
            if round_ is None:
                return
            matches = (
                await session.scalars(select(Match).where(Match.round_id == round_.id))
            ).all()
            base = datetime.now(timezone.utc) + timedelta(days=14)
            for i, match in enumerate(sorted(matches, key=lambda m: m.id)):
                match.date_time = base + timedelta(hours=i)
            earliest = min(m.date_time for m in matches)
            round_.deadline = earliest - timedelta(days=3)
            round_.status = RoundStatus.ACTIVE.value


async def get_round_id(
    sf: async_sessionmaker[AsyncSession],
    number: int,
    contest_id: int = DEFAULT_CONTEST_ID,
) -> int:
    async with sf() as session:
        round_ = await session.scalar(
            select(Round).where(Round.contest_id == contest_id, Round.number == number)
        )
        assert round_ is not None, f"Round {number} missing for contest {contest_id}"
        return round_.id


async def get_round10_match_ids(
    sf: async_sessionmaker[AsyncSession],
    contest_id: int = DEFAULT_CONTEST_ID,
) -> list[int]:
    async with sf() as session:
        round_ = await session.scalar(
            select(Round).where(Round.contest_id == contest_id, Round.number == 10)
        )
        assert round_ is not None
        matches = (
            await session.scalars(
                select(Match).where(Match.round_id == round_.id).order_by(Match.id)
            )
        ).all()
        return [m.id for m in matches]


async def reset_contest_unlocked(
    sf: async_sessionmaker[AsyncSession],
    contest_id: int = DEFAULT_CONTEST_ID,
) -> None:
    async with sf() as session:
        async with session.begin():
            contest = await session.get(Contest, contest_id)
            if contest:
                contest.is_locked = False
                contest.status = ContestLifecycleStatus.DRAFT.value


async def set_round_draft(
    sf: async_sessionmaker[AsyncSession],
    number: int,
    contest_id: int = DEFAULT_CONTEST_ID,
) -> int:
    async with sf() as session:
        async with session.begin():
            round_ = await session.scalar(
                select(Round).where(Round.contest_id == contest_id, Round.number == number)
            )
            assert round_ is not None
            round_.status = RoundStatus.DRAFT.value
            return round_.id


async def ensure_contest_running(
    sf: async_sessionmaker[AsyncSession],
    client: httpx.AsyncClient,
    contest_id: int = DEFAULT_CONTEST_ID,
) -> None:
    """Activate round 10 if contest not yet RUNNING (idempotent)."""
    async with sf() as session:
        contest = await session.get(Contest, contest_id)
        if (
            contest
            and contest.status == ContestLifecycleStatus.RUNNING.value
            and contest.is_locked
        ):
            return

    rid = await set_round_draft(sf, 10, contest_id)
    await reset_contest_unlocked(sf, contest_id)
    sup = await api_login(client, "supervisor_api")
    resp = await client.post(
        contest_url(contest_id, f"/admin/rounds/{rid}/activate"),
        headers=auth_header(sup),
    )
    if resp.status_code == 400 and "ACTIVE → ACTIVE" in resp.text:
        async with sf() as session:
            async with session.begin():
                contest = await session.get(Contest, contest_id)
                round_ = await session.get(Round, rid)
                if contest and round_ and round_.status == RoundStatus.ACTIVE.value:
                    contest.is_locked = True
                    contest.status = ContestLifecycleStatus.RUNNING.value
        return
    assert resp.status_code == 200, resp.text


def _load_contest_defaults() -> dict:
    with CONTEST_DEFAULTS.open(encoding="utf-8") as fh:
        return json.load(fh)


def _parse_match_dt(value: str) -> datetime:
    return datetime.strptime(value.strip(), DT_FORMAT).replace(tzinfo=timezone.utc)


def _load_teams_csv() -> list[dict[str, str]]:
    with (CONTRACTED / "teams.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_users_csv() -> list[dict[str, str]]:
    with (CONTRACTED / "users.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def _load_matches_csv() -> dict[int, list[dict[str, str]]]:
    with (CONTRACTED / "matches.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["round_number"])].append(row)
    return dict(grouped)


def _load_predictions_csv() -> dict[tuple[int, str], list[dict[str, str]]]:
    with (CONTRACTED / "predictions.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    grouped: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (int(row["round_number"]), row["user_login"].strip())
        grouped[key].append(row)
    return grouped


async def _invite_and_set_password(
    client: httpx.AsyncClient,
    contest_id: int,
    sup_h: dict[str, str],
    *,
    email: str,
    first_name: str,
    last_name: str,
    login: str | None = None,
) -> str:
    payload: dict[str, str] = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }
    if login:
        payload["login"] = login
    resp = await client.post(
        contest_url(contest_id, "/participants"),
        headers=sup_h,
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    user_login = data["login"]
    temp_pw = data["temp_password"]
    token = await api_login(client, user_login, temp_pw)
    change = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(token),
        json={"old_password": temp_pw, "new_password": TEST_PASSWORD},
    )
    assert change.status_code == 200, change.text
    return user_login


async def build_contracted_contest_via_http(
    client: httpx.AsyncClient,
    sf: async_sessionmaker[AsyncSession],
    *,
    rounds: range | None = None,
    calculate: bool = True,
) -> int:
    """Build contracted contest entirely via HTTP (input CSVs only, no expected oracle)."""
    if rounds is None:
        rounds = range(1, 10)

    defaults = _load_contest_defaults()
    structure = defaults["contest_structure"]
    rules_json = {
        "scoring_rules": defaults["scoring_rules"],
        "tiebreakers": defaults["tiebreakers"],
        "constraints": defaults["constraints"],
        "contest_structure": structure,
    }

    sup_token = await api_login(client, "supervisor_api")
    sup_h = auth_header(sup_token)

    create = await client.post(
        f"{API_PREFIX}/contests",
        headers=sup_h,
        json={
            "name": "Contracted E2E",
            "total_teams": structure["total_teams"],
            "matches_per_round": structure["matches_per_round"],
            "total_rounds": structure["total_rounds"],
            "is_round_robin": structure["is_round_robin"],
            "rules_json": rules_json,
        },
    )
    assert create.status_code == 200, create.text
    contest_id = create.json()["id"]

    team_short_to_id: dict[str, int] = {}
    for row in _load_teams_csv():
        resp = await client.post(
            contest_url(contest_id, "/teams"),
            headers=sup_h,
            json={
                "name": row["full_name"],
                "short_name": row["short_name"],
                "logo_url": row.get("logo_url") or None,
            },
        )
        assert resp.status_code == 200, resp.text
        team_short_to_id[row["short_name"]] = resp.json()["id"]

    user_logins: set[str] = set()
    for row in _load_users_csv():
        login = row["login"].strip()
        user_logins.add(login)
        await _invite_and_set_password(
            client,
            contest_id,
            sup_h,
            email=row["email"].strip(),
            first_name="",
            last_name=row["full_name"].strip(),
            login=login,
        )

    matches_by_round = _load_matches_csv()
    predictions_by_round_user = _load_predictions_csv()
    now = datetime.now(timezone.utc)
    match_key_to_id: dict[tuple[int, str, str], int] = {}

    for round_num in rounds:
        match_rows = matches_by_round[round_num]
        base_dt = now + timedelta(days=20 + round_num * 5)
        match_items = []
        for i, row in enumerate(match_rows):
            dt = (base_dt + timedelta(hours=i * 3)).isoformat()
            match_items.append(
                {
                    "team1_id": team_short_to_id[row["home_team_short"].strip()],
                    "team2_id": team_short_to_id[row["away_team_short"].strip()],
                    "date_time": dt,
                }
            )
        earliest = base_dt
        deadline = (earliest - timedelta(hours=structure["deadline_rule_hours"])).isoformat()

        created = await client.post(
            contest_url(contest_id, "/admin/rounds"),
            headers=sup_h,
            json={"number": round_num, "deadline": deadline, "matches": match_items},
        )
        assert created.status_code == 200, created.text
        round_id = created.json()["round_id"]

        async with sf() as session:
            db_matches = (
                await session.scalars(
                    select(Match).where(Match.round_id == round_id).order_by(Match.id)
                )
            ).all()
            for row, db_match in zip(match_rows, db_matches, strict=True):
                match_key_to_id[
                    (
                        round_num,
                        row["home_team_short"].strip(),
                        row["away_team_short"].strip(),
                    )
                ] = db_match.id

        activated = await client.post(
            contest_url(contest_id, f"/admin/rounds/{round_id}/activate"),
            headers=sup_h,
        )
        assert activated.status_code == 200, activated.text

        for login in sorted(user_logins):
            pred_rows = predictions_by_round_user.get((round_num, login), [])
            if not pred_rows:
                continue
            preds = []
            for prow in pred_rows:
                key = (
                    round_num,
                    prow["home_team_short"].strip(),
                    prow["away_team_short"].strip(),
                )
                preds.append(
                    {
                        "match_id": match_key_to_id[key],
                        "score1": int(prow["pred_score1"]),
                        "score2": int(prow["pred_score2"]),
                    }
                )
            user_token = await api_login(client, login)
            pred_resp = await client.post(
                contest_url(contest_id, f"/rounds/{round_id}/predictions"),
                headers=auth_header(user_token),
                json={"predictions": preds},
            )
            assert pred_resp.status_code == 200, pred_resp.text

        past_deadline_dt = now - timedelta(hours=48)
        past_match_dt = past_deadline_dt + timedelta(hours=25)
        upd = await client.patch(
            contest_url(contest_id, f"/admin/rounds/{round_id}"),
            headers=sup_h,
            json={
                "deadline": past_deadline_dt.isoformat(),
                "matches": [
                    {
                        "match_id": match_key_to_id[
                            (
                                round_num,
                                r["home_team_short"].strip(),
                                r["away_team_short"].strip(),
                            )
                        ],
                        "date_time": past_match_dt.isoformat(),
                    }
                    for r in match_rows
                ],
            },
        )
        assert upd.status_code == 200, upd.text
        closed = await client.post(
            contest_url(contest_id, f"/admin/rounds/{round_id}/close"),
            headers=sup_h,
        )
        assert closed.status_code == 200, closed.text

        for row in match_rows:
            if row["status"].strip() != "FINISHED":
                continue
            key = (
                round_num,
                row["home_team_short"].strip(),
                row["away_team_short"].strip(),
            )
            mid = match_key_to_id[key]
            result = await client.put(
                contest_url(contest_id, f"/admin/matches/{mid}/result"),
                headers=sup_h,
                json={
                    "score1": int(row["actual_score1"]),
                    "score2": int(row["actual_score2"]),
                },
            )
            assert result.status_code == 200, result.text

        if calculate:
            calc = await client.post(
                contest_url(contest_id, f"/admin/rounds/{round_id}/calculate"),
                headers=sup_h,
            )
            assert calc.status_code == 200, calc.text

    return contest_id


async def calculate_rounds_via_http(
    client: httpx.AsyncClient,
    sf: async_sessionmaker[AsyncSession],
    contest_id: int = DEFAULT_CONTEST_ID,
    round_numbers: range | None = None,
) -> None:
    if round_numbers is None:
        round_numbers = range(1, 10)
    await ensure_contest_running(sf, client, contest_id)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    for n in round_numbers:
        rid = await get_round_id(sf, n, contest_id)
        resp = await client.post(
            contest_url(contest_id, f"/admin/rounds/{rid}/calculate"),
            headers=h,
        )
        assert resp.status_code == 200, f"Round {n}: {resp.text}"


async def publish_rounds_via_http(
    client: httpx.AsyncClient,
    sf: async_sessionmaker[AsyncSession],
    contest_id: int = DEFAULT_CONTEST_ID,
    round_numbers: range | None = None,
) -> None:
    """Publish rounds after calculate (global LB requires PUBLISHED)."""
    if round_numbers is None:
        round_numbers = range(1, 10)
    sup = await api_login(client, "supervisor_api")
    h = auth_header(sup)
    for n in round_numbers:
        rid = await get_round_id(sf, n, contest_id)
        resp = await client.post(
            contest_url(contest_id, f"/admin/rounds/{rid}/publish"),
            headers=h,
        )
        assert resp.status_code == 200, f"Round {n} publish: {resp.text}"


def _ensure_src_api_importable() -> None:
    """pytest adds tests/api/ to sys.path — remove shadow of src/api."""
    test_dir = str(Path(__file__).resolve().parent)
    sys.path[:] = [p for p in sys.path if p not in (test_dir, "")]
    for p in (str(_SRC), str(_ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


def _patch_deps(monkeypatch: pytest.MonkeyPatch, engine: Any, sf: async_sessionmaker) -> None:
    import api.deps as deps

    monkeypatch.setattr(deps, "_engine", engine)
    monkeypatch.setattr(deps, "_session_factory", sf)


async def _make_api_client(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    db_name: str,
    *,
    instant_delete: bool,
    load_data: bool,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    db_url = f"sqlite+aiosqlite:///{tmp_path}/{db_name}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("CONTEST_ALLOW_INSTANT_DELETE", "true" if instant_delete else "false")
    from config.settings import get_settings

    get_settings.cache_clear()
    _ensure_src_api_importable()

    if load_data:
        await run_load(database_url=db_url, reset=True)
    else:
        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    engine = create_async_engine(db_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    await _seed_test_users(sf)
    if load_data:
        await _shift_round10_forward(sf)
    _patch_deps(monkeypatch, engine, sf)

    from main import app

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as client:
        yield client, sf, db_url
    await engine.dispose()


@pytest_asyncio.fixture
async def loaded_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    async for item in _make_api_client(
        tmp_path, monkeypatch, "api_test.db", instant_delete=False, load_data=True
    ):
        yield item


@pytest_asyncio.fixture
async def loaded_contest_api(loaded_api):
    """Alias for 1.4.1 contest-scoped lifecycle tests (loader contest id=1)."""
    return loaded_api


@pytest_asyncio.fixture
async def delete_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    async for item in _make_api_client(
        tmp_path, monkeypatch, "api_delete.db", instant_delete=True, load_data=True
    ):
        yield item


@pytest_asyncio.fixture
async def delete_contest_api(delete_api):
    """Alias for 1.4.1 contest-scoped delete tests."""
    return delete_api


@pytest_asyncio.fixture
async def empty_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    async for item in _make_api_client(
        tmp_path, monkeypatch, "empty_api.db", instant_delete=False, load_data=False
    ):
        yield item


@pytest_asyncio.fixture
async def stage_112_api(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], str]]:
    """Stage 1.12 API client with enforce_password_setup + training mode env."""
    from tests.api.stage_112_helpers import apply_env

    apply_env(monkeypatch)
    async for item in _make_api_client(
        tmp_path, monkeypatch, "stage_112.db", instant_delete=False, load_data=False
    ):
        yield item
