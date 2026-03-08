from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession


class ChatRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, user_id: str, notebook_id: str, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, notebook_id=notebook_id, title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_sessions(self, user_id: str) -> list[ChatSession]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
        return list(self.db.scalars(stmt).all())

    def list_sessions_for_notebook(self, user_id: str, notebook_id: str) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.notebook_id == notebook_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_session(self, user_id: str, session_id: str) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id, ChatSession.id == session_id)
        return self.db.scalar(stmt)

    def get_session_for_notebook(self, user_id: str, notebook_id: str, session_id: str) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.notebook_id == notebook_id,
            ChatSession.id == session_id,
        )
        return self.db.scalar(stmt)

    def add_message(
        self,
        session: ChatSession,
        role: str,
        content: str,
        citations: list[dict[str, Any]],
        model_info: dict[str, str],
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session.id,
            role=role,
            content=content,
            citations_json=citations,
            model_info_json=model_info,
        )
        session.updated_at = datetime.now(UTC)
        self.db.add(message)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_messages(self, user_id: str, session_id: str) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id, ChatSession.id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_messages_for_notebook(self, user_id: str, notebook_id: str, session_id: str) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.notebook_id == notebook_id,
                ChatSession.id == session_id,
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
