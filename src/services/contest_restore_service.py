"""Contest restore snapshots for supervisor training mode."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from config.settings import get_settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import SnapshotExpiredError, SnapshotNotFoundError
from database.models import (
    Contest,
    ContestParticipant,
    ContestRestoreSnapshot,
    Match,
    Round,
    Team,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def _build_snapshot(session: AsyncSession, contest_id: int) -> dict:
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise SnapshotNotFoundError(f"Конкурс {contest_id} не найден")

    teams = (
        await session.scalars(select(Team).where(Team.contest_id == contest_id).order_by(Team.id))
    ).all()
    participants = (
        await session.scalars(
            select(ContestParticipant).where(ContestParticipant.contest_id == contest_id)
        )
    ).all()
    rounds = (
        await session.scalars(
            select(Round).where(Round.contest_id == contest_id).order_by(Round.number)
        )
    ).all()
    round_ids = [r.id for r in rounds]
    matches: list[Match] = []
    if round_ids:
        matches = list(
            await session.scalars(
                select(Match).where(Match.round_id.in_(round_ids)).order_by(Match.id)
            )
        )

    round_number_by_id = {r.id: r.number for r in rounds}

    return {
        "contest": {
            "name": contest.name,
            "slug": contest.slug,
            "is_locked": contest.is_locked,
            "status": contest.status,
            "paused_at": _iso(contest.paused_at) if contest.paused_at else None,
            "finished_at": _iso(contest.finished_at) if contest.finished_at else None,
            "total_teams": contest.total_teams,
            "matches_per_round": contest.matches_per_round,
            "total_rounds": contest.total_rounds,
            "is_round_robin": contest.is_round_robin,
            "rules_json": contest.rules_json,
        },
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "short_name": t.short_name,
                "logo_url": t.logo_url,
            }
            for t in teams
        ],
        "participants": [
            {
                "user_id": p.user_id,
                "status": p.status,
                "exceptional_tiebreak_points": p.exceptional_tiebreak_points,
            }
            for p in participants
        ],
        "rounds": [
            {
                "number": r.number,
                "deadline": _iso(r.deadline),
                "status": r.status,
                "matches_count": r.matches_count,
                "kind": r.kind,
                "supplementary_index": r.supplementary_index,
            }
            for r in rounds
        ],
        "matches": [
            {
                "round_number": round_number_by_id[m.round_id],
                "origin_round_number": (
                    round_number_by_id.get(m.origin_round_id)
                    if m.origin_round_id is not None
                    else None
                ),
                "team1_id": m.team1_id,
                "team2_id": m.team2_id,
                "date_time": _iso(m.date_time),
                "score1": m.score1,
                "score2": m.score2,
                "status": m.status,
            }
            for m in matches
        ],
    }


async def save_restore_snapshot(
    session: AsyncSession,
    contest_id: int,
    *,
    deleted_by_user_id: int | None,
) -> None:
    """Persist restorable contest payload before wipe."""
    settings = get_settings()
    if not settings.contest_delete_enabled:
        return

    existing = await session.get(ContestRestoreSnapshot, contest_id)
    if existing is not None:
        await session.delete(existing)
        await session.flush()

    snapshot = await _build_snapshot(session, contest_id)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.contest_restore_window_seconds)
    session.add(
        ContestRestoreSnapshot(
            contest_id=contest_id,
            snapshot_json=snapshot,
            deleted_at=now,
            expires_at=expires,
            deleted_by_user_id=deleted_by_user_id,
        )
    )


async def restore_contest_from_snapshot(session: AsyncSession, contest_id: int) -> None:
    """Replay snapshot into contest and remove snapshot row."""
    row = await session.get(ContestRestoreSnapshot, contest_id)
    if row is None:
        raise SnapshotNotFoundError("Снимок для восстановления не найден")

    now = datetime.now(UTC)
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if now >= expires:
        raise SnapshotExpiredError("Срок восстановления истёк")

    data = row.snapshot_json
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise SnapshotNotFoundError(f"Конкурс {contest_id} не найден")

    c = data["contest"]
    contest.name = c["name"]
    contest.slug = c.get("slug")
    contest.is_locked = c["is_locked"]
    contest.status = c["status"]
    contest.paused_at = _parse_dt(c["paused_at"]) if c.get("paused_at") else None
    contest.finished_at = _parse_dt(c["finished_at"]) if c.get("finished_at") else None
    contest.total_teams = c["total_teams"]
    contest.matches_per_round = c["matches_per_round"]
    contest.total_rounds = c["total_rounds"]
    contest.is_round_robin = c["is_round_robin"]
    contest.rules_json = c["rules_json"]
    contest.deleted_at = None

    team_id_map: dict[int, int] = {}
    for team in data.get("teams", []):
        entity = Team(
            contest_id=contest_id,
            name=team["name"],
            short_name=team["short_name"],
            logo_url=team.get("logo_url"),
        )
        session.add(entity)
        await session.flush()
        team_id_map[int(team["id"])] = entity.id

    for part in data.get("participants", []):
        session.add(
            ContestParticipant(
                contest_id=contest_id,
                user_id=part["user_id"],
                status=part["status"],
                exceptional_tiebreak_points=part.get("exceptional_tiebreak_points", 0),
            )
        )

    round_id_by_number: dict[int, int] = {}
    for rnd in data.get("rounds", []):
        entity = Round(
            contest_id=contest_id,
            number=rnd["number"],
            deadline=_parse_dt(rnd["deadline"]),
            status=rnd["status"],
            matches_count=rnd.get("matches_count", 0),
            kind=rnd.get("kind", "REGULAR"),
            supplementary_index=rnd.get("supplementary_index"),
        )
        session.add(entity)
        await session.flush()
        round_id_by_number[int(rnd["number"])] = entity.id

    for match in data.get("matches", []):
        origin_round_number = match.get("origin_round_number")
        origin_round_id = (
            round_id_by_number.get(int(origin_round_number))
            if origin_round_number is not None
            else None
        )
        session.add(
            Match(
                round_id=round_id_by_number[int(match["round_number"])],
                origin_round_id=origin_round_id,
                team1_id=team_id_map[int(match["team1_id"])],
                team2_id=team_id_map[int(match["team2_id"])],
                date_time=_parse_dt(match["date_time"]),
                score1=match.get("score1"),
                score2=match.get("score2"),
                status=match["status"],
            )
        )

    await session.delete(row)


async def has_restore_snapshot(session: AsyncSession, contest_id: int) -> bool:
    """True when a non-expired restore snapshot exists."""
    row = await session.get(ContestRestoreSnapshot, contest_id)
    if row is None:
        return False
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return datetime.now(UTC) < expires
