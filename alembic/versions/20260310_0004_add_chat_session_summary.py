"""Add chat session summary fields.

Revision ID: 20260310_0004
Revises: 20260309_0003
Create Date: 2026-03-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260310_0004"
down_revision = "20260309_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    if "summary" not in columns:
        op.add_column("chat_sessions", sa.Column("summary", sa.Text(), nullable=True))
    if "summary_updated_at" not in columns:
        op.add_column("chat_sessions", sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    if "summary_updated_at" in columns:
        op.drop_column("chat_sessions", "summary_updated_at")
    if "summary" in columns:
        op.drop_column("chat_sessions", "summary")
