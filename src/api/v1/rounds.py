"""Public rounds listing."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from api.deps import DbSession
from database.models import Round
from schemas.rounds import RoundOut

router = APIRouter(prefix="/rounds", tags=["rounds (public)"])


@router.get("", response_model=list[RoundOut])
async def list_rounds(session: DbSession) -> list[RoundOut]:
    rounds = (await session.scalars(select(Round).order_by(Round.number))).all()
    return [RoundOut.model_validate(r) for r in rounds]
