from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import NotebookUsage


class NotebookUsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_notebook(self, notebook_id: str) -> NotebookUsage | None:
        stmt = select(NotebookUsage).where(NotebookUsage.notebook_id == notebook_id)
        return self.db.scalar(stmt)

    def get_or_create(self, notebook_id: str) -> NotebookUsage:
        existing = self.get_for_notebook(notebook_id)
        if existing is not None:
            return existing
        usage = NotebookUsage(notebook_id=notebook_id)
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def increment_messages(
        self,
        *,
        notebook_id: str,
        prompt_tokens: int,
        response_tokens: int,
        cost_usd: float,
    ) -> NotebookUsage:
        usage = self.get_or_create(notebook_id)
        usage.total_messages += 1
        usage.total_prompt_tokens_est += prompt_tokens
        usage.total_response_tokens_est += response_tokens
        usage.estimated_cost_usd += cost_usd
        usage.last_activity_at = datetime.now(UTC)
        usage.updated_at = datetime.now(UTC)
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def increment_sources(self, *, notebook_id: str, delta: int = 1) -> NotebookUsage:
        usage = self.get_or_create(notebook_id)
        usage.total_sources += delta
        usage.updated_at = datetime.now(UTC)
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage
