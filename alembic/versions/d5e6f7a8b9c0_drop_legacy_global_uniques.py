"""Drop legacy global UNIQUE on rounds.number and teams.name

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-25 10:00:00.000000

Migration c4d5e6f7a8b9 added per-contest composite uniques via batch recreate but
retained singleton-era global uniques from 0992bb744cc8. This revision recreates
teams and rounds with composite uniques only.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove global UNIQUE(name) and UNIQUE(number); keep per-contest composites."""
    with op.batch_alter_table("teams", recreate="always") as batch_op:
        batch_op.drop_constraint("name", type_="unique")
        batch_op.create_unique_constraint("uq_teams_contest_name", ["contest_id", "name"])

    with op.batch_alter_table("rounds", recreate="always") as batch_op:
        batch_op.drop_constraint("number", type_="unique")
        batch_op.create_unique_constraint("uq_rounds_contest_number", ["contest_id", "number"])


def downgrade() -> None:
    """Restore global uniques — fails if cross-contest duplicate names/numbers exist."""
    with op.batch_alter_table("rounds", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_rounds_contest_number", type_="unique")
        batch_op.create_unique_constraint("number", ["number"])

    with op.batch_alter_table("teams", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_teams_contest_name", type_="unique")
        batch_op.create_unique_constraint("name", ["name"])
