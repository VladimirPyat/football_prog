"""Add contest lifecycle columns and exceptional tie-break points

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-06-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add lifecycle columns to contest_settings and tie-break points to users."""
    with op.batch_alter_table("contest_settings") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        )
        batch_op.add_column(
            sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.create_check_constraint(
            "ck_contest_settings_status",
            "status IN ('DRAFT', 'RUNNING', 'PAUSED', 'FINISHED')",
        )

    op.execute(
        "UPDATE contest_settings SET status = 'RUNNING' WHERE is_locked = TRUE"
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "exceptional_tiebreak_points",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
        batch_op.create_check_constraint(
            "ck_users_exceptional_tiebreak_nonneg",
            "exceptional_tiebreak_points >= 0",
        )


def downgrade() -> None:
    """Remove lifecycle columns from contest_settings and tie-break points from users."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_exceptional_tiebreak_nonneg", type_="check")
        batch_op.drop_column("exceptional_tiebreak_points")

    with op.batch_alter_table("contest_settings") as batch_op:
        batch_op.drop_constraint("ck_contest_settings_status", type_="check")
        batch_op.drop_column("finished_at")
        batch_op.drop_column("paused_at")
        batch_op.drop_column("status")
