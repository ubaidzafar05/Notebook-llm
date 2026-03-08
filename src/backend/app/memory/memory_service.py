from __future__ import annotations

from sqlalchemy.orm import Session

from app.memory.zep_client import ZepClient


class MemoryService:
    def __init__(self, db: Session) -> None:
        _ = db
        self.zep = ZepClient()

    def store_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        self.zep.upsert_message(user_id=user_id, session_id=session_id, role=role, content=content)

    def summarize_session(self, user_id: str, session_id: str) -> tuple[str, str]:
        return self.zep.summarize_session(user_id=user_id, session_id=session_id), "zep"
