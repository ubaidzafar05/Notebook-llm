from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import case, select
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
        pinned_sort = case((Notebook.pinned_at.is_(None), 1), else_=0)
        stmt = (
            select(Notebook)
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.is_pinned.desc(), pinned_sort.asc(), Notebook.pinned_at.desc(), Notebook.updated_at.desc())
        )
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

    def update(
        self,
        notebook: Notebook,
        *,
        title: str | None,
        description: str | None,
        is_pinned: bool | None,
    ) -> Notebook:
        changed = False
        if title is not None and title != notebook.title:
            notebook.title = title
            changed = True
        if description is not None and description != notebook.description:
            notebook.description = description
            changed = True
        if is_pinned is not None and is_pinned != notebook.is_pinned:
            notebook.is_pinned = is_pinned
            notebook.pinned_at = datetime.now(UTC) if is_pinned else None
            changed = True
        if changed:
            notebook.updated_at = datetime.now(UTC)
            self.db.add(notebook)
            self.db.commit()
            self.db.refresh(notebook)
        return notebook

    def delete(self, notebook: Notebook) -> None:
        self.db.delete(notebook)
        self.db.commit()
