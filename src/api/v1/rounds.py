"""Public rounds listing (legacy 1.3 shim)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from api.deps import DbSession, resolve_default_contest_id
from database.models import Round
from schemas.rounds import RoundOut

router = APIRouter(prefix="/rounds", tags=["legacy (deprecated)", "rounds (public)"])


@router.get("", response_model=list[RoundOut], deprecated=True)
async def list_rounds(session: DbSession) -> list[RoundOut]:
    contest_id = await resolve_default_contest_id(session)
    rounds = (
        await session.scalars(
            select(Round).where(Round.contest_id == contest_id).order_by(Round.number)
        )
    ).all()
    return [RoundOut.model_validate(r) for r in rounds]
