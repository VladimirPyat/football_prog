"""Contest setup phase: create contest, teams, participants, invites."""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from core.security import hash_password
from database.models import (
    Contact,
    Contest,
    ContestLifecycleStatus,
    ContestParticipant,
    ParticipantStatus,
    Team,
    User,
    UserRole,
)
from services.contest_lifecycle_service import require_unlocked


def _build_rules_json(data: dict) -> dict:
    return {
        "scoring_rules": data["scoring_rules"],
        "tiebreakers": data["tiebreakers"],
        "constraints": data["constraints"],
        "contest_structure": data["contest_structure"],
    }


def _load_contest_defaults(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _login_from_email(email: str) -> str:
    local = email.split("@")[0].lower()
    return re.sub(r"[^a-z0-9_]", "_", local)[:32]


async def create_contest(
    session: AsyncSession,
    name: str,
    *,
    slug: str | None = None,
    rules_from_defaults: bool = True,
    rules_json: dict | None = None,
    total_teams: int | None = None,
    matches_per_round: int | None = None,
    total_rounds: int | None = None,
    is_round_robin: bool | None = None,
) -> Contest:
    """Create a DRAFT contest."""
    if rules_from_defaults or rules_json is None:
        data = _load_contest_defaults(get_settings().contest_defaults_path)
        structure = data["contest_structure"]
        rules = _build_rules_json(data)
        contest = Contest(
            name=name,
            slug=slug,
            is_locked=False,
            status=ContestLifecycleStatus.DRAFT,
            total_teams=total_teams or structure["total_teams"],
            matches_per_round=matches_per_round or structure["matches_per_round"],
            total_rounds=total_rounds or structure["total_rounds"],
            is_round_robin=is_round_robin if is_round_robin is not None else structure["is_round_robin"],
            rules_json=rules,
        )
    else:
        contest = Contest(
            name=name,
            slug=slug,
            is_locked=False,
            status=ContestLifecycleStatus.DRAFT,
            total_teams=total_teams or 16,
            matches_per_round=matches_per_round or 8,
            total_rounds=total_rounds or 30,
            is_round_robin=is_round_robin if is_round_robin is not None else True,
            rules_json=rules_json,
        )

    session.add(contest)
    await session.flush()
    return contest


async def update_contest(
    session: AsyncSession, contest_id: int, patch: dict
) -> Contest:
    """Patch contest fields when unlocked."""
    contest = await require_unlocked(session, contest_id)
    for field in (
        "name",
        "slug",
        "total_teams",
        "matches_per_round",
        "total_rounds",
        "is_round_robin",
        "rules_json",
    ):
        if field in patch and patch[field] is not None:
            setattr(contest, field, patch[field])
    return contest


async def list_teams(session: AsyncSession, contest_id: int) -> list[Team]:
    return list(
        await session.scalars(
            select(Team).where(Team.contest_id == contest_id).order_by(Team.id)
        )
    )


async def create_team(
    session: AsyncSession,
    contest_id: int,
    name: str,
    short_name: str,
    logo_url: str | None = None,
) -> Team:
    contest = await require_unlocked(session, contest_id)
    team_count = await session.scalar(
        select(func.count()).select_from(Team).where(Team.contest_id == contest_id)
    )
    if team_count is not None and team_count >= contest.total_teams:
        raise ValueError(f"Contest team cap reached ({contest.total_teams})")

    team = Team(
        contest_id=contest_id,
        name=name,
        short_name=short_name,
        logo_url=logo_url,
    )
    session.add(team)
    await session.flush()
    return team


async def update_team(
    session: AsyncSession,
    contest_id: int,
    team_id: int,
    patch: dict,
) -> Team:
    await require_unlocked(session, contest_id)
    team = await session.get(Team, team_id)
    if team is None or team.contest_id != contest_id:
        raise ValueError(f"Team {team_id} not found in contest {contest_id}")

    for field in ("name", "short_name", "logo_url"):
        if field in patch and patch[field] is not None:
            setattr(team, field, patch[field])
    return team


async def delete_team(session: AsyncSession, contest_id: int, team_id: int) -> None:
    await require_unlocked(session, contest_id)
    team = await session.get(Team, team_id)
    if team is None or team.contest_id != contest_id:
        raise ValueError(f"Team {team_id} not found in contest {contest_id}")
    await session.delete(team)


async def list_participants(session: AsyncSession, contest_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(ContestParticipant, User, Contact)
            .join(User, User.id == ContestParticipant.user_id)
            .outerjoin(Contact, Contact.user_id == User.id)
            .where(ContestParticipant.contest_id == contest_id)
            .order_by(User.id)
        )
    ).all()

    return [
        {
            "user_id": user.id,
            "login": user.login,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": contact.email if contact else None,
            "status": participant.status,
            "exceptional_tiebreak_points": participant.exceptional_tiebreak_points,
        }
        for participant, user, contact in rows
    ]


async def add_participant(
    session: AsyncSession,
    contest_id: int,
    email: str,
    first_name: str,
    last_name: str,
    login: str | None = None,
) -> dict:
    """Create user + contact if needed, add PENDING participant, return temp password."""
    await require_unlocked(session, contest_id)

    candidate_login = login or _login_from_email(email)
    existing_login = await session.scalar(select(User).where(User.login == candidate_login))
    if existing_login is not None:
        suffix = 1
        while await session.scalar(
            select(User).where(User.login == f"{candidate_login}{suffix}")
        ):
            suffix += 1
        candidate_login = f"{candidate_login}{suffix}"

    temp_password = secrets.token_urlsafe(10)
    user = User(
        login=candidate_login,
        password_hash=hash_password(temp_password),
        role=UserRole.USER,
        first_name=first_name,
        last_name=last_name,
        is_temp_password=True,
    )
    session.add(user)
    await session.flush()

    session.add(Contact(user_id=user.id, email=email))
    session.add(
        ContestParticipant(
            contest_id=contest_id,
            user_id=user.id,
            status=ParticipantStatus.PENDING,
        )
    )
    await session.flush()

    return {
        "user_id": user.id,
        "login": user.login,
        "temp_password": temp_password,
        "status": ParticipantStatus.PENDING,
    }


async def remove_participant(
    session: AsyncSession, contest_id: int, user_id: int
) -> None:
    """Remove participant from contest; keep global user if enrolled elsewhere."""
    await require_unlocked(session, contest_id)
    participant = await session.get(ContestParticipant, (contest_id, user_id))
    if participant is None:
        raise ValueError(f"Participant {user_id} not found in contest {contest_id}")

    other_enrollments = await session.scalar(
        select(func.count())
        .select_from(ContestParticipant)
        .where(
            ContestParticipant.user_id == user_id,
            ContestParticipant.contest_id != contest_id,
        )
    )

    await session.delete(participant)

    if not other_enrollments:
        user = await session.get(User, user_id)
        if user is not None and user.role == UserRole.USER:
            contact = await session.get(Contact, user_id)
            if contact is not None:
                await session.delete(contact)
            await session.delete(user)
