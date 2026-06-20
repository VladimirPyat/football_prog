"""Admin round management endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from api.deps import DbSession, RoleChecker
from database.models import ContestSettings, Match, MatchStatus, Round, RoundStatus, Team, UserRole
from schemas.admin import CreateRoundRequest, RoundActionResponse, UpdateRoundRequest
from services.contest_lifecycle_service import assert_contest_running, ensure_running_on_first_activation
from services.round_service import set_deadline, transition_round

router = APIRouter(prefix="/admin/rounds", tags=["admin (supervisor)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))


async def _get_settings(session) -> ContestSettings:
    settings = await session.scalar(select(ContestSettings).limit(1))
    if settings is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No contest settings")
    return settings


@router.post("", dependencies=[_supervisor])
async def create_round(body: CreateRoundRequest, session: DbSession) -> dict:
    await assert_contest_running(session)
    settings = await _get_settings(session)
    max_matches = settings.matches_per_round

    if len(body.matches) > max_matches:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Too many matches: max {max_matches}",
        )

    team_ids_in_round: set[int] = set()
    for m in body.matches:
        if m.team1_id == m.team2_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="team1_id must differ from team2_id")
        if m.team1_id in team_ids_in_round or m.team2_id in team_ids_in_round:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Duplicate team in round")
        team_ids_in_round.add(m.team1_id)
        team_ids_in_round.add(m.team2_id)

    deadline_rule = settings.rules_json["contest_structure"]["deadline_rule_hours"]
    earliest = min(m.date_time for m in body.matches)
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=timezone.utc)
    cutoff = earliest - timedelta(hours=deadline_rule)
    dl = body.deadline if body.deadline.tzinfo else body.deadline.replace(tzinfo=timezone.utc)
    if dl >= cutoff:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Deadline violates 24h rule")

    existing = await session.scalar(select(Round).where(Round.number == body.number))
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Round number {body.number} exists")

    round_ = Round(
        number=body.number,
        deadline=dl,
        status=RoundStatus.DRAFT,
        matches_count=len(body.matches),
    )
    session.add(round_)
    await session.flush()

    for m in body.matches:
        dt = m.date_time if m.date_time.tzinfo else m.date_time.replace(tzinfo=timezone.utc)
        session.add(
            Match(
                round_id=round_.id,
                team1_id=m.team1_id,
                team2_id=m.team2_id,
                date_time=dt,
                status=MatchStatus.SCHEDULED,
            )
        )

    await session.commit()
    return {"round_id": round_.id, "status": round_.status}


@router.patch("/{round_id}", dependencies=[_supervisor])
async def update_round(round_id: int, body: UpdateRoundRequest, session: DbSession) -> dict:
    await assert_contest_running(session)
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Round not found")
    if round_.status != RoundStatus.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Only ACTIVE rounds can be edited")

    if body.deadline is not None:
        try:
            await set_deadline(session, round_id, body.deadline)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if body.matches:
        for item in body.matches:
            if item.match_id is None:
                continue
            match = await session.get(Match, item.match_id)
            if match is None or match.round_id != round_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Match {item.match_id} not found")
            if item.team1_id is not None:
                match.team1_id = item.team1_id
            if item.team2_id is not None:
                match.team2_id = item.team2_id
            if item.date_time is not None:
                match.date_time = item.date_time
            if item.status is not None:
                match.status = item.status

    await session.commit()
    return {"success": True}


@router.post("/{round_id}/activate", dependencies=[_supervisor])
async def activate_round(round_id: int, session: DbSession) -> dict:
    await assert_contest_running(session)
    try:
        round_ = await transition_round(session, round_id, RoundStatus.ACTIVE)
        await ensure_running_on_first_activation(session)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "status": round_.status}


@router.post("/{round_id}/calculate", response_model=RoundActionResponse, dependencies=[_supervisor])
async def calculate(round_id: int, session: DbSession) -> RoundActionResponse:
    await assert_contest_running(session)
    from services.scoring_persistence import calculate_round  # noqa: PLC0415

    try:
        count = await calculate_round(session, round_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RoundActionResponse(round_id=round_id, status=RoundStatus.CALCULATED, users_scored=count)


@router.post("/{round_id}/publish", dependencies=[_supervisor])
async def publish_round(round_id: int, session: DbSession) -> dict:
    await assert_contest_running(session)
    try:
        round_ = await transition_round(session, round_id, RoundStatus.PUBLISHED)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "status": round_.status}
