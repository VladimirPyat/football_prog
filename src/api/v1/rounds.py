"""Public rounds listing (legacy 1.3 shim)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from api.deps import DbSession, resolve_default_contest_id
from database.models import Round
from schemas.rounds import RoundOut
from services.round_serialization import rounds_to_out

router = APIRouter(prefix="/rounds", tags=["legacy (deprecated)", "rounds (public)"])


@router.get("", response_model=list[RoundOut], deprecated=True)
async def list_rounds(session: DbSession) -> list[RoundOut]:
    """Список туров. Устаревший shim: default contest."""
    contest_id = await resolve_default_contest_id(session)
    rounds = (
        await session.scalars(
            select(Round).where(Round.contest_id == contest_id).order_by(Round.number)
        )
    ).all()
    return await rounds_to_out(session, list(rounds))
