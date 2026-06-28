"""Supplementary (free) round metadata and match origin tracking.

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-28 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("rounds", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(), nullable=False, server_default="REGULAR")
        )
        batch_op.add_column(sa.Column("supplementary_index", sa.Integer(), nullable=True))

    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.add_column(sa.Column("origin_round_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_matches_origin_round_id",
            "rounds",
            ["origin_round_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.drop_constraint("fk_matches_origin_round_id", type_="foreignkey")
        batch_op.drop_column("origin_round_id")

    with op.batch_alter_table("rounds", schema=None) as batch_op:
        batch_op.drop_column("supplementary_index")
        batch_op.drop_column("kind")
