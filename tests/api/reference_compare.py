"""Shared CSV load and DB comparison helpers for Stage 1.4 API tests."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import Round, Score, User

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTED = PROJECT_ROOT / "docs" / "test_data" / "contracted"


def load_expected_scores(path: Path | None = None) -> list[dict[str, str]]:
    csv_path = path or (CONTRACTED / "expected_scores.csv")
    with csv_path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def load_leaderboard(path: Path | None = None) -> list[dict[str, str]]:
    csv_path = path or (CONTRACTED / "leaderboard.csv")
    with csv_path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


async def build_score_lookup(
    sf: async_sessionmaker[AsyncSession],
    contest_id: int,
) -> tuple[dict[str, int], dict[int, int], dict[tuple[int, int], Score]]:
    async with sf() as session:
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
                .where(Round.contest_id == contest_id)
            )
        ).all()
        score_map = {(s.user_id, s.round_id): s for s in scores}

    return login_to_id, round_num_to_id, score_map


def compare_scores_to_expected(
    expected_rows: list[dict[str, str]],
    login_to_id: dict[str, int],
    round_num_to_id: dict[int, int],
    score_map: dict[tuple[int, int], Score],
    *,
    check_counts: bool = False,
) -> tuple[int, list[str]]:
    """Compare persisted scores to expected CSV rows. Returns (matched_count, mismatches)."""
    mismatches: list[str] = []
    matched = 0

    for row in expected_rows:
        login = row["user_login"]
        rnum = int(row["round_number"])
        uid = login_to_id.get(login)
        rid = round_num_to_id.get(rnum)

        if uid is None or rid is None:
            mismatches.append(f"Lookup failed: {login}/round {rnum}")
            continue

        score = score_map.get((uid, rid))
        if score is None:
            mismatches.append(f"Missing Score row: {login}/round {rnum}")
            continue

        exp_base = int(row["expected_base_pts"])
        exp_b12 = int(row["expected_bonus1"])
        exp_b3 = int(row["expected_bonus3"])
        exp_total = int(row["expected_total"])

        assert int(row["expected_bonus2"]) == 0, (
            f"Fixture regression: expected_bonus2 != 0 for {login}/round {rnum}"
        )

        actual_base = score.points_exact + score.points_diff + score.points_outcome
        actual_b12 = score.bonus1 + score.bonus2

        errors: list[str] = []
        if actual_base != exp_base:
            errors.append(f"base: got {actual_base}, want {exp_base}")
        if actual_b12 != exp_b12:
            errors.append(f"bonus1+2: got {actual_b12}, want {exp_b12}")
        if score.bonus3 != exp_b3:
            errors.append(f"bonus3: got {score.bonus3}, want {exp_b3}")
        if score.total_with_bonus3 != exp_total:
            errors.append(f"total: got {score.total_with_bonus3}, want {exp_total}")

        if check_counts:
            for csv_col, attr in (
                ("count_exact_high", "count_exact_high"),
                ("count_exact", "count_exact"),
                ("count_diff", "count_diff"),
                ("count_outcome", "count_outcome"),
            ):
                exp_val = int(row[csv_col])
                act_val = getattr(score, attr)
                if act_val != exp_val:
                    errors.append(f"{attr}: got {act_val}, want {exp_val}")

        if errors:
            mismatches.append(f"{login}/round {rnum}: {'; '.join(errors)}")
        else:
            matched += 1

    return matched, mismatches


def compare_leaderboard_counts(
    leaderboard_rows: list[dict[str, str]],
    login_to_id: dict[str, int],
    score_map: dict[tuple[int, int], Score],
) -> tuple[int, list[str]]:
    """Aggregate count_* per user vs leaderboard.csv — 10/10 gate."""
    agg: dict[int, dict[str, int]] = {}
    for s in score_map.values():
        if s.user_id not in agg:
            agg[s.user_id] = {"eh": 0, "ex": 0, "di": 0, "ou": 0}
        agg[s.user_id]["eh"] += s.count_exact_high
        agg[s.user_id]["ex"] += s.count_exact
        agg[s.user_id]["di"] += s.count_diff
        agg[s.user_id]["ou"] += s.count_outcome

    mismatches: list[str] = []
    matched = 0

    for row in leaderboard_rows:
        login = row["user_login"]
        uid = login_to_id.get(login)
        if uid is None:
            mismatches.append(f"Unknown login in leaderboard: {login}")
            continue

        user_agg = agg.get(uid, {"eh": 0, "ex": 0, "di": 0, "ou": 0})
        exp_eh = int(row["exact_high_count"])
        exp_ex = int(row["exact_count"])
        exp_di = int(row["diff_count"])
        exp_ou = int(row["outcome_count"])

        errors: list[str] = []
        if user_agg["eh"] != exp_eh:
            errors.append(f"exact_high: got {user_agg['eh']}, want {exp_eh}")
        if user_agg["ex"] != exp_ex:
            errors.append(f"exact: got {user_agg['ex']}, want {exp_ex}")
        if user_agg["di"] != exp_di:
            errors.append(f"diff: got {user_agg['di']}, want {exp_di}")
        if user_agg["ou"] != exp_ou:
            errors.append(f"outcome: got {user_agg['ou']}, want {exp_ou}")

        if errors:
            mismatches.append(f"{login}: {'; '.join(errors)}")
        else:
            matched += 1

    return matched, mismatches


async def assert_scores_match_expected(
    sf: async_sessionmaker[AsyncSession],
    contest_id: int,
    *,
    expected_path: Path | None = None,
    expected_total: int = 90,
    check_counts: bool = False,
) -> int:
    """Load DB scores and assert exact match against expected_scores.csv."""
    expected = load_expected_scores(expected_path)
    login_to_id, round_num_to_id, score_map = await build_score_lookup(sf, contest_id)
    matched, mismatches = compare_scores_to_expected(
        expected,
        login_to_id,
        round_num_to_id,
        score_map,
        check_counts=check_counts,
    )
    assert not mismatches, (
        f"[API-RESULTS] {len(mismatches)} mismatches:\n" + "\n".join(mismatches)
    )
    assert matched == expected_total, (
        f"[API-RESULTS] Expected {expected_total} exact matches, got {matched}"
    )
    return matched
