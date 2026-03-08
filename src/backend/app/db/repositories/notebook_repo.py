from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notebook


class NotebookRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: str,
        title: str,
        description: str | None = None,
        is_default: bool = False,
    ) -> Notebook:
        notebook = Notebook(
            user_id=user_id,
            title=title,
            description=description,
            is_default=is_default,
        )
        self.db.add(notebook)
        self.db.commit()
        self.db.refresh(notebook)
        return notebook

    def list_for_user(self, user_id: str) -> list[Notebook]:
        stmt = select(Notebook).where(Notebook.user_id == user_id).order_by(Notebook.updated_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_for_user(self, notebook_id: str, user_id: str) -> Notebook | None:
        stmt = select(Notebook).where(Notebook.id == notebook_id, Notebook.user_id == user_id)
        return self.db.scalar(stmt)

    def get_default_for_user(self, user_id: str) -> Notebook | None:
        stmt = select(Notebook).where(Notebook.user_id == user_id, Notebook.is_default.is_(True))
        return self.db.scalar(stmt)

    def ensure_default_for_user(self, user_id: str) -> Notebook:
        existing = self.get_default_for_user(user_id)
        if existing is not None:
            return existing
        return self.create(user_id=user_id, title="Default Notebook", description=None, is_default=True)

    def update(self, notebook: Notebook, *, title: str, description: str | None) -> Notebook:
        notebook.title = title
        notebook.description = description
        notebook.updated_at = datetime.now(UTC)
        self.db.add(notebook)
        self.db.commit()
        self.db.refresh(notebook)
        return notebook

    def delete(self, notebook: Notebook) -> None:
        self.db.delete(notebook)
        self.db.commit()
