from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import create_engine

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[4]


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["database_url_override"] = database_url
    return config


def upgrade_to_head(database_url: str) -> None:
    config = _build_alembic_config(database_url)
    try:
        if _needs_legacy_baseline(database_url):
            # Treat legacy/unversioned DBs as having the initial schema applied,
            # then run repair migrations to bring it to current head.
            command.stamp(config, "20260306_0001")
        command.upgrade(config, "head")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to apply Alembic migrations", extra={"correlation_id": ""})
        raise RuntimeError("Database migration failed. Run 'uv run alembic upgrade head'.") from exc


def _needs_legacy_baseline(database_url: str) -> bool:
    engine = create_engine(database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if not table_names:
        return False
    if "alembic_version" in table_names:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
            return row is None
    legacy_tables = {"users", "sources", "chunks", "chat_sessions", "chat_messages", "jobs", "podcast_jobs"}
    return any(table in table_names for table in legacy_tables)
