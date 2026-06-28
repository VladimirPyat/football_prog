"""Prediction submission and visibility endpoints (legacy 1.3 shims)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from api.deps import CurrentUser, DbSession, get_optional_user, resolve_default_contest_id
from api.handlers.predictions import build_round_predictions_view
from database.models import User
from schemas.predictions import (
    PredictionBatchRequest,
    PredictionBatchResponse,
    RoundPredictionsView,
)
from services.contest_lifecycle_service import assert_contest_running
from services.prediction_service import submit_batch

router = APIRouter(prefix="/rounds", tags=["legacy (deprecated)", "predictions"])

OptionalUser = Annotated[User | None, Depends(get_optional_user)]


@router.get("/{round_id}/predictions", response_model=RoundPredictionsView, deprecated=True)
async def get_predictions(
    round_id: int,
    session: DbSession,
    user: OptionalUser,
) -> RoundPredictionsView:
    """Прогнозы тура. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    return await build_round_predictions_view(session, contest_id, round_id, user)


@router.post("/{round_id}/predictions", response_model=PredictionBatchResponse, deprecated=True)
async def post_predictions(
    round_id: int,
    body: PredictionBatchRequest,
    session: DbSession,
    user: CurrentUser,
) -> PredictionBatchResponse:
    """Сохранить прогнозы. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    await assert_contest_running(session, contest_id)
    items = [(p.match_id, p.score1, p.score2) for p in body.predictions]
    count = await submit_batch(session, contest_id, user.id, round_id, items)
    await session.commit()
    return PredictionBatchResponse(saved_count=count)
