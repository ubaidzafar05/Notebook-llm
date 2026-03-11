"""Add notebook usage analytics table.

Revision ID: 20260310_0005
Revises: 20260310_0004
Create Date: 2026-03-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260310_0005"
down_revision = "20260310_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "notebook_usage" in inspector.get_table_names():
        return
    if bind.dialect.name == "sqlite":
        now_default = sa.text("CURRENT_TIMESTAMP")
    else:
        now_default = sa.text("now()")
    op.create_table(
        "notebook_usage",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("notebook_id", sa.String(length=36), sa.ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("total_messages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sources", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_prompt_tokens_est", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_response_tokens_est", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now_default),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "notebook_usage" not in inspector.get_table_names():
        return
    op.drop_table("notebook_usage")
