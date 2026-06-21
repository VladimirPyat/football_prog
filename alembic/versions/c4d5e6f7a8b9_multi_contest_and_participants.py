"""Multi-contest schema: contests, contest_participants, contest_id FKs

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace contest_settings with contests and add contest-scoped FKs."""
    op.create_table(
        "contests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_teams", sa.Integer(), nullable=False),
        sa.Column("matches_per_round", sa.Integer(), nullable=False),
        sa.Column("total_rounds", sa.Integer(), nullable=False),
        sa.Column("is_round_robin", sa.Boolean(), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'RUNNING', 'PAUSED', 'FINISHED')",
            name="ck_contests_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.execute(
        """
        INSERT INTO contests (
            id, name, slug, is_locked, status, paused_at, finished_at,
            total_teams, matches_per_round, total_rounds, is_round_robin, rules_json
        )
        SELECT
            id,
            'Default',
            NULL,
            is_locked,
            COALESCE(status, 'DRAFT'),
            paused_at,
            finished_at,
            total_teams,
            matches_per_round,
            total_rounds,
            is_round_robin,
            rules_json
        FROM contest_settings
        """
    )

    op.create_table(
        "contest_participants",
        sa.Column("contest_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACCEPTED"),
        sa.Column(
            "exceptional_tiebreak_points",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.CheckConstraint(
            "exceptional_tiebreak_points >= 0",
            name="ck_contest_participants_tiebreak_nonneg",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED')",
            name="ck_contest_participants_status",
        ),
        sa.ForeignKeyConstraint(["contest_id"], ["contests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("contest_id", "user_id"),
    )

    op.execute(
        """
        INSERT INTO contest_participants (contest_id, user_id, status, exceptional_tiebreak_points)
        SELECT 1, id, 'ACCEPTED', COALESCE(exceptional_tiebreak_points, 0)
        FROM users
        """
    )

    with op.batch_alter_table("teams", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("contest_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_foreign_key(
            "fk_teams_contest_id", "contests", ["contest_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_unique_constraint("uq_teams_contest_name", ["contest_id", "name"])

    op.execute("UPDATE teams SET contest_id = 1")

    with op.batch_alter_table("rounds", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("contest_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_foreign_key(
            "fk_rounds_contest_id", "contests", ["contest_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_unique_constraint("uq_rounds_contest_number", ["contest_id", "number"])

    op.execute("UPDATE rounds SET contest_id = 1")

    op.execute("UPDATE contests SET status = 'RUNNING' WHERE is_locked = TRUE")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_exceptional_tiebreak_nonneg", type_="check")
        batch_op.drop_column("exceptional_tiebreak_points")

    op.drop_table("contest_settings")


def downgrade() -> None:
    """Restore contest_settings singleton schema."""
    op.create_table(
        "contest_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_teams", sa.Integer(), nullable=False),
        sa.Column("matches_per_round", sa.Integer(), nullable=False),
        sa.Column("total_rounds", sa.Integer(), nullable=False),
        sa.Column("is_round_robin", sa.Boolean(), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'RUNNING', 'PAUSED', 'FINISHED')",
            name="ck_contest_settings_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO contest_settings (
            id, is_locked, status, paused_at, finished_at,
            total_teams, matches_per_round, total_rounds, is_round_robin, rules_json
        )
        SELECT
            id, is_locked, status, paused_at, finished_at,
            total_teams, matches_per_round, total_rounds, is_round_robin, rules_json
        FROM contests
        WHERE id = 1
        """
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "exceptional_tiebreak_points",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_check_constraint(
            "ck_users_exceptional_tiebreak_nonneg",
            "exceptional_tiebreak_points >= 0",
        )

    op.execute(
        """
        UPDATE users
        SET exceptional_tiebreak_points = COALESCE((
            SELECT exceptional_tiebreak_points
            FROM contest_participants
            WHERE contest_participants.user_id = users.id
              AND contest_participants.contest_id = 1
        ), 0)
        """
    )

    with op.batch_alter_table("rounds", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_rounds_contest_number", type_="unique")
        batch_op.drop_constraint("fk_rounds_contest_id", type_="foreignkey")
        batch_op.drop_column("contest_id")
        batch_op.create_unique_constraint("number", ["number"])

    with op.batch_alter_table("teams", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_teams_contest_name", type_="unique")
        batch_op.drop_constraint("fk_teams_contest_id", type_="foreignkey")
        batch_op.drop_column("contest_id")
        batch_op.create_unique_constraint("name", ["name"])

    op.drop_table("contest_participants")
    op.drop_table("contests")
