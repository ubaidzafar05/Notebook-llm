from __future__ import annotations

from typing import Any

from sqlalchemy import case, delete, func, literal, or_, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.orm import Session

from app.db.models import Chunk, Source, SourceStatus


class SourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        user_id: str,
        name: str,
        source_type: str,
        path_or_url: str,
        checksum: str,
        metadata_json: dict[str, Any],
        *,
        notebook_id: str | None = None,
    ) -> Source:
        source = Source(
            user_id=user_id,
            notebook_id=notebook_id,
            name=name,
            source_type=source_type,
            path_or_url=path_or_url,
            checksum=checksum,
            metadata_json=metadata_json,
            status=SourceStatus.PENDING.value,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def get_by_id_for_user(self, source_id: str, user_id: str) -> Source | None:
        stmt = select(Source).where(Source.id == source_id, Source.user_id == user_id)
        return self.db.scalar(stmt)

    def get_by_id_for_notebook(self, source_id: str, user_id: str, notebook_id: str) -> Source | None:
        stmt = select(Source).where(
            Source.id == source_id,
            Source.user_id == user_id,
            Source.notebook_id == notebook_id,
        )
        return self.db.scalar(stmt)

    def list_for_user(self, user_id: str) -> list[Source]:
        stmt = select(Source).where(Source.user_id == user_id).order_by(Source.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def list_for_notebook(self, user_id: str, notebook_id: str) -> list[Source]:
        stmt = (
            select(Source)
            .where(Source.user_id == user_id, Source.notebook_id == notebook_id)
            .order_by(Source.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def set_status(
        self,
        source: Source,
        status: SourceStatus,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        source.status = status.value
        if metadata_json is not None:
            source.metadata_json = metadata_json
        self.db.add(source)
        self.db.commit()

    def delete(self, source: Source) -> None:
        self.db.execute(delete(Chunk).where(Chunk.source_id == source.id))
        self.db.delete(source)
        self.db.commit()


class ChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_create(
        self,
        source_id: str,
        user_id: str,
        rows: list[tuple[int, str, int, dict[str, str | int | float | None]]],
        *,
        notebook_id: str | None = None,
    ) -> list[Chunk]:
        created: list[Chunk] = []
        for index, text, token_count, citation in rows:
            chunk = Chunk(
                source_id=source_id,
                user_id=user_id,
                notebook_id=notebook_id,
                chunk_index=index,
                text=text,
                token_count=token_count,
                citation_json=citation,
            )
            self.db.add(chunk)
            created.append(chunk)
        self.db.commit()
        for chunk in created:
            self.db.refresh(chunk)
        return created

    def list_for_source(self, source_id: str, user_id: str) -> list[Chunk]:
        stmt = (
            select(Chunk)
            .where(Chunk.source_id == source_id, Chunk.user_id == user_id)
            .order_by(Chunk.chunk_index.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_source_in_notebook(self, source_id: str, user_id: str, notebook_id: str) -> list[Chunk]:
        stmt = (
            select(Chunk)
            .where(
                Chunk.source_id == source_id,
                Chunk.user_id == user_id,
                Chunk.notebook_id == notebook_id,
            )
            .order_by(Chunk.chunk_index.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_source_paginated(
        self,
        source_id: str,
        user_id: str,
        notebook_id: str | None = None,
        *,
        limit: int,
        offset: int,
    ) -> list[Chunk]:
        stmt = select(Chunk).where(Chunk.source_id == source_id, Chunk.user_id == user_id)
        if notebook_id is not None:
            stmt = stmt.where(Chunk.notebook_id == notebook_id)
        stmt = stmt.order_by(Chunk.chunk_index.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_for_sources(self, source_ids: list[str], user_id: str, notebook_id: str | None = None) -> list[Chunk]:
        if not source_ids:
            return []
        stmt = select(Chunk).where(Chunk.user_id == user_id, Chunk.source_id.in_(source_ids))
        if notebook_id is not None:
            stmt = stmt.where(Chunk.notebook_id == notebook_id)
        return list(self.db.scalars(stmt).all())

    def lexical_candidates(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        limit: int,
    ) -> list[Chunk]:
        trimmed = query.strip()
        if not trimmed:
            return []
        dialect = self.db.bind.dialect.name if self.db.bind is not None else ""
        if dialect == "postgresql":
            return self._postgres_lexical_candidates(
                user_id=user_id,
                notebook_id=notebook_id,
                query=trimmed,
                limit=limit,
            )
        return self._fallback_lexical_candidates(
            user_id=user_id,
            notebook_id=notebook_id,
            query=trimmed,
            limit=limit,
        )

    def _postgres_lexical_candidates(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        limit: int,
    ) -> list[Chunk]:
        # Use PostgreSQL FTS when available for better lexical recall.
        vector = func.to_tsvector("english", Chunk.text)
        ts_query = func.plainto_tsquery("english", query)
        rank = func.ts_rank_cd(vector, ts_query)
        stmt = (
            select(Chunk)
            .where(
                Chunk.user_id == user_id,
                Chunk.notebook_id == notebook_id,
                vector.op("@@")(ts_query),
            )
            .order_by(rank.desc(), Chunk.chunk_index.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def _fallback_lexical_candidates(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        limit: int,
    ) -> list[Chunk]:
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return []
        like_predicates = [func.lower(Chunk.text).like(f"%{term}%") for term in terms]
        score_expr: ColumnElement[int] = literal(0)
        for term in terms:
            score_expr = score_expr + case((func.lower(Chunk.text).like(f"%{term}%"), 1), else_=0)
        stmt = (
            select(Chunk)
            .where(Chunk.user_id == user_id, Chunk.notebook_id == notebook_id, or_(*like_predicates))
            .order_by(score_expr.desc(), Chunk.chunk_index.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
