"""Leaderboard aggregation, results matrix, and HTTP cache ETag helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ContestRuleError, NotFoundError
from database.models import (
    ContestParticipant,
    Match,
    Prediction,
    Round,
    RoundStatus,
    Score,
    Team,
    User,
)
from scoring.standings import build_standings
from scoring.types import UserRoundScore
from services.round_auto_close_service import ensure_round_closed_if_expired
from services.round_scoring_pending import origin_round_bonuses_pending
from services.scoring_persistence import compute_round_user_scores
from services.team_display import match_team_fields

logger = logging.getLogger(__name__)

_STAFF_ROLES: frozenset[str] = frozenset({"SUPERVISOR", "SUPPORT"})
LeaderboardScope = frozenset({"round", "total"})


def _allowed_round_statuses(viewer_role: str | None) -> set[RoundStatus]:
    if viewer_role in _STAFF_ROLES:
        return {RoundStatus.CALCULATED, RoundStatus.PUBLISHED}
    return {RoundStatus.PUBLISHED}


def _assert_round_visible(round_: Round, viewer_role: str | None) -> None:
    allowed = _allowed_round_statuses(viewer_role)
    if RoundStatus(round_.status) not in allowed:
        raise ContestRuleError(
            f"Таблица тура недоступна (статус: {round_.status})",
            code="RESULTS_NOT_AVAILABLE",
        )


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


def _tiebreak_points(
    user_id: int, overrides: dict[int, int], *, context: str
) -> int:
    if user_id not in overrides:
        logger.warning(
            "participant missing for tiebreak user_id=%s context=%s — using 0",
            user_id,
            context,
        )
        return 0
    return overrides[user_id]


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


async def _prediction_counts(
    session: AsyncSession, contest_id: int, round_ids: list[int]
) -> dict[int, int]:
    if not round_ids:
        return {}
    rows = await session.execute(
        select(Prediction.user_id, func.count())
        .join(Round, Prediction.round_id == Round.id)
        .where(Round.contest_id == contest_id, Prediction.round_id.in_(round_ids))
        .group_by(Prediction.user_id)
    )
    return {int(user_id): int(count) for user_id, count in rows.all()}


def _total_bonus_points(bonus1: int, bonus2: int, bonus3: int) -> int:
    return bonus1 + bonus2 + bonus3


def _build_leaderboard_rows(
    scores: list[Score],
    names: dict[int, str],
    overrides: dict[int, int],
    prediction_counts: dict[int, int],
    *,
    aggregate: bool,
    context: str,
) -> list[dict]:
    per_user: dict[int, list[UserRoundScore]] = {}
    for s in scores:
        per_user.setdefault(s.user_id, []).append(_score_to_user_round(s))

    standings = build_standings(per_user, overrides)
    rows: list[dict] = []
    for row in standings:
        uid = row.user_id
        user_scores = [s for s in scores if s.user_id == uid]
        if aggregate:
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
                    "total_bonus_points": _total_bonus_points(total_b1, total_b2, total_b3),
                    "total_without_bonus3": total_wo_b3,
                    "total_with_bonus3": total_w_b3,
                    "correct_outcomes": total_co,
                    "rank": row.rank,
                    "predictions_count": prediction_counts.get(uid, 0),
                    "exceptional_tiebreak_points": _tiebreak_points(uid, overrides, context=context),
                    "tiebreaker_status": row.tiebreaker_status,
                    "count_exact_high": row.exact_high_count,
                    "count_exact": row.exact_count,
                    "count_diff": row.diff_count,
                    "count_outcome": row.outcome_count,
                }
            )
        else:
            sr = user_scores[0] if user_scores else None
            b1 = sr.bonus1 if sr else 0
            b2 = sr.bonus2 if sr else 0
            b3 = sr.bonus3 if sr else 0
            rows.append(
                {
                    "user_id": uid,
                    "user_name": names.get(uid, str(uid)),
                    "points_base": sr.points_exact + sr.points_diff + sr.points_outcome if sr else 0,
                    "bonus1": b1,
                    "bonus2": b2,
                    "bonus3": b3,
                    "total_bonus_points": _total_bonus_points(b1, b2, b3),
                    "total_without_bonus3": sr.total_without_bonus3 if sr else 0,
                    "total_with_bonus3": sr.total_with_bonus3 if sr else 0,
                    "correct_outcomes": sr.correct_outcomes if sr else 0,
                    "rank": row.rank,
                    "predictions_count": prediction_counts.get(uid, 0),
                    "exceptional_tiebreak_points": _tiebreak_points(uid, overrides, context=context),
                    "tiebreaker_status": row.tiebreaker_status,
                    "count_exact_high": sr.count_exact_high if sr else 0,
                    "count_exact": sr.count_exact if sr else 0,
                    "count_diff": sr.count_diff if sr else 0,
                    "count_outcome": sr.count_outcome if sr else 0,
                }
            )
    return rows


async def _rounds_for_leaderboard_scope(
    session: AsyncSession,
    contest_id: int,
    selected_round: Round,
    *,
    scope: str,
    viewer_role: str | None,
) -> list[Round]:
    allowed = _allowed_round_statuses(viewer_role)
    allowed_values = {s.value for s in allowed}
    stmt = select(Round).where(
        Round.contest_id == contest_id,
        Round.status.in_(allowed_values),
    )
    if scope == "total":
        stmt = stmt.where(Round.number <= selected_round.number)
    else:
        stmt = stmt.where(Round.id == selected_round.id)
    return list((await session.scalars(stmt.order_by(Round.number))).all())


async def get_round_leaderboard(
    session: AsyncSession,
    contest_id: int,
    round_id: int,
    *,
    viewer_role: str | None = None,
    scope: str = "round",
) -> dict:
    round_ = await ensure_round_closed_if_expired(session, round_id)
    if round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не принадлежит конкурсу {contest_id}")

    _assert_round_visible(round_, viewer_role)

    if scope not in LeaderboardScope:
        raise ContestRuleError(f"Неизвестный scope: {scope}", code="VALIDATION_ERROR")

    counted_rounds = await _rounds_for_leaderboard_scope(
        session, contest_id, round_, scope=scope, viewer_role=viewer_role
    )
    round_ids = [r.id for r in counted_rounds]
    scores = (
        await session.scalars(select(Score).where(Score.round_id.in_(round_ids)))
    ).all() if round_ids else []
    names = await _user_name_map(session)
    overrides = await _manual_overrides(session, contest_id)
    pred_counts = await _prediction_counts(session, contest_id, round_ids)

    rows = _build_leaderboard_rows(
        list(scores),
        names,
        overrides,
        pred_counts,
        aggregate=scope == "total",
        context=f"round_leaderboard round={round_id} scope={scope}",
    )

    pending, pending_message = await origin_round_bonuses_pending(session, round_id)

    return {
        "contest_id": contest_id,
        "round_id": round_id,
        "round_number": round_.number,
        "bonuses_pending": pending,
        "bonuses_pending_message": pending_message,
        "leaderboard": rows,
    }


async def get_global_leaderboard(session: AsyncSession, contest_id: int) -> dict:
    rounds = (
        await session.scalars(
            select(Round).where(
                Round.contest_id == contest_id,
                Round.status == RoundStatus.PUBLISHED.value,
            )
        )
    ).all()
    round_ids = [r.id for r in rounds]
    scores = (
        await session.scalars(select(Score).where(Score.round_id.in_(round_ids)))
    ).all() if round_ids else []
    names = await _user_name_map(session)
    overrides = await _manual_overrides(session, contest_id)
    pred_counts = await _prediction_counts(session, contest_id, round_ids)

    rows = _build_leaderboard_rows(
        list(scores),
        names,
        overrides,
        pred_counts,
        aggregate=True,
        context=f"global_leaderboard contest={contest_id}",
    )

    return {
        "contest_id": contest_id,
        "round_id": None,
        "round_number": None,
        "leaderboard": rows,
    }


async def get_round_results(
    session: AsyncSession, contest_id: int, round_id: int, *, viewer_role: str | None = None
) -> dict:
    round_ = await ensure_round_closed_if_expired(session, round_id)
    if round_.contest_id != contest_id:
        raise NotFoundError(f"Тур {round_id} не принадлежит конкурсу {contest_id}")

    _assert_round_visible(round_, viewer_role)

    matches = (
        await session.scalars(select(Match).where(Match.round_id == round_id))
    ).all()
    team_ids = {m.team1_id for m in matches} | {m.team2_id for m in matches}
    teams = {
        t.id: t
        for t in (await session.scalars(select(Team).where(Team.id.in_(team_ids)))).all()
    }

    match_out: list[dict] = []
    match_ids: list[int] = []
    for m in matches:
        match_ids.append(m.id)
        match_out.append(
            {
                "id": m.id,
                **match_team_fields(teams, m.team1_id, m.team2_id),
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

    t0 = time.perf_counter()
    engine_scores = await compute_round_user_scores(session, round_id, contest_id)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if elapsed_ms > 100:
        logger.debug(
            "compute_round_user_scores round_id=%s took %.1fms",
            round_id,
            elapsed_ms,
        )

    results = []
    for score in scores:
        uid = score.user_id
        user_round = engine_scores.get(uid)
        per_match = {
            ms.match_id: ms.base_points
            for ms in (user_round.per_match if user_round else ())
        }
        points = [{"match_id": mid, "base_points": per_match.get(mid)} for mid in match_ids]
        persisted_base = score.points_exact + score.points_diff + score.points_outcome
        computed_base = sum(p["base_points"] or 0 for p in points)
        if persisted_base != computed_base:
            logger.warning(
                "round results per-match base sum mismatch user_id=%s round_id=%s "
                "persisted=%s computed=%s",
                uid,
                round_id,
                persisted_base,
                computed_base,
            )
        results.append(
            {
                "user_id": uid,
                "user_name": names.get(uid, str(uid)),
                "points": points,
                "bonus1": score.bonus1,
                "bonus2": score.bonus2,
                "bonus3": score.bonus3,
                "total_without_bonus3": score.total_without_bonus3,
                "total": score.total_with_bonus3,
                "correct_outcomes": score.correct_outcomes,
            }
        )

    return {"round_id": round_id, "matches": match_out, "results": results}


async def compute_etag(
    session: AsyncSession,
    *,
    contest_id: int,
    round_id: int | None = None,
    scope: str = "round",
) -> str:
    """Content hash for cache ETag based on score/version state."""
    contest_max_score_id = await session.scalar(
        select(func.max(Score.id))
        .join(Round, Score.round_id == Round.id)
        .where(Round.contest_id == contest_id)
    )
    if round_id is not None:
        round_ = await session.get(Round, round_id)
        payload = {
            "contest_id": contest_id,
            "round_id": round_id,
            "scope": scope,
            "status": round_.status if round_ else None,
            "max_score_id": contest_max_score_id,
        }
    else:
        payload = {
            "contest_id": contest_id,
            "global": True,
            "max_score_id": contest_max_score_id,
        }

    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
