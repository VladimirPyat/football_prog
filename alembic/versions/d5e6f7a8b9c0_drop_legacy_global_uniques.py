"""Drop legacy global UNIQUE on rounds.number and teams.name

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-25 10:00:00.000000

Migration c4d5e6f7a8b9 added per-contest composite uniques via batch recreate but
retained singleton-era global uniques from 0992bb744cc8 on some upgrade paths.
Fresh installs after c4d5 already have composite uniques only — this revision
skips work when legacy globals are absent.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _unique_names(table: str) -> set[str]:
    inspector = inspect(op.get_bind())
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table)
        if constraint.get("name")
    }


def upgrade() -> None:
    """Remove global UNIQUE(name/number) when present; ensure per-contest composites."""
    team_uniques = _unique_names("teams")
    if "name" in team_uniques or "uq_teams_contest_name" not in team_uniques:
        with op.batch_alter_table("teams", recreate="always") as batch_op:
            if "name" in team_uniques:
                batch_op.drop_constraint("name", type_="unique")
            if "uq_teams_contest_name" not in team_uniques:
                batch_op.create_unique_constraint("uq_teams_contest_name", ["contest_id", "name"])

    round_uniques = _unique_names("rounds")
    if "number" in round_uniques or "uq_rounds_contest_number" not in round_uniques:
        with op.batch_alter_table("rounds", recreate="always") as batch_op:
            if "number" in round_uniques:
                batch_op.drop_constraint("number", type_="unique")
            if "uq_rounds_contest_number" not in round_uniques:
                batch_op.create_unique_constraint("uq_rounds_contest_number", ["contest_id", "number"])


def downgrade() -> None:
    """Restore global uniques — fails if cross-contest duplicate names/numbers exist."""
    with op.batch_alter_table("rounds", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_rounds_contest_number", type_="unique")
        batch_op.create_unique_constraint("number", ["number"])

    with op.batch_alter_table("teams", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_teams_contest_name", type_="unique")
        batch_op.create_unique_constraint("name", ["name"])
