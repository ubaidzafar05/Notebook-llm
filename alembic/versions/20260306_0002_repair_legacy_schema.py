"""Repair legacy schema for notebook-scoped data.

Revision ID: 20260306_0002
Revises: 20260306_0001
Create Date: 2026-03-06

This migration is intentionally defensive.
- Some users may have an older DB where parts of the schema exist (e.g. users/sources)
  but notebook-scoped tables/columns are missing.
- For Postgres, we create missing tables/columns and backfill default notebooks.
- For SQLite (tests), the initial migration already creates the full schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260306_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "notebooks" not in table_names:
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS notebooks (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NULL,
                    is_default BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                );
                """
            )
        )
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_notebooks_user_id ON notebooks (user_id);"))

    _add_column_if_missing(inspector, "sources", "notebook_id", "VARCHAR(36)")
    _add_column_if_missing(inspector, "chunks", "notebook_id", "VARCHAR(36)")
    _add_column_if_missing(inspector, "chat_sessions", "notebook_id", "VARCHAR(36)")
    _add_column_if_missing(inspector, "jobs", "notebook_id", "VARCHAR(36)")
    _add_column_if_missing(inspector, "podcast_jobs", "notebook_id", "VARCHAR(36)")

    _backfill_default_notebooks(bind)


def downgrade() -> None:
    # Non-destructive repair migration; do not attempt to drop columns/tables.
    pass


def _add_column_if_missing(inspector: sa.Inspector, table: str, column: str, col_sql: str) -> None:
    if table not in set(inspector.get_table_names()):
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column in existing:
        return
    op.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_sql}"))


def _backfill_default_notebooks(bind: sa.engine.Connection) -> None:
    # Create one default notebook per user if missing.
    users = [row[0] for row in bind.execute(sa.text("SELECT id FROM users"))]
    if not users:
        return

    existing_defaults = {
        row[0]
        for row in bind.execute(sa.text("SELECT user_id FROM notebooks WHERE is_default IS TRUE"))
    }

    now = datetime.now(UTC)
    defaults_by_user: dict[str, str] = {}

    for user_id in users:
        row = bind.execute(
            sa.text(
                "SELECT id FROM notebooks WHERE user_id = :user_id AND is_default IS TRUE LIMIT 1"
            ),
            {"user_id": user_id},
        ).first()
        if row is not None:
            defaults_by_user[user_id] = str(row[0])
            continue
        if user_id in existing_defaults:
            continue
        notebook_id = str(uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO notebooks (id, user_id, title, description, is_default, created_at, updated_at)
                VALUES (:id, :user_id, :title, :description, TRUE, :created_at, :updated_at)
                """
            ),
            {
                "id": notebook_id,
                "user_id": user_id,
                "title": "Default Notebook",
                "description": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        defaults_by_user[user_id] = notebook_id

    if not defaults_by_user:
        return

    # sources.notebook_id
    for user_id, notebook_id in defaults_by_user.items():
        bind.execute(
            sa.text(
                "UPDATE sources SET notebook_id = :nb WHERE user_id = :uid AND notebook_id IS NULL"
            ),
            {"uid": user_id, "nb": notebook_id},
        )

    # chat_sessions.notebook_id
    for user_id, notebook_id in defaults_by_user.items():
        bind.execute(
            sa.text(
                "UPDATE chat_sessions SET notebook_id = :nb WHERE user_id = :uid AND notebook_id IS NULL"
            ),
            {"uid": user_id, "nb": notebook_id},
        )

    # jobs.notebook_id
    for user_id, notebook_id in defaults_by_user.items():
        bind.execute(
            sa.text(
                "UPDATE jobs SET notebook_id = :nb WHERE user_id = :uid AND notebook_id IS NULL"
            ),
            {"uid": user_id, "nb": notebook_id},
        )

    # podcast_jobs.notebook_id
    for user_id, notebook_id in defaults_by_user.items():
        bind.execute(
            sa.text(
                "UPDATE podcast_jobs SET notebook_id = :nb WHERE user_id = :uid AND notebook_id IS NULL"
            ),
            {"uid": user_id, "nb": notebook_id},
        )

    # chunks.notebook_id, prefer source.notebook_id
    bind.execute(
        sa.text(
            """
            UPDATE chunks
            SET notebook_id = sources.notebook_id
            FROM sources
            WHERE chunks.source_id = sources.id
              AND (chunks.notebook_id IS NULL)
              AND (sources.notebook_id IS NOT NULL)
            """
        )
    )

    # chunks fallback by user
    for user_id, notebook_id in defaults_by_user.items():
        bind.execute(
            sa.text(
                "UPDATE chunks SET notebook_id = :nb WHERE user_id = :uid AND notebook_id IS NULL"
            ),
            {"uid": user_id, "nb": notebook_id},
        )
