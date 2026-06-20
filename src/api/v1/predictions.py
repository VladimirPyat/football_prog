"""Prediction submission and visibility endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from api.deps import CurrentUser, DbSession, require_not_temp_password
from database.models import Match, Round, Team, User
from schemas.predictions import PredictionBatchRequest, PredictionBatchResponse, RoundPredictionsView
from services.contest_lifecycle_service import assert_contest_running
from services.prediction_service import submit_batch, visible_predictions

router = APIRouter(prefix="/rounds", tags=["predictions"])


@router.get("/{round_id}/predictions", response_model=RoundPredictionsView)
async def get_predictions(
    round_id: int,
    session: DbSession,
    user: CurrentUser,
) -> RoundPredictionsView:
    round_ = await session.get(Round, round_id)
    if round_ is None:
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

    raw = await visible_predictions(session, round_id, user.role, user.id)

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


@router.post("/{round_id}/predictions", response_model=PredictionBatchResponse)
async def post_predictions(
    round_id: int,
    body: PredictionBatchRequest,
    session: DbSession,
    user: Annotated[User, Depends(require_not_temp_password)],
) -> PredictionBatchResponse:
    try:
        await assert_contest_running(session)
        items = [(p.match_id, p.score1, p.score2) for p in body.predictions]
        count = await submit_batch(session, user.id, round_id, items)
        await session.commit()
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "out of range" in msg:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg) from exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=msg) from exc

    return PredictionBatchResponse(saved_count=count)
