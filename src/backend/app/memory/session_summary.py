from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.repositories.chat_repo import ChatRepository
from app.memory.memory_service import MemoryService


class SessionSummaryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.memory = MemoryService(db)

    def maybe_update(self, *, user_id: str, session_id: str) -> str | None:
        session = self.chat_repo.get_session(user_id=user_id, session_id=session_id)
        if session is None:
            return None
        if not self._should_summarize(session_id=session_id, last_updated=session.summary_updated_at):
            return None
        summary, _provider = self.memory.summarize_session(user_id=user_id, session_id=session_id)
        self.chat_repo.update_session_summary(session_id=session_id, summary=summary)
        return summary

    def _should_summarize(self, *, session_id: str, last_updated: datetime | None) -> bool:
        message_count = self.chat_repo.count_messages(session_id=session_id)
        if message_count < 6:
            return False
        if last_updated is None:
            return True
        return datetime.now(UTC) - last_updated > timedelta(minutes=30)
