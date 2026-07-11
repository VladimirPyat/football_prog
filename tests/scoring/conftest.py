"""
CSV loaders and engine-run helpers for stage 1.1 contracted cross-check.

No database, no API — all data comes from docs/test_data/contracted/.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import NamedTuple

import pytest

from src.scoring.engine import score_round
from src.scoring.standings import build_standings
from src.scoring.types import MatchResult, UserPrediction, UserRoundScore, StandingRow

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path("docs/test_data/contracted")
CONFIG_PATH = Path("config/contest_defaults.json")

PREDICTIONS_CSV = DATA_DIR / "predictions.csv"
MATCHES_CSV = DATA_DIR / "matches.csv"
USERS_CSV = DATA_DIR / "users.csv"
TEAMS_CSV = DATA_DIR / "teams.csv"
EXPECTED_SCORES_CSV = DATA_DIR / "expected_scores.csv"
LEADERBOARD_CSV = DATA_DIR / "leaderboard.csv"

SCORED_ROUNDS = list(range(1, 10))  # rounds 1–9 (FINISHED)

# ---------------------------------------------------------------------------
# ID helpers — deterministic, derived from row positions in CSVs
# ---------------------------------------------------------------------------


def _make_match_id(round_number: int, match_num: int) -> int:
    """Deterministic match_id: round * 100 + match_num."""
    return round_number * 100 + match_num


# ---------------------------------------------------------------------------
# Raw CSV readers
# ---------------------------------------------------------------------------


def _read_csv(path: Path, delimiter: str = ";") -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


# ---------------------------------------------------------------------------
# Fixture data structures
# ---------------------------------------------------------------------------


class UserRow(NamedTuple):
    user_id: int
    login: str


class MatchRow(NamedTuple):
    match_id: int
    round_number: int
    home_short: str
    away_short: str
    actual_score1: int | None
    actual_score2: int | None
    is_scorable: bool


class PredictionRow(NamedTuple):
    user_id: int
    match_id: int
    round_number: int
    score1: int
    score2: int


class ExpectedScoreRow(NamedTuple):
    user_id: int
    login: str
    round_number: int
    expected_base_pts: int
    expected_bonus1: int  # contains bonus1 + bonus2 per fixture quirk
    expected_bonus2: int  # always 0 in the fixture
    expected_bonus3: int
    expected_total: int
    expected_rank: int
    count_exact_high: int
    count_exact: int
    count_diff: int
    count_outcome: int


class LeaderboardRow(NamedTuple):
    rank: int
    user_id: int
    login: str
    total_predictions: int
    exact_high_count: int
    exact_count: int
    diff_count: int
    outcome_count: int
    total_without_bonuses: int
    total_bonuses: int
    total_points: int


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rules() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def users() -> list[UserRow]:
    rows = _read_csv(USERS_CSV)
    return [UserRow(user_id=i + 1, login=r["login"]) for i, r in enumerate(rows)]


@pytest.fixture(scope="session")
def login_to_uid(users: list[UserRow]) -> dict[str, int]:
    return {u.login: u.user_id for u in users}


@pytest.fixture(scope="session")
def uid_to_login(users: list[UserRow]) -> dict[int, str]:
    return {u.user_id: u.login for u in users}


@pytest.fixture(scope="session")
def team_short_to_id() -> dict[str, int]:
    rows = _read_csv(TEAMS_CSV, delimiter=",")
    return {r["short_name"]: i + 1 for i, r in enumerate(rows)}


@pytest.fixture(scope="session")
def match_rows() -> list[MatchRow]:
    rows = _read_csv(MATCHES_CSV)
    result = []
    for r in rows:
        rn = int(r["round_number"])
        mn = int(r["match_num"])
        mid = _make_match_id(rn, mn)
        status = r["status"]
        s1_raw = r["actual_score1"].strip()
        s2_raw = r["actual_score2"].strip()
        is_scorable = status == "FINISHED" and s1_raw != "" and s2_raw != ""
        s1 = int(s1_raw) if s1_raw else None
        s2 = int(s2_raw) if s2_raw else None
        result.append(
            MatchRow(
                match_id=mid,
                round_number=rn,
                home_short=r["home_team_short"],
                away_short=r["away_team_short"],
                actual_score1=s1,
                actual_score2=s2,
                is_scorable=is_scorable,
            )
        )
    return result


@pytest.fixture(scope="session")
def prediction_rows(login_to_uid: dict[str, int], match_rows: list[MatchRow]) -> list[PredictionRow]:
    # Build a lookup: (round, home_short, away_short) -> match_id
    match_lookup: dict[tuple[int, str, str], int] = {}
    for mr in match_rows:
        match_lookup[(mr.round_number, mr.home_short, mr.away_short)] = mr.match_id

    rows = _read_csv(PREDICTIONS_CSV)
    result = []
    for r in rows:
        rn = int(r["round_number"])
        uid = login_to_uid[r["user_login"]]
        mid = match_lookup[(rn, r["home_team_short"], r["away_team_short"])]
        result.append(
            PredictionRow(
                user_id=uid,
                match_id=mid,
                round_number=rn,
                score1=int(r["pred_score1"]),
                score2=int(r["pred_score2"]),
            )
        )
    return result


@pytest.fixture(scope="session")
def expected_score_rows(login_to_uid: dict[str, int]) -> list[ExpectedScoreRow]:
    rows = _read_csv(EXPECTED_SCORES_CSV)
    result = []
    for r in rows:
        login = r["user_login"]
        result.append(
            ExpectedScoreRow(
                user_id=login_to_uid[login],
                login=login,
                round_number=int(r["round_number"]),
                expected_base_pts=int(r["expected_base_pts"]),
                expected_bonus1=int(r["expected_bonus1"]),
                expected_bonus2=int(r["expected_bonus2"]),
                expected_bonus3=int(r["expected_bonus3"]),
                expected_total=int(r["expected_total"]),
                expected_rank=int(r["expected_rank"]),
                count_exact_high=int(r["count_exact_high"]),
                count_exact=int(r["count_exact"]),
                count_diff=int(r["count_diff"]),
                count_outcome=int(r["count_outcome"]),
            )
        )
    return result


@pytest.fixture(scope="session")
def leaderboard_rows(login_to_uid: dict[str, int]) -> list[LeaderboardRow]:
    rows = _read_csv(LEADERBOARD_CSV)
    result = []
    for r in rows:
        login = r["user_login"]
        result.append(
            LeaderboardRow(
                rank=int(r["rank"]),
                user_id=login_to_uid[login],
                login=login,
                total_predictions=int(r["total_predictions"]),
                exact_high_count=int(r["exact_high_count"]),
                exact_count=int(r["exact_count"]),
                diff_count=int(r["diff_count"]),
                outcome_count=int(r["outcome_count"]),
                total_without_bonuses=int(r["total_without_bonuses"]),
                total_bonuses=int(r["total_bonuses"]),
                total_points=int(r["total_points"]),
            )
        )
    return result


# ---------------------------------------------------------------------------
# Engine run — score all 9 rounds, build standings
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine_results(
    match_rows: list[MatchRow],
    prediction_rows: list[PredictionRow],
    users: list[UserRow],
    rules: dict,
) -> dict[int, dict[int, UserRoundScore]]:
    """dict[round_number, dict[user_id, UserRoundScore]] for rounds 1–9."""
    participant_ids = [u.user_id for u in users]

    results_by_round: dict[int, dict[int, UserRoundScore]] = {}
    for rn in SCORED_ROUNDS:
        round_match_results = [
            MatchResult(
                match_id=mr.match_id,
                score1=mr.actual_score1,
                score2=mr.actual_score2,
                is_scorable=mr.is_scorable,
            )
            for mr in match_rows
            if mr.round_number == rn
        ]
        round_predictions = [
            UserPrediction(
                user_id=pr.user_id,
                match_id=pr.match_id,
                score1=pr.score1,
                score2=pr.score2,
            )
            for pr in prediction_rows
            if pr.round_number == rn
        ]
        results_by_round[rn] = score_round(
            round_match_results, round_predictions, participant_ids, rules
        )

    return results_by_round


@pytest.fixture(scope="session")
def per_user_rounds(
    engine_results: dict[int, dict[int, UserRoundScore]],
    users: list[UserRow],
) -> dict[int, list[UserRoundScore]]:
    """Aggregate: user_id → list of UserRoundScore across all scored rounds."""
    all_uids = [u.user_id for u in users]
    result: dict[int, list[UserRoundScore]] = {uid: [] for uid in all_uids}
    for rn in SCORED_ROUNDS:
        for uid in all_uids:
            result[uid].append(engine_results[rn][uid])
    return result


@pytest.fixture(scope="session")
def standings(
    per_user_rounds: dict[int, list[UserRoundScore]],
) -> list[StandingRow]:
    return build_standings(per_user_rounds, manual_overrides=None)
