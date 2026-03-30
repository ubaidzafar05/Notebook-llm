from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
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

    def list_sessions(self, user_id: str, *, limit: int = 50, offset: int = 0) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def list_sessions_for_notebook(self, user_id: str, notebook_id: str, *, limit: int = 50, offset: int = 0) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.notebook_id == notebook_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
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

    def count_messages(self, session_id: str) -> int:
        stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session_id)
        return int(self.db.scalar(stmt) or 0)

    def update_session_summary(self, session_id: str, summary: str) -> None:
        session = self.db.scalar(select(ChatSession).where(ChatSession.id == session_id))
        if session is None:
            return
        session.summary = summary
        session.summary_updated_at = datetime.now(UTC)
        session.updated_at = datetime.now(UTC)
        self.db.add(session)
        self.db.commit()

    def list_messages(self, user_id: str, session_id: str, *, limit: int = 100, offset: int = 0) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id, ChatSession.id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
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

    def search_messages_for_notebook(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        limit: int,
    ) -> list[ChatMessage]:
        trimmed = query.strip()
        if not trimmed:
            return []
        dialect = self.db.bind.dialect.name if self.db.bind is not None else ""
        if dialect == "postgresql":
            return self._postgres_search(user_id=user_id, notebook_id=notebook_id, query=trimmed, limit=limit)
        return self._fallback_search(user_id=user_id, notebook_id=notebook_id, query=trimmed, limit=limit)

    def _postgres_search(self, *, user_id: str, notebook_id: str, query: str, limit: int) -> list[ChatMessage]:
        ts_query = func.plainto_tsquery("english", query)
        vector = func.to_tsvector("english", ChatMessage.content)
        rank = func.ts_rank_cd(vector, ts_query)
        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.notebook_id == notebook_id,
                vector.op("@@")(ts_query),
            )
            .order_by(rank.desc(), ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def _fallback_search(self, *, user_id: str, notebook_id: str, query: str, limit: int) -> list[ChatMessage]:
        like_expr = f"%{query.lower()}%"
        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.notebook_id == notebook_id,
                func.lower(ChatMessage.content).like(like_expr),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
