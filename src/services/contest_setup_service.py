"""Contest setup phase: create contest, teams, participants, invites."""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from config.settings import get_settings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
from core.security import hash_password
from core.setup_tokens import build_setup_url, create_setup_token
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
from services.team_logo_service import delete_uploaded_logo_if_custom


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


def validate_contest_structure(
    *,
    total_teams: int,
    matches_per_round: int,
    total_rounds: int,
    is_round_robin: bool,
) -> None:
    """Validate contest structure fields before persist."""
    if total_teams < 1:
        raise ValidationError("Число команд должно быть положительным")
    if matches_per_round < 1:
        raise ValidationError("Матчей в туре должно быть положительным")
    if total_rounds < 1:
        raise ValidationError("Число туров должно быть положительным")

    if not is_round_robin:
        return

    if total_teams % 2 != 0:
        raise ValidationError(
            "Для круговой системы нужно чётное число команд (≥ 2) "
            "или отключите круговую систему"
        )
    expected_matches = total_teams // 2
    if matches_per_round != expected_matches:
        raise ValidationError("Матчей в туре должно быть = команды / 2")
    expected_rounds = (total_teams - 1) * 2
    if total_rounds != expected_rounds:
        raise ValidationError("Число туров должно быть = (команды − 1) × 2")


def _sync_round_robin_structure(
    *,
    total_teams: int,
    matches_per_round: int,
    total_rounds: int,
    is_round_robin: bool,
    fields_set: set[str],
) -> tuple[int, int, int]:
    """Derive matches/rounds from team count when round-robin and not explicitly set."""
    if not is_round_robin or "total_teams" not in fields_set:
        return total_teams, matches_per_round, total_rounds

    if "matches_per_round" not in fields_set:
        matches_per_round = total_teams // 2
    if "total_rounds" not in fields_set:
        total_rounds = (total_teams - 1) * 2
    return total_teams, matches_per_round, total_rounds


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
    fields_set: set[str] = set()
    if total_teams is not None:
        fields_set.add("total_teams")
    if matches_per_round is not None:
        fields_set.add("matches_per_round")
    if total_rounds is not None:
        fields_set.add("total_rounds")
    if is_round_robin is not None:
        fields_set.add("is_round_robin")

    if rules_from_defaults or rules_json is None:
        data = _load_contest_defaults(get_settings().contest_defaults_path)
        structure = data["contest_structure"]
        rules = _build_rules_json(data)
        resolved_teams = total_teams or structure["total_teams"]
        resolved_matches = matches_per_round or structure["matches_per_round"]
        resolved_rounds = total_rounds or structure["total_rounds"]
        resolved_round_robin = (
            is_round_robin if is_round_robin is not None else structure["is_round_robin"]
        )
    else:
        rules = rules_json
        resolved_teams = total_teams or 16
        resolved_matches = matches_per_round or 8
        resolved_rounds = total_rounds or 30
        resolved_round_robin = is_round_robin if is_round_robin is not None else True

    resolved_teams, resolved_matches, resolved_rounds = _sync_round_robin_structure(
        total_teams=resolved_teams,
        matches_per_round=resolved_matches,
        total_rounds=resolved_rounds,
        is_round_robin=resolved_round_robin,
        fields_set=fields_set,
    )

    contest = Contest(
        name=name,
        slug=slug,
        is_locked=False,
        status=ContestLifecycleStatus.DRAFT,
        total_teams=resolved_teams,
        matches_per_round=resolved_matches,
        total_rounds=resolved_rounds,
        is_round_robin=resolved_round_robin,
        rules_json=rules,
    )

    validate_contest_structure(
        total_teams=contest.total_teams,
        matches_per_round=contest.matches_per_round,
        total_rounds=contest.total_rounds,
        is_round_robin=contest.is_round_robin,
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

    fields_set = {
        field
        for field in ("total_teams", "matches_per_round", "total_rounds", "is_round_robin")
        if field in patch and patch[field] is not None
    }
    synced_teams, synced_matches, synced_rounds = _sync_round_robin_structure(
        total_teams=contest.total_teams,
        matches_per_round=contest.matches_per_round,
        total_rounds=contest.total_rounds,
        is_round_robin=contest.is_round_robin,
        fields_set=fields_set,
    )
    contest.total_teams = synced_teams
    contest.matches_per_round = synced_matches
    contest.total_rounds = synced_rounds

    validate_contest_structure(
        total_teams=contest.total_teams,
        matches_per_round=contest.matches_per_round,
        total_rounds=contest.total_rounds,
        is_round_robin=contest.is_round_robin,
    )
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
        raise ValidationError(f"Достигнут лимит команд в конкурсе ({contest.total_teams})")

    dup = await session.scalar(
        select(Team).where(Team.contest_id == contest_id, Team.name == name)
    )
    if dup is not None:
        raise ValidationError(f"Команда с именем «{name}» уже существует")

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
        raise NotFoundError(f"Команда {team_id} не найдена в конкурсе {contest_id}")

    settings = get_settings()
    if "logo_url" in patch:
        if patch["logo_url"] is None:
            delete_uploaded_logo_if_custom(team.logo_url, settings)
            team.logo_url = None
        else:
            team.logo_url = patch["logo_url"]

    for field in ("name", "short_name"):
        if field in patch and patch[field] is not None:
            setattr(team, field, patch[field])
    return team


async def delete_team(session: AsyncSession, contest_id: int, team_id: int) -> None:
    await require_unlocked(session, contest_id)
    team = await session.get(Team, team_id)
    if team is None or team.contest_id != contest_id:
        raise NotFoundError(f"Команда {team_id} не найдена в конкурсе {contest_id}")
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

    token = create_setup_token(user_id=user.id, contest_id=contest_id)
    return {
        "user_id": user.id,
        "login": user.login,
        "temp_password": temp_password,
        "status": ParticipantStatus.PENDING,
        "setup_url": build_setup_url(token),
    }


async def purge_unconfirmed_participants(session: AsyncSession, contest_id: int) -> int:
    """Remove PENDING USER participants before contest goes live."""
    import logging

    logger = logging.getLogger(__name__)
    rows = (
        await session.execute(
            select(ContestParticipant.user_id)
            .join(User, User.id == ContestParticipant.user_id)
            .where(
                ContestParticipant.contest_id == contest_id,
                ContestParticipant.status == ParticipantStatus.PENDING,
                User.role == UserRole.USER.value,
            )
        )
    ).all()
    removed = 0
    for (user_id,) in rows:
        await remove_participant(session, contest_id, user_id)
        removed += 1
    if removed:
        logger.info(
            "purged unconfirmed participants contest_id=%s count=%s", contest_id, removed
        )
    return removed


async def remove_participant(
    session: AsyncSession, contest_id: int, user_id: int
) -> None:
    """Remove participant from contest; keep global user if enrolled elsewhere."""
    await require_unlocked(session, contest_id)
    participant = await session.get(ContestParticipant, (contest_id, user_id))
    if participant is None:
        raise NotFoundError(f"Участник {user_id} не найден в конкурсе {contest_id}")

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
