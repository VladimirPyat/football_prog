"""Dev fixture finalizer: publish rounds 1–9, CALCULATED round 10, CLOSED round 11.

Used after load_test_data + bootstrap for manual supervisor QA (Stage 1.14).
Pytest isolation keeps load_test_data defaults (CLOSED 1–9, ACTIVE 10) — finalize runs
only from dev_setup, not from the loader.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from database.engine import create_engine, create_session_factory  # noqa: E402
from database.models import (  # noqa: E402
    Contest,
    ContestLifecycleStatus,
    ContestParticipant,
    Match,
    MatchStatus,
    ParticipantStatus,
    Round,
    RoundStatus,
    Score,
    User,
)
from services.round_service import transition_round  # noqa: E402
from services.scoring_persistence import calculate_round  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_CONTEST_ID = 1
REFERENCE_NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=UTC)
CONTRACTED_USERS_CSV = PROJECT_ROOT / "docs" / "test_data" / "contracted" / "users.csv"

# Synthetic finished results for round 10 (8 matches).
ROUND_10_SYNTHETIC_SCORES: tuple[tuple[int, int], ...] = (
    (1, 0),
    (2, 1),
    (1, 1),
    (0, 0),
    (3, 2),
    (2, 0),
    (1, 2),
    (0, 1),
)


async def _contracted_logins() -> set[str]:
    with CONTRACTED_USERS_CSV.open(newline="", encoding="utf-8") as fh:
        return {row["login"].strip() for row in csv.DictReader(fh, delimiter=";")}


async def _restrict_participants_to_contracted(
    session: AsyncSession, contest_id: int
) -> None:
    """Only contracted CSV users stay ACCEPTED — bootstrap admin/demo must not add score rows."""
    allowed = await _contracted_logins()
    await _apply_participant_allowlist(session, contest_id, allowed)


async def _ensure_demo_user_accepted(
    session: AsyncSession, contest_id: int, *, demo_login: str
) -> None:
    """Re-accept bootstrap demo login after contracted-only scoring (E2E hybrid)."""
    user = await session.scalar(select(User).where(User.login == demo_login))
    if user is None:
        logger.warning("Demo login %s not found — skip ACCEPTED", demo_login)
        return
    part = await session.scalar(
        select(ContestParticipant).where(
            ContestParticipant.contest_id == contest_id,
            ContestParticipant.user_id == user.id,
        )
    )
    if part is None:
        logger.warning("Demo participant missing for %s — skip ACCEPTED", demo_login)
        return
    part.status = ParticipantStatus.ACCEPTED.value
    logger.info("Demo participant %s set ACCEPTED (e2e hybrid)", demo_login)


async def _apply_participant_allowlist(
    session: AsyncSession, contest_id: int, allowed: set[str]
) -> None:
    participants = (
        await session.scalars(
            select(ContestParticipant).where(ContestParticipant.contest_id == contest_id)
        )
    ).all()
    users = {u.id: u for u in (await session.scalars(select(User))).all()}
    for part in participants:
        user = users.get(part.user_id)
        if user is None:
            continue
        if user.login in allowed:
            part.status = ParticipantStatus.ACCEPTED.value
        else:
            part.status = ParticipantStatus.PENDING.value
            logger.info("Participant %s set PENDING for fixture scoring", user.login)


async def _score_count(session: AsyncSession, round_id: int) -> int:
    return int(
        await session.scalar(select(func.count()).select_from(Score).where(Score.round_id == round_id))
        or 0
    )


async def _get_round_by_number(
    session: AsyncSession, contest_id: int, number: int
) -> Round | None:
    return await session.scalar(
        select(Round).where(Round.contest_id == contest_id, Round.number == number)
    )


async def finalize_rounds_1_9_published(
    session: AsyncSession,
    contest_id: int = DEFAULT_CONTEST_ID,
    *,
    validate_expected: bool = True,
) -> None:
    """Calculate and publish rounds 1–9 when scores are missing (idempotent)."""
    for number in range(1, 10):
        round_ = await _get_round_by_number(session, contest_id, number)
        if round_ is None:
            raise RuntimeError(f"Round {number} missing for contest {contest_id}")

        existing = await _score_count(session, round_.id)
        if existing == 0:
            if RoundStatus(round_.status) != RoundStatus.CLOSED:
                raise RuntimeError(
                    f"Round {number} must be CLOSED before calculate (got {round_.status})"
                )
            count = await calculate_round(session, round_.id, contest_id)
            logger.info("Round %s calculated (%s score rows)", number, count)
            assert count == 10, f"Round {number}: expected 10 scores, got {count}"
        elif RoundStatus(round_.status) not in (RoundStatus.CALCULATED, RoundStatus.PUBLISHED):
            raise RuntimeError(
                f"Round {number} has {existing} scores but status={round_.status}"
            )

        if RoundStatus(round_.status) == RoundStatus.CALCULATED:
            await transition_round(session, round_.id, RoundStatus.PUBLISHED)
            logger.info("Round %s published", number)

    if validate_expected:
        await _assert_rounds_1_9_match_expected(session, contest_id)


def _load_reference_compare():
    import importlib.util

    module_path = PROJECT_ROOT / "tests" / "api" / "reference_compare.py"
    spec = importlib.util.spec_from_file_location("reference_compare", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _assert_rounds_1_9_match_expected(session: AsyncSession, contest_id: int) -> None:
    """Compare rounds 1–9 scores to expected_scores.csv (90/90)."""
    ref = _load_reference_compare()
    expected = [row for row in ref.load_expected_scores() if int(row["round_number"]) <= 9]
    users = (await session.scalars(select(User))).all()
    login_to_id = {u.login: u.id for u in users}
    rounds = (
        await session.scalars(select(Round).where(Round.contest_id == contest_id))
    ).all()
    round_num_to_id = {r.number: r.id for r in rounds}
    scores = (
        await session.scalars(
            select(Score)
            .join(Round, Score.round_id == Round.id)
            .where(Round.contest_id == contest_id, Round.number <= 9)
        )
    ).all()
    score_map = {(s.user_id, s.round_id): s for s in scores}

    matched, mismatches = ref.compare_scores_to_expected(
        expected, login_to_id, round_num_to_id, score_map
    )
    if mismatches:
        sample = "\n".join(mismatches[:5])
        raise RuntimeError(f"expected_scores mismatch ({len(mismatches)}): {sample}")
    if matched != 90:
        raise RuntimeError(f"expected 90/90 score matches, got {matched}")


async def finalize_round_10_active_e2e(
    session: AsyncSession,
    contest_id: int = DEFAULT_CONTEST_ID,
) -> None:
    """ACTIVE round 10 with future deadline and no participant scores (E2E hybrid profile)."""
    round_ = await _get_round_by_number(session, contest_id, 10)
    if round_ is None:
        raise RuntimeError("Round 10 missing")

    existing = await _score_count(session, round_.id)
    status = RoundStatus(round_.status)
    now = datetime.now(UTC)

    if status == RoundStatus.ACTIVE and existing == 0 and round_.deadline.replace(tzinfo=UTC) > now:
        matches = (
            await session.scalars(
                select(Match).where(Match.round_id == round_.id).order_by(Match.id)
            )
        ).all()
        if matches and all(m.date_time.replace(tzinfo=UTC) > now for m in matches):
            logger.info("Round 10 already ACTIVE (e2e hybrid) — skip")
            return

    if existing > 0:
        await session.execute(delete(Score).where(Score.round_id == round_.id))
        logger.info("Cleared %s score rows from round 10", existing)

    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise RuntimeError(f"Contest {contest_id} not found")

    matches = (
        await session.scalars(
            select(Match).where(Match.round_id == round_.id).order_by(Match.id)
        )
    ).all()
    if len(matches) != 8:
        raise RuntimeError(f"Round 10 expected 8 matches, got {len(matches)}")

    base = now + timedelta(days=14)
    for i, match in enumerate(matches):
        match.date_time = base + timedelta(hours=i)
        match.score1 = None
        match.score2 = None
        match.status = MatchStatus.SCHEDULED.value

    earliest = min(m.date_time for m in matches)
    deadline_rule_hours: int = contest.rules_json["contest_structure"]["deadline_rule_hours"]
    round_.deadline = earliest - timedelta(hours=deadline_rule_hours)
    round_.status = RoundStatus.ACTIVE.value
    logger.info("Round 10 set ACTIVE with future deadline (e2e hybrid)")


async def finalize_round_10_calculated(
    session: AsyncSession,
    contest_id: int = DEFAULT_CONTEST_ID,
    *,
    reference_now: datetime = REFERENCE_NOW,
) -> None:
    """Finish round 10 matches, close deadline, calculate — leave CALCULATED (not PUBLISHED)."""
    round_ = await _get_round_by_number(session, contest_id, 10)
    if round_ is None:
        raise RuntimeError("Round 10 missing")

    if RoundStatus(round_.status) == RoundStatus.PUBLISHED:
        raise RuntimeError("Round 10 must not be PUBLISHED in manual dev profile")

    existing = await _score_count(session, round_.id)
    if existing > 0 and RoundStatus(round_.status) == RoundStatus.CALCULATED:
        logger.info("Round 10 already CALCULATED with %s scores — skip", existing)
        return

    matches = (
        await session.scalars(
            select(Match).where(Match.round_id == round_.id).order_by(Match.id)
        )
    ).all()
    if len(matches) != 8:
        raise RuntimeError(f"Round 10 expected 8 matches, got {len(matches)}")

    base_kickoff = datetime(2026, 6, 26, 15, 0, 0, tzinfo=UTC)
    for i, match in enumerate(matches):
        s1, s2 = ROUND_10_SYNTHETIC_SCORES[i]
        match.date_time = base_kickoff + timedelta(hours=i)
        match.score1 = s1
        match.score2 = s2
        match.status = MatchStatus.FINISHED.value

    round_.deadline = datetime(2026, 6, 26, 12, 0, 0, tzinfo=UTC)
    round_.status = RoundStatus.CLOSED.value

    if existing == 0:
        count = await calculate_round(session, round_.id, contest_id)
        logger.info("Round 10 calculated (%s score rows)", count)
        assert count == 10, f"Round 10: expected 10 scores, got {count}"
    else:
        round_.status = RoundStatus.CALCULATED.value


async def ensure_round_11_closed(
    session: AsyncSession,
    contest_id: int = DEFAULT_CONTEST_ID,
    *,
    reference_now: datetime = REFERENCE_NOW,
) -> None:
    """Create round 11 (CLOSED, deadline passed) with 8 SCHEDULED matches if missing."""
    existing = await _get_round_by_number(session, contest_id, 11)
    if existing is not None:
        logger.info("Round 11 already exists (status=%s) — skip create", existing.status)
        return

    round_10 = await _get_round_by_number(session, contest_id, 10)
    if round_10 is None:
        raise RuntimeError("Round 10 required to seed round 11 pairings")

    r10_matches = (
        await session.scalars(
            select(Match).where(Match.round_id == round_10.id).order_by(Match.id)
        )
    ).all()

    deadline = datetime(2026, 6, 27, 8, 0, 0, tzinfo=UTC)
    round_11 = Round(
        contest_id=contest_id,
        number=11,
        deadline=deadline,
        status=RoundStatus.CLOSED.value,
        matches_count=8,
    )
    session.add(round_11)
    await session.flush()

    base_kickoff = datetime(2026, 6, 27, 14, 0, 0, tzinfo=UTC)
    for i, src in enumerate(r10_matches[:8]):
        session.add(
            Match(
                round_id=round_11.id,
                team1_id=src.team1_id,
                team2_id=src.team2_id,
                date_time=base_kickoff + timedelta(hours=i),
                score1=None,
                score2=None,
                status=MatchStatus.SCHEDULED.value,
            )
        )

    logger.info("Round 11 created (CLOSED, 8 SCHEDULED matches)")


async def _ensure_contest_running(session: AsyncSession, contest_id: int) -> None:
    contest = await session.get(Contest, contest_id)
    if contest is None:
        raise RuntimeError(f"Contest {contest_id} not found")
    contest.status = ContestLifecycleStatus.RUNNING.value
    contest.is_locked = True


async def finalize_dev_fixture(
    contest_id: int = DEFAULT_CONTEST_ID,
    *,
    profile: str = "manual",
    reference_now: datetime = REFERENCE_NOW,
    validate_expected: bool = True,
) -> None:
    """Orchestrate dev fixture finalize (manual or e2e_with_published profile)."""
    if profile not in ("manual", "e2e_with_published"):
        raise ValueError(f"Unknown profile: {profile!r}")

    from config.settings import get_settings

    demo_login = get_settings().seed_demo_user_login

    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        async with session.begin():
            await _ensure_contest_running(session, contest_id)
            await _restrict_participants_to_contracted(session, contest_id)
            await finalize_rounds_1_9_published(
                session, contest_id, validate_expected=validate_expected
            )
            if profile == "manual":
                await finalize_round_10_calculated(
                    session, contest_id, reference_now=reference_now
                )
            else:
                await finalize_round_10_active_e2e(session, contest_id)
            await ensure_round_11_closed(
                session, contest_id, reference_now=reference_now
            )
            if profile == "e2e_with_published":
                await _ensure_demo_user_accepted(
                    session, contest_id, demo_login=demo_login
                )
    await engine.dispose()
    logger.info("Dev fixture finalized for contest %s (profile=%s)", contest_id, profile)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Finalize dev contest fixture (Stage 1.14)")
    parser.add_argument("--contest-id", type=int, default=DEFAULT_CONTEST_ID)
    parser.add_argument("--no-validate", action="store_true", help="Skip expected_scores.csv check")
    parser.add_argument(
        "--profile",
        choices=("manual", "e2e_with_published"),
        default="manual",
        help="Fixture profile (default: manual supervisor QA)",
    )
    args = parser.parse_args()
    asyncio.run(
        finalize_dev_fixture(
            contest_id=args.contest_id,
            profile=args.profile,
            validate_expected=not args.no_validate,
        )
    )
    print("✅ Dev fixture finalized")


if __name__ == "__main__":
    main()
