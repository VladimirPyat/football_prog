"""Leaderboard aggregation, results matrix, and HTTP cache ETag helpers."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContestParticipant, Match, Round, RoundStatus, Score, Team, User
from scoring.standings import build_standings
from scoring.types import UserRoundScore


async def _user_name_map(session: AsyncSession) -> dict[int, str]:
    users = (await session.scalars(select(User))).all()
    return {u.id: f"{u.first_name} {u.last_name}" for u in users}


async def _manual_overrides(session: AsyncSession, contest_id: int) -> dict[int, int]:
    participants = (
        await session.scalars(
            select(ContestParticipant).where(ContestParticipant.contest_id == contest_id)
        )
    ).all()
    return {p.user_id: p.exceptional_tiebreak_points for p in participants}


def _score_to_user_round(score: Score) -> UserRoundScore:
    base = score.points_exact + score.points_diff + score.points_outcome
    return UserRoundScore(
        user_id=score.user_id,
        base_points=base,
        count_exact_high=score.count_exact_high,
        count_exact=score.count_exact,
        count_diff=score.count_diff,
        count_outcome=score.count_outcome,
        correct_outcomes=score.correct_outcomes,
        bonus1=score.bonus1,
        bonus2=score.bonus2,
        bonus3=score.bonus3,
        total_without_bonus3=score.total_without_bonus3,
        total_with_bonus3=score.total_with_bonus3,
        round_rank=0,
        per_match=(),
    )


async def get_round_leaderboard(
    session: AsyncSession, contest_id: int, round_id: int
) -> dict:
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    if round_.contest_id != contest_id:
        raise ValueError(f"Round {round_id} does not belong to contest {contest_id}")

    if round_.status not in {RoundStatus.CALCULATED, RoundStatus.PUBLISHED}:
        raise ValueError(f"Round {round_id} results not available (status={round_.status})")

    scores = (
        await session.scalars(select(Score).where(Score.round_id == round_id))
    ).all()
    names = await _user_name_map(session)
    overrides = await _manual_overrides(session, contest_id)

    per_user: dict[int, list[UserRoundScore]] = {}
    for s in scores:
        per_user.setdefault(s.user_id, []).append(_score_to_user_round(s))

    standings = build_standings(per_user, overrides)
    rows = []
    for row in standings:
        uid = row.user_id
        score_rows = [s for s in scores if s.user_id == uid]
        sr = score_rows[0] if score_rows else None
        rows.append(
            {
                "user_id": uid,
                "user_name": names.get(uid, str(uid)),
                "points_base": sr.points_exact + sr.points_diff + sr.points_outcome if sr else 0,
                "bonus1": sr.bonus1 if sr else 0,
                "bonus2": sr.bonus2 if sr else 0,
                "bonus3": sr.bonus3 if sr else 0,
                "total_without_bonus3": sr.total_without_bonus3 if sr else 0,
                "total_with_bonus3": sr.total_with_bonus3 if sr else 0,
                "correct_outcomes": sr.correct_outcomes if sr else 0,
                "rank": row.rank,
                "predictions_count": row.total_predictions,
                "exceptional_tiebreak_points": overrides.get(uid, 0),
                "tiebreaker_status": row.tiebreaker_status,
            }
        )

    return {
        "contest_id": contest_id,
        "round_id": round_id,
        "round_number": round_.number,
        "leaderboard": rows,
    }


async def get_global_leaderboard(session: AsyncSession, contest_id: int) -> dict:
    scores = (
        await session.scalars(
            select(Score)
            .join(Round)
            .where(
                Round.contest_id == contest_id,
                Round.status.in_([RoundStatus.CALCULATED, RoundStatus.PUBLISHED]),
            )
        )
    ).all()
    names = await _user_name_map(session)
    overrides = await _manual_overrides(session, contest_id)

    per_user: dict[int, list[UserRoundScore]] = {}
    for s in scores:
        per_user.setdefault(s.user_id, []).append(_score_to_user_round(s))

    standings = build_standings(per_user, overrides)
    rows = []
    for row in standings:
        uid = row.user_id
        user_scores = [s for s in scores if s.user_id == uid]
        total_base = sum(s.points_exact + s.points_diff + s.points_outcome for s in user_scores)
        total_b1 = sum(s.bonus1 for s in user_scores)
        total_b2 = sum(s.bonus2 for s in user_scores)
        total_b3 = sum(s.bonus3 for s in user_scores)
        total_wo_b3 = sum(s.total_without_bonus3 for s in user_scores)
        total_w_b3 = sum(s.total_with_bonus3 for s in user_scores)
        total_co = sum(s.correct_outcomes for s in user_scores)
        rows.append(
            {
                "user_id": uid,
                "user_name": names.get(uid, str(uid)),
                "points_base": total_base,
                "bonus1": total_b1,
                "bonus2": total_b2,
                "bonus3": total_b3,
                "total_without_bonus3": total_wo_b3,
                "total_with_bonus3": total_w_b3,
                "correct_outcomes": total_co,
                "rank": row.rank,
                "predictions_count": row.total_predictions,
                "exceptional_tiebreak_points": overrides.get(uid, 0),
                "tiebreaker_status": row.tiebreaker_status,
            }
        )

    return {
        "contest_id": contest_id,
        "round_id": None,
        "round_number": None,
        "leaderboard": rows,
    }


async def get_round_results(
    session: AsyncSession, contest_id: int, round_id: int
) -> dict:
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise ValueError(f"Round {round_id} not found")
    if round_.contest_id != contest_id:
        raise ValueError(f"Round {round_id} does not belong to contest {contest_id}")

    if round_.status not in {RoundStatus.CALCULATED, RoundStatus.PUBLISHED}:
        raise ValueError(f"Round {round_id} results not available (status={round_.status})")

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

    scores = (
        await session.scalars(select(Score).where(Score.round_id == round_id))
    ).all()
    names = await _user_name_map(session)

    results = []
    for score in scores:
        uid = score.user_id
        results.append(
            {
                "user_id": uid,
                "user_name": names.get(uid, str(uid)),
                "points": [],
                "bonus1": score.bonus1,
                "bonus2": score.bonus2,
                "bonus3": score.bonus3,
                "total": score.total_with_bonus3,
                "correct_outcomes": score.correct_outcomes,
            }
        )

    return {"round_id": round_id, "matches": match_out, "results": results}


async def compute_etag(
    session: AsyncSession, *, contest_id: int, round_id: int | None = None
) -> str:
    """Content hash for cache ETag based on score/version state."""
    if round_id is not None:
        max_score_id = await session.scalar(
            select(func.max(Score.id)).where(Score.round_id == round_id)
        )
        round_ = await session.get(Round, round_id)
        payload = {
            "contest_id": contest_id,
            "round_id": round_id,
            "status": round_.status if round_ else None,
            "max_score_id": max_score_id,
        }
    else:
        max_score_id = await session.scalar(
            select(func.max(Score.id))
            .join(Round)
            .where(Round.contest_id == contest_id)
        )
        payload = {"contest_id": contest_id, "global": True, "max_score_id": max_score_id}

    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
