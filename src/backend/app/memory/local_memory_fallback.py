from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.chat_repo import ChatRepository


class LocalMemoryFallback:
    def __init__(self, db: Session) -> None:
        self.chat_repo = ChatRepository(db)

    def summarize(self, user_id: str, session_id: str) -> str:
        messages = self.chat_repo.list_messages(user_id=user_id, session_id=session_id)
        if not messages:
            return "No conversation history yet."

        last_messages = messages[-6:]
        lines: list[str] = []
        for message in last_messages:
            prefix = "User" if message.role == "user" else "Assistant"
            lines.append(f"{prefix}: {message.content[:220]}")
        return "\n".join(lines)
