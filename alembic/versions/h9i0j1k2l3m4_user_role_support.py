"""Rename users.role ADMIN -> SUPPORT.

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-07-11 01:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "h9i0j1k2l3m4"
down_revision: str | Sequence[str] | None = "g8h9i0j1k2l3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'SUPPORT' WHERE role = 'ADMIN'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SUPPORT'")
