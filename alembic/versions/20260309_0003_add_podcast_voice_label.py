"""Add podcast voice label field.

Revision ID: 20260309_0003
Revises: 20260306_0002
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260309_0003"
down_revision = "20260306_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("podcast_jobs")}
    if "voice_label" in columns:
        return
    op.add_column("podcast_jobs", sa.Column("voice_label", sa.String(length=64), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("podcast_jobs")}
    if "voice_label" not in columns:
        return
    op.drop_column("podcast_jobs", "voice_label")
