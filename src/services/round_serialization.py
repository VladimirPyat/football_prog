"""Build API round payloads with supplementary-tour metadata."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Match, Round
from schemas.rounds import RoundOut


async def source_round_numbers_by_round_id(
    session: AsyncSession, round_ids: list[int]
) -> dict[int, list[int]]:
    """Map supplementary round id → sorted source round numbers (from moved matches)."""
    if not round_ids:
        return {}

    rows = (
        await session.execute(
            select(Match.round_id, Round.number)
            .join(Round, Round.id == Match.origin_round_id)
            .where(
                Match.round_id.in_(round_ids),
                Match.origin_round_id.is_not(None),
            )
            .distinct()
        )
    ).all()

    grouped: dict[int, set[int]] = {}
    for round_id, origin_number in rows:
        grouped.setdefault(round_id, set()).add(origin_number)
    return {rid: sorted(nums) for rid, nums in grouped.items()}


def build_round_out(round_: Round, source_round_numbers: list[int] | None = None) -> RoundOut:
    return RoundOut(
        id=round_.id,
        contest_id=round_.contest_id,
        number=round_.number,
        deadline=round_.deadline,
        status=round_.status,
        matches_count=round_.matches_count,
        kind=round_.kind,
        supplementary_index=round_.supplementary_index,
        source_round_numbers=source_round_numbers or [],
    )


async def rounds_to_out(session: AsyncSession, rounds: list[Round]) -> list[RoundOut]:
    round_ids = [r.id for r in rounds]
    sources = await source_round_numbers_by_round_id(session, round_ids)
    return [build_round_out(r, sources.get(r.id, [])) for r in rounds]
