"""Add count_* columns to scores table

Revision ID: a2b3c4d5e6f7
Revises: 0992bb744cc8
Create Date: 2026-06-11 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "0992bb744cc8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add per-category count columns to the scores table."""
    op.add_column("scores", sa.Column("count_exact_high", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scores", sa.Column("count_exact", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scores", sa.Column("count_diff", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scores", sa.Column("count_outcome", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    """Drop per-category count columns from the scores table."""
    op.drop_column("scores", "count_outcome")
    op.drop_column("scores", "count_diff")
    op.drop_column("scores", "count_exact")
    op.drop_column("scores", "count_exact_high")
