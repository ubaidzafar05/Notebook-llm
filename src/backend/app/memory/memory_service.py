from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.memory.local_memory_fallback import LocalMemoryFallback
from app.memory.zep_client import ZepClient

logger = logging.getLogger(__name__)


class MemoryService:
    """Unified memory layer that delegates to Zep and falls back to local DB."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.zep = ZepClient()
        self.fallback = LocalMemoryFallback(db)

    def is_remote_enabled(self) -> bool:
        return self.zep.is_enabled()

    def store_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        if not self.zep.is_enabled():
            logger.debug("Zep disabled — message stored locally only")
            return
        try:
            self.zep.upsert_message(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
            )
        except AppError:
            logger.warning(
                "Zep upsert failed for session %s — message persisted in local DB only",
                session_id,
                exc_info=True,
            )

    def summarize_session(self, user_id: str, session_id: str) -> tuple[str, str]:
        if not self.zep.is_enabled():
            return self.fallback.summarize(user_id=user_id, session_id=session_id), "local"
        try:
            summary = self.zep.summarize_session(user_id=user_id, session_id=session_id)
            return summary, "zep"
        except AppError:
            logger.warning(
                "Zep summary failed for session %s — falling back to local",
                session_id,
                exc_info=True,
            )
            return self.fallback.summarize(user_id=user_id, session_id=session_id), "local"

    def get_context_for_generation(self, user_id: str, session_id: str) -> str:
        """Return memory context suitable for injection into the generation prompt."""
        summary, provider = self.summarize_session(user_id=user_id, session_id=session_id)
        if summary and summary != "No summary available" and summary != "No conversation history yet.":
            return f"[Memory context via {provider}]\n{summary}"
        return ""
