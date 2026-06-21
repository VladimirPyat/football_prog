"""Admin round management endpoints (legacy 1.3 shims)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from api.deps import DbSession, RoleChecker, resolve_default_contest_id
from database.models import Contest, Match, MatchStatus, Round, RoundStatus, UserRole
from schemas.admin import CreateRoundRequest, RoundActionResponse, UpdateRoundRequest
from services.contest_lifecycle_service import assert_contest_running, ensure_running_on_first_activation
from services.round_service import close_round, set_deadline, transition_round
from services.scoring_persistence import calculate_round

router = APIRouter(prefix="/admin/rounds", tags=["legacy (deprecated)", "admin (supervisor)"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))


@router.post("", dependencies=[_supervisor], deprecated=True)
async def create_round(body: CreateRoundRequest, session: DbSession) -> dict:
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No contest")

    if len(body.matches) > contest.matches_per_round:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Too many matches: max {contest.matches_per_round}",
        )

    team_ids_in_round: set[int] = set()
    for m in body.matches:
        if m.team1_id == m.team2_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="team1_id must differ from team2_id")
        if m.team1_id in team_ids_in_round or m.team2_id in team_ids_in_round:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Duplicate team in round")
        team_ids_in_round.add(m.team1_id)
        team_ids_in_round.add(m.team2_id)

    deadline_rule = contest.rules_json["contest_structure"]["deadline_rule_hours"]
    earliest = min(m.date_time for m in body.matches)
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=timezone.utc)
    cutoff = earliest - timedelta(hours=deadline_rule)
    dl = body.deadline if body.deadline.tzinfo else body.deadline.replace(tzinfo=timezone.utc)
    if dl >= cutoff:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Deadline violates 24h rule")

    existing = await session.scalar(
        select(Round).where(Round.contest_id == contest_id, Round.number == body.number)
    )
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Round number {body.number} exists")

    round_ = Round(
        contest_id=contest_id,
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


@router.patch("/{round_id}", dependencies=[_supervisor], deprecated=True)
async def update_round(round_id: int, body: UpdateRoundRequest, session: DbSession) -> dict:
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
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


@router.post("/{round_id}/activate", dependencies=[_supervisor], deprecated=True)
async def activate_round(round_id: int, session: DbSession) -> dict:
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    try:
        round_ = await transition_round(session, round_id, RoundStatus.ACTIVE)
        await ensure_running_on_first_activation(session, contest_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "status": round_.status}


@router.post("/{round_id}/close", dependencies=[_supervisor], deprecated=True)
async def close_round_endpoint(round_id: int, session: DbSession) -> dict:
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    try:
        round_ = await close_round(session, contest_id, round_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"round_id": round_.id, "status": round_.status}


@router.post("/{round_id}/calculate", response_model=RoundActionResponse, dependencies=[_supervisor], deprecated=True)
async def calculate(round_id: int, session: DbSession) -> RoundActionResponse:
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    try:
        count = await calculate_round(session, round_id, contest_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RoundActionResponse(round_id=round_id, status=RoundStatus.CALCULATED, users_scored=count)


@router.post("/{round_id}/publish", dependencies=[_supervisor], deprecated=True)
async def publish_round(round_id: int, session: DbSession) -> dict:
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    try:
        round_ = await transition_round(session, round_id, RoundStatus.PUBLISHED)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "status": round_.status}
