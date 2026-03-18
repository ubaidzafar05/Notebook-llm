from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.db.repositories.chat_repo import ChatRepository
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.db.session import get_db
from app.export.chat_exporter import ChatExportService, ExportChunkRecord, ExportContext, ExportSourceRecord

router = APIRouter(prefix="/api/v1/notebooks", tags=["export"])


@router.get("/{notebook_id}/export")
def export_notebook_session(
    notebook_id: str,
    format: str = Query(default="md", pattern="^(md|pdf)$"),
    session_id: str | None = Query(default=None),
    top_k: int | None = Query(default=None),
    similarity_threshold: float | None = Query(default=None),
    model: str | None = Query(default=None),
    memory_enabled: bool | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    notebook_repo = NotebookRepository(db)
    notebook = notebook_repo.get_for_user(notebook_id, user.id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")

    chat_repo = ChatRepository(db)
    sessions = chat_repo.list_sessions_for_notebook(user.id, notebook_id)
    if not sessions:
        raise HTTPException(status_code=404, detail="No chat sessions found")

    session = sessions[0]
    if session_id:
        session_match = chat_repo.get_session_for_notebook(user.id, notebook_id, session_id)
        if session_match is None:
            raise HTTPException(status_code=404, detail="Session not found")
        session = session_match

    messages = chat_repo.list_messages_for_notebook(user.id, notebook_id, session.id)

    source_repo = SourceRepository(db)
    chunk_repo = ChunkRepository(db)
    raw_sources = source_repo.list_for_notebook(user.id, notebook_id)
    sources: dict[str, ExportSourceRecord] = {}
    for s in raw_sources:
        sources[s.id] = ExportSourceRecord(
            id=s.id,
            title=s.title,
            source_type=s.source_type,
            status=s.status,
            path_or_url=s.path_or_url or "",
            metadata=s.metadata_json or {},
        )

    raw_chunks = chunk_repo.list_for_sources([s.id for s in raw_sources], user.id, notebook_id)
    chunks: dict[str, ExportChunkRecord] = {}
    for c in raw_chunks:
        chunks[c.id] = ExportChunkRecord(
            id=c.id,
            source_id=c.source_id,
            chunk_index=c.chunk_index,
            text=c.text,
            citation=c.citation_json or {},
        )

    context = ExportContext(
        attached_source_ids=[s.id for s in raw_sources],
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        model=model,
        memory_enabled=memory_enabled,
    )

    exporter = ChatExportService()
    md_text = exporter.render_markdown(
        session=session,
        notebook=notebook,
        messages=messages,
        sources=sources,
        chunks=chunks,
        context=context,
    )

    if format == "pdf":
        pdf_bytes = exporter.render_pdf(md_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{notebook.title}-export.pdf"'},
        )

    return Response(
        content=md_text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{notebook.title}-export.md"'},
    )
