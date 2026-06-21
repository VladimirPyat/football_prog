"""Contest-scoped operational endpoints: rounds, predictions, admin, leaderboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from api.deps import (
    ContestContext,
    CurrentUser,
    DbSession,
    RoleChecker,
    cache_control_header,
    require_not_temp_password,
)
from database.models import Contest, Match, MatchStatus, Round, RoundStatus, Team, User, UserRole
from schemas.admin import (
    CreateRoundRequest,
    MatchResultRequest,
    MatchResultResponse,
    MatchStatusPatch,
    MatchStatusResponse,
    RoundActionResponse,
    UpdateRoundRequest,
)
from schemas.contest import FreeTourRequest
from schemas.leaderboard import LeaderboardOut, RoundResultsOut
from schemas.predictions import PredictionBatchRequest, PredictionBatchResponse, RoundPredictionsView
from schemas.rounds import RoundOut
from services.contest_lifecycle_service import assert_contest_running, ensure_running_on_first_activation
from services.leaderboard_service import (
    compute_etag,
    get_global_leaderboard,
    get_round_leaderboard,
    get_round_results,
)
from services.match_service import change_status, set_result
from services.prediction_service import submit_batch, visible_predictions
from services.round_service import close_round, create_free_tour, set_deadline, transition_round
from services.scoring_persistence import calculate_round, recalculate_contest

router = APIRouter(prefix="/contests/{contest_id}", tags=["contest operations"])

_supervisor = Depends(RoleChecker(UserRole.SUPERVISOR, UserRole.ADMIN))
_admin = Depends(RoleChecker(UserRole.ADMIN))


async def _get_contest(session: DbSession, contest_id: int, _contest: ContestContext) -> Contest:
    return _contest


@router.get("/rounds", response_model=list[RoundOut])
async def list_rounds(
    contest_id: int, session: DbSession, _contest: ContestContext
) -> list[RoundOut]:
    rounds = (
        await session.scalars(
            select(Round).where(Round.contest_id == contest_id).order_by(Round.number)
        )
    ).all()
    return [RoundOut.model_validate(r) for r in rounds]


@router.get("/rounds/{round_id}/predictions", response_model=RoundPredictionsView)
async def get_predictions(
    contest_id: int,
    round_id: int,
    session: DbSession,
    user: CurrentUser,
    _contest: ContestContext,
) -> RoundPredictionsView:
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Round not found")

    now = datetime.now(timezone.utc)
    deadline = round_.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    matches = (
        await session.scalars(select(Match).where(Match.round_id == round_id))
    ).all()
    team_ids = {m.team1_id for m in matches} | {m.team2_id for m in matches}
    teams = {
        t.id: t
        for t in (await session.scalars(select(Team).where(Team.id.in_(team_ids)))).all()
    }

    match_out = []
    for m in matches:
        t1 = teams.get(m.team1_id)
        t2 = teams.get(m.team2_id)
        match_out.append(
            {
                "id": m.id,
                "team1": t1.name if t1 else str(m.team1_id),
                "team2": t2.name if t2 else str(m.team2_id),
                "date_time": m.date_time.isoformat(),
                "score1": m.score1,
                "score2": m.score2,
                "status": m.status,
            }
        )

    raw = await visible_predictions(session, contest_id, round_id, user.role, user.id)
    users = {u.id: u for u in (await session.scalars(select(User))).all()}
    by_user: dict[int, list] = {}
    for item in raw:
        uid = item["user_id"]
        by_user.setdefault(uid, []).append(item)

    entries = []
    for uid, preds in by_user.items():
        u = users.get(uid)
        name = f"{u.first_name} {u.last_name}" if u else str(uid)
        if "match_id" in preds[0]:
            entries.append(
                {
                    "user_id": uid,
                    "user_name": name,
                    "submitted": True,
                    "predictions": [
                        {
                            "match_id": p["match_id"],
                            "score1": p.get("score1"),
                            "score2": p.get("score2"),
                        }
                        for p in preds
                    ],
                }
            )
        else:
            entries.append({"user_id": uid, "user_name": name, "submitted": True, "predictions": None})

    return RoundPredictionsView(
        round_id=round_id,
        deadline_passed=now >= deadline,
        matches=match_out,
        entries=entries,
    )


@router.post("/rounds/{round_id}/predictions", response_model=PredictionBatchResponse)
async def post_predictions(
    contest_id: int,
    round_id: int,
    body: PredictionBatchRequest,
    session: DbSession,
    user: Annotated[User, Depends(require_not_temp_password)],
    _contest: ContestContext,
) -> PredictionBatchResponse:
    try:
        await assert_contest_running(session, contest_id)
        items = [(p.match_id, p.score1, p.score2) for p in body.predictions]
        count = await submit_batch(session, contest_id, user.id, round_id, items)
        await session.commit()
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "out of range" in msg:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg) from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=msg) from exc

    return PredictionBatchResponse(saved_count=count)


@router.get("/rounds/{round_id}/leaderboard", response_model=LeaderboardOut)
async def round_leaderboard(
    contest_id: int, round_id: int, session: DbSession, response: Response, _contest: ContestContext
) -> LeaderboardOut:
    try:
        data = await get_round_leaderboard(session, contest_id, round_id)
        etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return LeaderboardOut(**data)


@router.get("/rounds/{round_id}/results", response_model=RoundResultsOut)
async def round_results(
    contest_id: int, round_id: int, session: DbSession, response: Response, _contest: ContestContext
) -> RoundResultsOut:
    try:
        data = await get_round_results(session, contest_id, round_id)
        etag = await compute_etag(session, contest_id=contest_id, round_id=round_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return RoundResultsOut(**data)


@router.get("/leaderboard", response_model=LeaderboardOut)
async def global_leaderboard(
    contest_id: int, session: DbSession, response: Response, _contest: ContestContext
) -> LeaderboardOut:
    try:
        data = await get_global_leaderboard(session, contest_id)
        etag = await compute_etag(session, contest_id=contest_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    for k, v in cache_control_header().items():
        response.headers[k] = v
    response.headers["ETag"] = etag
    return LeaderboardOut(**data)


@router.post("/admin/rounds", dependencies=[_supervisor])
async def create_round(
    contest_id: int, body: CreateRoundRequest, session: DbSession, _contest: ContestContext
) -> dict:
    await assert_contest_running(session, contest_id)
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Contest not found")

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


@router.patch("/admin/rounds/{round_id}", dependencies=[_supervisor])
async def update_round(
    contest_id: int,
    round_id: int,
    body: UpdateRoundRequest,
    session: DbSession,
    _contest: ContestContext,
) -> dict:
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


@router.post("/admin/rounds/{round_id}/activate", dependencies=[_supervisor])
async def activate_round(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Round not found")
    try:
        round_ = await transition_round(session, round_id, RoundStatus.ACTIVE)
        await ensure_running_on_first_activation(session, contest_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "status": round_.status}


@router.post("/admin/rounds/{round_id}/close", dependencies=[_supervisor])
async def close_round_endpoint(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    await assert_contest_running(session, contest_id)
    try:
        round_ = await close_round(session, contest_id, round_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"round_id": round_.id, "status": round_.status}


@router.post("/admin/rounds/{round_id}/calculate", response_model=RoundActionResponse, dependencies=[_supervisor])
async def calculate(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> RoundActionResponse:
    await assert_contest_running(session, contest_id)
    try:
        count = await calculate_round(session, round_id, contest_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RoundActionResponse(round_id=round_id, status=RoundStatus.CALCULATED, users_scored=count)


@router.post("/admin/rounds/{round_id}/publish", dependencies=[_supervisor])
async def publish_round(
    contest_id: int, round_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    await assert_contest_running(session, contest_id)
    round_ = await session.get(Round, round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Round not found")
    try:
        round_ = await transition_round(session, round_id, RoundStatus.PUBLISHED)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "status": round_.status}


@router.post("/admin/rounds/free-tour", dependencies=[_supervisor])
async def free_tour(
    contest_id: int, body: FreeTourRequest, session: DbSession, _contest: ContestContext
) -> dict:
    await assert_contest_running(session, contest_id)
    try:
        new_round = await create_free_tour(
            session,
            contest_id,
            [{"match_id": m.match_id, "new_date_time": m.new_date_time} for m in body.matches],
            body.deadline,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"round_id": new_round.id, "round_number": new_round.number}


@router.put("/admin/matches/{match_id}/result", response_model=MatchResultResponse, dependencies=[_supervisor])
async def apply_result(
    contest_id: int,
    match_id: int,
    body: MatchResultRequest,
    session: DbSession,
    _contest: ContestContext,
) -> MatchResultResponse:
    try:
        match = await set_result(session, contest_id, match_id, body.score1, body.score2)
        await session.commit()
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "deadline" in msg.lower() or "closed" in msg.lower():
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=msg) from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    return MatchResultResponse(round_id=match.round_id)


@router.patch("/admin/matches/{match_id}/status", response_model=MatchStatusResponse, dependencies=[_supervisor])
async def patch_status(
    contest_id: int,
    match_id: int,
    body: MatchStatusPatch,
    session: DbSession,
    _contest: ContestContext,
) -> MatchStatusResponse:
    await assert_contest_running(session, contest_id)
    match = await session.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Match not found")

    round_ = await session.get(Round, match.round_id)
    if round_ is None or round_.contest_id != contest_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Match not found")

    was_calculated = round_.status == RoundStatus.CALCULATED

    try:
        new_status = MatchStatus(body.status)
        await change_status(session, contest_id, match_id, new_status)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    recalc = was_calculated and body.status == MatchStatus.VOID
    return MatchStatusResponse(recalculation_triggered=recalc)


@router.post("/admin/recalculate", dependencies=[_admin])
async def admin_recalculate(
    contest_id: int, session: DbSession, _contest: ContestContext
) -> dict:
    count = await recalculate_contest(session, contest_id)
    await session.commit()
    return {"recalculated_rounds": count}
