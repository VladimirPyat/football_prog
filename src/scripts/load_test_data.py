"""Load contracted test-data CSVs into the database.

Usage:
    uv run python src/scripts/load_test_data.py [--reset] [--database-url URL]

Design decisions:
- All mapping/format config lives in config/test_data_loader.json (not in code).
- Entities are persisted by DB id; name strings are used only as display / lookup keys.
- Round 10 is set to ACTIVE status so that deadline/batch tests have an open round to work with.
  Rounds 1–9 are CLOSED (all matches finished).
- Predictions: one row per CSV line only. Absence = no row. Never insert NULL/0 as sentinel.
- --reset: DELETE in FK-safe dependency order before reloading, making reruns idempotent.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for _p in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.base import Base
from database.engine import create_engine, create_session_factory
from database.models import (
    Contact,
    Contest,
    ContestParticipant,
    Match,
    MatchStatus,
    ParticipantStatus,
    Prediction,
    Round,
    RoundStatus,
    Score,
    Team,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

_PLACEHOLDER_PASSWORD_HASH = "test-data-placeholder-hash-not-for-auth"

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _load_loader_config(project_root: Path) -> dict:
    config_path = project_root / "config" / "test_data_loader.json"
    with config_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_contest_defaults(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Reset helpers
# ---------------------------------------------------------------------------


async def _reset_tables(session: AsyncSession) -> None:
    """Delete all loaded data in FK-safe dependency order."""
    for table in (
        "predictions",
        "scores",
        "matches",
        "rounds",
        "contacts",
        "users",
        "teams",
        "contest_participants",
        "contests",
    ):
        await session.execute(text(f"DELETE FROM {table}"))  # noqa: S608
    logger.info("All loaded tables cleared")


# ---------------------------------------------------------------------------
# Contest-settings seed (reused from src/scripts/seed.py logic)
# ---------------------------------------------------------------------------


def _build_rules_json(data: dict) -> dict:
    return {
        "scoring_rules": data["scoring_rules"],
        "tiebreakers": data["tiebreakers"],
        "constraints": data["constraints"],
        "contest_structure": data["contest_structure"],
    }


async def _seed_contest(session: AsyncSession, defaults_path: Path) -> Contest:
    data = _load_contest_defaults(defaults_path)
    structure = data["contest_structure"]
    contest = Contest(
        name="Default",
        slug=None,
        is_locked=False,
        total_teams=structure["total_teams"],
        matches_per_round=structure["matches_per_round"],
        total_rounds=structure["total_rounds"],
        is_round_robin=structure["is_round_robin"],
        rules_json=_build_rules_json(data),
    )
    session.add(contest)
    await session.flush()
    logger.info("Seeded contest (id=%s)", contest.id)
    return contest


# ---------------------------------------------------------------------------
# CSV readers
# ---------------------------------------------------------------------------


def _read_csv(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        rows = list(reader)
    return rows


def _parse_dt(value: str, fmt: str, tz_name: str) -> datetime:
    """Parse a datetime string per loader config format into an aware datetime."""
    dt = datetime.strptime(value.strip(), fmt)
    if tz_name.upper() == "UTC":
        return dt.replace(tzinfo=timezone.utc)
    raise ValueError(f"Unsupported timezone in config: {tz_name}")


# ---------------------------------------------------------------------------
# Entity loaders
# ---------------------------------------------------------------------------


async def _load_teams(
    session: AsyncSession,
    contest_id: int,
    data_dir: Path,
    file_cfg: dict,
) -> dict[str, int]:
    """Load teams. Returns short_name → team_id map."""
    path = data_dir / file_cfg["name"]
    rows = _read_csv(path, file_cfg["delimiter"])

    short_to_id: dict[str, int] = {}
    seen_short: set[str] = set()

    for row in rows:
        short = row["short_name"].strip()
        full = row["full_name"].strip()
        logo = row.get("logo_url", "").strip() or None

        if not short or not full:
            raise ValueError(f"Invalid team row (missing short_name/full_name): {row}")
        if short in seen_short:
            raise ValueError(f"Duplicate team short_name in CSV: {short!r}")
        seen_short.add(short)

        team = Team(contest_id=contest_id, name=full, short_name=short, logo_url=logo)
        session.add(team)
        await session.flush()
        short_to_id[short] = team.id
        logger.debug("Team %s → id=%s", short, team.id)

    return short_to_id


async def _load_users(
    session: AsyncSession,
    data_dir: Path,
    file_cfg: dict,
    name_split_strategy: str,
    default_role: str,
) -> dict[str, int]:
    """Load users and contacts. Returns login → user_id map."""
    path = data_dir / file_cfg["name"]
    rows = _read_csv(path, file_cfg["delimiter"])

    login_to_id: dict[str, int] = {}
    seen_logins: set[str] = set()

    for row in rows:
        login = row["login"].strip()
        full_name = row["full_name"].strip()
        email = row.get("email", "").strip() or None
        is_temp = row.get("is_temp_password", "false").strip().lower() == "true"

        if not login or not full_name:
            raise ValueError(f"Invalid user row (missing login/full_name): {row}")
        if login in seen_logins:
            raise ValueError(f"Duplicate login in CSV: {login!r}")
        seen_logins.add(login)

        # Apply name-split strategy from config.
        if name_split_strategy == "last_name_only":
            last_name = full_name
            first_name = ""
        else:
            raise ValueError(f"Unknown user_name_split strategy: {name_split_strategy!r}")

        user = User(
            login=login,
            password_hash=_PLACEHOLDER_PASSWORD_HASH,
            role=default_role,
            first_name=first_name,
            last_name=last_name,
            is_temp_password=is_temp,
        )
        session.add(user)
        await session.flush()

        if email:
            contact = Contact(user_id=user.id, email=email)
            session.add(contact)

        login_to_id[login] = user.id
        logger.debug("User %s → id=%s", login, user.id)

    return login_to_id


async def _load_matches_and_rounds(
    session: AsyncSession,
    contest_id: int,
    data_dir: Path,
    file_cfg: dict,
    short_to_id: dict[str, int],
    dt_format: str,
    dt_timezone: str,
    deadline_rule_hours: int,
) -> dict[tuple[int, str, str], int]:
    """Load rounds and matches. Returns (round_number, home_short, away_short) → match_id map."""
    path = data_dir / file_cfg["name"]
    rows = _read_csv(path, file_cfg["delimiter"])

    # Group rows by round_number.
    from collections import defaultdict
    round_rows: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        rn = int(row["round_number"].strip())
        round_rows[rn].append(row)

    match_key_to_id: dict[tuple[int, str, str], int] = {}

    for round_number in sorted(round_rows.keys()):
        match_rows = round_rows[round_number]

        # Parse all match datetimes to determine earliest and round deadline.
        parsed_dts: list[datetime] = []
        for row in match_rows:
            dt = _parse_dt(row["scheduled_at"].strip(), dt_format, dt_timezone)
            parsed_dts.append(dt)

        earliest_dt = min(parsed_dts)
        deadline = earliest_dt - timedelta(hours=deadline_rule_hours)

        # Rounds 1–9 are CLOSED (all matches finished).
        # Round 10 is ACTIVE so that deadline/batch tests have an open round.
        # This is a deliberate test-data convention, not production logic.
        if round_number < 10:
            round_status = RoundStatus.CLOSED
        else:
            round_status = RoundStatus.ACTIVE

        round_ = Round(
            contest_id=contest_id,
            number=round_number,
            deadline=deadline,
            status=round_status,
            matches_count=len(match_rows),
        )
        session.add(round_)
        await session.flush()
        logger.debug("Round %s → id=%s (status=%s)", round_number, round_.id, round_status)

        for row in match_rows:
            home_short = row["home_team_short"].strip()
            away_short = row["away_team_short"].strip()
            status_str = row["status"].strip()
            dt = _parse_dt(row["scheduled_at"].strip(), dt_format, dt_timezone)

            if home_short not in short_to_id:
                raise ValueError(f"Unknown home team short_name {home_short!r} in row: {row}")
            if away_short not in short_to_id:
                raise ValueError(f"Unknown away team short_name {away_short!r} in row: {row}")

            match_status = MatchStatus(status_str)

            # Store NULL scores for non-FINISHED matches regardless of CSV values.
            # 0:0 in CSV for SCHEDULED matches is a placeholder, not a real result.
            if match_status == MatchStatus.FINISHED:
                raw1 = row["actual_score1"].strip()
                raw2 = row["actual_score2"].strip()
                if raw1 == "" or raw2 == "":
                    raise ValueError(
                        f"FINISHED match missing scores in row: {row}"
                    )
                score1: int | None = int(raw1)
                score2: int | None = int(raw2)
            else:
                score1 = None
                score2 = None

            match = Match(
                round_id=round_.id,
                team1_id=short_to_id[home_short],
                team2_id=short_to_id[away_short],
                date_time=dt,
                score1=score1,
                score2=score2,
                status=match_status,
            )
            session.add(match)
            await session.flush()

            match_key_to_id[(round_number, home_short, away_short)] = match.id
            logger.debug(
                "Match %s vs %s (round %s) → id=%s", home_short, away_short, round_number, match.id
            )

    return match_key_to_id


async def _load_predictions(
    session: AsyncSession,
    data_dir: Path,
    file_cfg: dict,
    login_to_id: dict[str, int],
    match_key_to_id: dict[tuple[int, str, str], int],
    round_number_to_id: dict[int, int],
) -> int:
    """Load predictions. Returns count of inserted rows.

    Inserts ONLY where a CSV row exists.
    Absence = no row; never write NULL or 0:0 as sentinel.
    """
    path = data_dir / file_cfg["name"]
    rows = _read_csv(path, file_cfg["delimiter"])

    count = 0
    for row in rows:
        login = row["user_login"].strip()
        round_number = int(row["round_number"].strip())
        home_short = row["home_team_short"].strip()
        away_short = row["away_team_short"].strip()
        score1 = int(row["pred_score1"].strip())
        score2 = int(row["pred_score2"].strip())

        if login not in login_to_id:
            raise ValueError(f"Unknown user login {login!r} in prediction row: {row}")

        match_key = (round_number, home_short, away_short)
        if match_key not in match_key_to_id:
            raise ValueError(
                f"Unknown match key {match_key!r} in prediction row: {row}"
            )

        round_id = round_number_to_id[round_number]
        prediction = Prediction(
            user_id=login_to_id[login],
            round_id=round_id,
            match_id=match_key_to_id[match_key],
            score1=score1,
            score2=score2,
        )
        session.add(prediction)
        count += 1

    await session.flush()
    return count


async def _load_participants(
    session: AsyncSession, contest_id: int, login_to_id: dict[str, int]
) -> int:
    """Create ACCEPTED contest_participants for all loaded users."""
    count = 0
    for user_id in login_to_id.values():
        session.add(
            ContestParticipant(
                contest_id=contest_id,
                user_id=user_id,
                status=ParticipantStatus.ACCEPTED,
            )
        )
        count += 1
    await session.flush()
    return count


# ---------------------------------------------------------------------------
# Main loader entry point
# ---------------------------------------------------------------------------


async def run_load(
    database_url: str | None = None,
    config_path: Path | None = None,
    reset: bool = False,
) -> None:
    """Load all test CSV data into the database.

    Parameters
    ----------
    database_url:
        Async SQLAlchemy URL. Defaults to settings.database_url.
    config_path:
        Path to test_data_loader.json. Defaults to config/test_data_loader.json in project root.
    reset:
        If True, truncate all loaded tables before inserting (idempotent reloads).
    """
    app_settings = get_settings()
    db_url = database_url or app_settings.database_url
    cfg_path = config_path or (PROJECT_ROOT / "config" / "test_data_loader.json")

    loader_cfg = _load_loader_config(PROJECT_ROOT) if config_path is None else json.loads(cfg_path.read_text())
    data_dir = PROJECT_ROOT / loader_cfg["data_dir"]
    files = loader_cfg["files"]
    name_split_strategy = loader_cfg["user_name_split"]["strategy"]
    dt_format = loader_cfg["datetime"]["format"]
    dt_timezone = loader_cfg["datetime"]["timezone"]
    default_role = loader_cfg["default_user_role"]

    defaults_path = app_settings.contest_defaults_path
    contest_data = _load_contest_defaults(defaults_path)
    deadline_rule_hours: int = contest_data["contest_structure"]["deadline_rule_hours"]

    engine = create_engine(db_url)
    session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        async with session.begin():
            if reset:
                await _reset_tables(session)

            contest = await _seed_contest(session, defaults_path)
            contest_id = contest.id

            short_to_id = await _load_teams(session, contest_id, data_dir, files["teams"])
            login_to_id = await _load_users(
                session,
                data_dir,
                files["users"],
                name_split_strategy=name_split_strategy,
                default_role=default_role,
            )

            match_key_to_id = await _load_matches_and_rounds(
                session,
                contest_id,
                data_dir,
                files["matches"],
                short_to_id=short_to_id,
                dt_format=dt_format,
                dt_timezone=dt_timezone,
                deadline_rule_hours=deadline_rule_hours,
            )

            # Build round_number → round_id map from the inserted matches.
            round_numbers = {key[0] for key in match_key_to_id}
            from sqlalchemy import select as _select
            from database.models import Round as _Round
            round_rows = (
                await session.scalars(_select(_Round).where(_Round.number.in_(round_numbers)))
            ).all()
            round_number_to_id = {r.number: r.id for r in round_rows}

            pred_count = await _load_predictions(
                session,
                data_dir,
                files["predictions"],
                login_to_id=login_to_id,
                match_key_to_id=match_key_to_id,
                round_number_to_id=round_number_to_id,
            )

            await _load_participants(session, contest_id, login_to_id)

    await engine.dispose()

    team_count = len(short_to_id)
    user_count = len(login_to_id)
    match_count = len(match_key_to_id)
    logger.info(
        "Loaded: %d teams, %d users, %d matches, %d predictions",
        team_count,
        user_count,
        match_count,
        pred_count,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Load contracted test-data CSVs into DB")
    parser.add_argument("--reset", action="store_true", help="Truncate loaded tables before reloading")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Async SQLAlchemy database URL (defaults to DATABASE_URL env / settings)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_load(database_url=args.database_url, reset=args.reset))
    except Exception as exc:
        print(f"❌ Load failed: {exc}", file=sys.stderr)
        logger.exception("Load failed")
        sys.exit(1)

    print("✅ Data loaded successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
