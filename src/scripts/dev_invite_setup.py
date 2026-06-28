"""Dev tooling: export and confirm unconfirmed invitees without SMTP.

Usage::

    uv run python src/scripts/dev_invite_setup.py list-pending
    uv run python src/scripts/dev_invite_setup.py get-unconfirmed --contest-id 2
    uv run python src/scripts/dev_invite_setup.py confirm-list --file src/scripts/dev_unconfirmed.tsv
    uv run python src/scripts/dev_invite_setup.py confirm-all --contest-id 2

When ``ENFORCE_PASSWORD_SETUP=true``, ``confirm-*`` uses ``SEED_SUPERVISOR_PASSWORD``
from ``.env`` unless ``--password`` is passed (password for invited users after setup).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.settings import get_settings  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.setup_tokens import build_setup_url, create_setup_token  # noqa: E402
from database.models import (  # noqa: E402
    Contact,
    Contest,
    ContestParticipant,
    ParticipantStatus,
    User,
    UserRole,
)
from services.auth_setup_service import complete_setup  # noqa: E402

TSV_HEADER = "user_id\tcontest_id\temail\tlogin\n"
DEFAULT_TSV = PROJECT_ROOT / "src" / "scripts" / "dev_unconfirmed.tsv"
DEFAULT_TOKENS = PROJECT_ROOT / "src" / "scripts" / ".tokens"


def _session_factory() -> async_sessionmaker[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


def _unconfirmed_filters():
    return (
        ContestParticipant.status == ParticipantStatus.PENDING,
        User.is_temp_password.is_(True),
        User.role == UserRole.USER.value,
        Contest.deleted_at.is_(None),
    )


def _resolve_confirm_password(explicit: str | None) -> str | None:
    """Password for invited users on complete-setup (dev default: supervisor seed)."""
    if explicit:
        return explicit
    settings = get_settings()
    if not settings.enforce_password_setup:
        return None
    password = settings.seed_supervisor_password
    if not password:
        print(
            "Error: ENFORCE_PASSWORD_SETUP=true but SEED_SUPERVISOR_PASSWORD is not set.",
            file=sys.stderr,
        )
        print("Add it to .env or pass --password explicitly.", file=sys.stderr)
        sys.exit(1)
    return password


async def _fetch_unconfirmed(
    session: AsyncSession, contest_id: int | None
) -> list[dict]:
    stmt = (
        select(
            ContestParticipant.contest_id,
            ContestParticipant.user_id,
            User.login,
            Contact.email,
        )
        .join(User, User.id == ContestParticipant.user_id)
        .join(Contest, Contest.id == ContestParticipant.contest_id)
        .outerjoin(Contact, Contact.user_id == User.id)
        .where(*_unconfirmed_filters())
        .order_by(ContestParticipant.contest_id, User.id)
    )
    if contest_id is not None:
        stmt = stmt.where(ContestParticipant.contest_id == contest_id)

    rows = (await session.execute(stmt)).all()
    return [
        {
            "contest_id": cid,
            "user_id": uid,
            "login": login,
            "email": email or "",
        }
        for cid, uid, login, email in rows
    ]


async def cmd_list_pending() -> None:
    sf = _session_factory()
    async with sf() as session:
        stmt = (
            select(
                ContestParticipant.contest_id,
                Contest.name,
                func.count().label("pending_count"),
            )
            .join(User, User.id == ContestParticipant.user_id)
            .join(Contest, Contest.id == ContestParticipant.contest_id)
            .where(*_unconfirmed_filters())
            .group_by(ContestParticipant.contest_id, Contest.name)
            .order_by(ContestParticipant.contest_id)
        )
        rows = (await session.execute(stmt)).all()

    if not rows:
        print("No contests with pending invites.")
        return

    print("contest_id\tpending\tname")
    for contest_id, name, pending_count in rows:
        print(f"{contest_id}\t{pending_count}\t{name}")


async def cmd_get_unconfirmed(
    contest_id: int | None,
    out_path: Path,
    links_out: Path | None,
) -> None:
    sf = _session_factory()
    async with sf() as session:
        rows = await _fetch_unconfirmed(session, contest_id)

    lines = [TSV_HEADER]
    for row in rows:
        lines.append(
            f"{row['user_id']}\t{row['contest_id']}\t{row['email']}\t{row['login']}\n"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {len(rows)} row(s) to {out_path}")

    if links_out is not None:
        links_out.parent.mkdir(parents=True, exist_ok=True)
        exported_at = datetime.now(UTC).isoformat()
        with links_out.open("a", encoding="utf-8") as handle:
            for row in rows:
                token = create_setup_token(
                    user_id=row["user_id"], contest_id=row["contest_id"]
                )
                record = {
                    "user_id": row["user_id"],
                    "contest_id": row["contest_id"],
                    "login": row["login"],
                    "setup_url": build_setup_url(token),
                    "exported_at": exported_at,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Appended links to {links_out}")


def _read_tsv(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("user_id"):
            continue
        parts = stripped.split("\t")
        if len(parts) < 4:
            continue
        rows.append(
            {
                "user_id": int(parts[0]),
                "contest_id": int(parts[1]),
                "email": parts[2],
                "login": parts[3],
            }
        )
    return rows


async def _confirm_rows(rows: list[dict], password: str | None) -> int:
    sf = _session_factory()
    confirmed = 0
    async with sf() as session:
        for row in rows:
            token = create_setup_token(
                user_id=row["user_id"], contest_id=row["contest_id"]
            )
            result = await complete_setup(session, token, password)
            if result.get("already_completed") or result.get("accepted"):
                confirmed += 1
        await session.commit()
    return confirmed


async def cmd_confirm_list(file_path: Path, password: str | None) -> None:
    rows = _read_tsv(file_path)
    count = await _confirm_rows(rows, password)
    print(f"Confirmed {count} row(s) from {file_path}")


async def cmd_confirm_all(contest_id: int | None, password: str | None) -> None:
    sf = _session_factory()
    async with sf() as session:
        rows = await _fetch_unconfirmed(session, contest_id)
    count = await _confirm_rows(rows, password)
    print(f"Confirmed {count} unconfirmed participant(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dev invite setup helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "list-pending",
        help="Show contest IDs with PENDING temp-password invitees",
    )

    get_p = sub.add_parser("get-unconfirmed", help="Export PENDING temp-password users")
    get_p.add_argument("--contest-id", type=int, default=None)
    get_p.add_argument("--out", type=Path, default=DEFAULT_TSV)
    get_p.add_argument("--links-out", type=Path, default=None)

    list_p = sub.add_parser("confirm-list", help="Confirm rows from TSV")
    list_p.add_argument("--file", type=Path, default=DEFAULT_TSV)
    list_p.add_argument(
        "--password",
        type=str,
        default=None,
        help="New user password (default: SEED_SUPERVISOR_PASSWORD from .env)",
    )

    all_p = sub.add_parser("confirm-all", help="Confirm all unconfirmed invitees")
    all_p.add_argument("--contest-id", type=int, default=None)
    all_p.add_argument(
        "--password",
        type=str,
        default=None,
        help="New user password (default: SEED_SUPERVISOR_PASSWORD from .env)",
    )

    args = parser.parse_args()

    if args.command == "list-pending":
        asyncio.run(cmd_list_pending())
    elif args.command == "get-unconfirmed":
        asyncio.run(cmd_get_unconfirmed(args.contest_id, args.out, args.links_out))
    elif args.command == "confirm-list":
        password = _resolve_confirm_password(args.password)
        asyncio.run(cmd_confirm_list(args.file, password))
    elif args.command == "confirm-all":
        password = _resolve_confirm_password(args.password)
        asyncio.run(cmd_confirm_all(args.contest_id, password))


if __name__ == "__main__":
    main()
