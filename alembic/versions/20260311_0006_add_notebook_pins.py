"""Add notebook pinning fields.

Revision ID: 20260311_0006
Revises: 20260310_0005
Create Date: 2026-03-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0006"
down_revision = "20260310_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notebooks",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "notebooks",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notebooks", "pinned_at")
    op.drop_column("notebooks", "is_pinned")
