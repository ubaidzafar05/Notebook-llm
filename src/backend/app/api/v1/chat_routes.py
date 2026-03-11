from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from app.api.dependencies import rate_limit_dependency
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.response_envelope import error_response, success_response
from app.core.token_estimate import estimate_tokens
from app.export.chat_exporter import (
    ChatExportService,
    ExportChunkRecord,
    ExportContext,
    ExportSourceRecord,
)
from app.db.repositories.chat_repo import ChatRepository
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.db.repositories.usage_repo import NotebookUsageRepository
from app.db.models import ChatMessage
from app.db.session import get_db
from app.embeddings.embedding_service import EmbeddingService
from app.generation.response_generator import ResponseGenerator
from app.memory.memory_service import MemoryService
from app.memory.session_summary import SessionSummaryService
from app.retrieval.citation_builder import build_citations
from app.retrieval.citation_guard import filter_citations_by_chunk_ids
from app.retrieval.citation_scoring import score_citations
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import rerank
from app.vector_store.collections import VectorRecord
from app.vector_store.milvus_client import VectorStoreClient
from schemas.chat import ChatMessageRequest, CreateSessionRequest

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat/sessions", dependencies=[rate_limit_dependency(times=5, seconds=60)])
def create_session(
    payload: CreateSessionRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    notebook_id = _resolved_notebook_id(db, user.id, None)
    session = ChatRepository(db).create_session(user_id=user.id, notebook_id=notebook_id, title=payload.title)
    data = {
        "id": session.id,
        "notebook_id": session.notebook_id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }
    return success_response(data=data, request_id=request_id, status_code=201)


@router.get("/chat/sessions")
def list_sessions(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    sessions = ChatRepository(db).list_sessions(user_id=user.id)
    data = [
        {
            "id": session.id,
            "notebook_id": session.notebook_id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "summary": session.summary,
            "summary_updated_at": session.summary_updated_at.isoformat() if session.summary_updated_at else None,
        }
        for session in sessions
    ]
    return success_response(data=data, request_id=request_id)


@router.post("/chat/sessions/{session_id}/messages", dependencies=[rate_limit_dependency(times=10, seconds=60)])
def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    request_id = getattr(request.state, "request_id", "")
    chat_repo = ChatRepository(db)
    session = chat_repo.get_session(user_id=user.id, session_id=session_id)
    if session is None:
        return error_response(code="NOT_FOUND", message="Session not found", request_id=request_id, status_code=404)

    chat_repo.add_message(session=session, role="user", content=payload.message, citations=[], model_info={})

    vector_store = _vector_store_from_request(request)
    notebook_id = session.notebook_id or _resolved_notebook_id(db, user.id, None)
    chunk_repo = ChunkRepository(db)
    retriever = HybridRetriever(
        embedding_service=EmbeddingService(),
        vector_store=vector_store,
        chunk_repo=chunk_repo,
    )
    try:
        hybrid = retriever.retrieve(user_id=user.id, notebook_id=notebook_id, query=payload.message)
        candidates = hybrid.records
    except Exception:  # noqa: BLE001
        return error_response(code="RETRIEVAL_FAILED", message="Retrieval failed", request_id=request_id, status_code=500)

    filtered_candidates = _filter_candidates(candidates=candidates, source_ids=payload.source_ids)
    if not filtered_candidates:
        filtered_candidates = _fallback_candidates_from_chunks(
            db=db,
            chunk_repo=chunk_repo,
            user_id=user.id,
            notebook_id=notebook_id,
            requested_source_ids=payload.source_ids,
        )
    reranked = rerank(query=payload.message, candidates=filtered_candidates)

    source_ids = payload.source_ids if payload.source_ids else [record.source_id for record in reranked]
    chunk_lookup = {
        chunk.id: chunk
        for chunk in chunk_repo.list_for_sources(source_ids=source_ids, user_id=user.id, notebook_id=notebook_id)
    }
    citations = build_citations(records=reranked, chunk_lookup=chunk_lookup)
    citations = filter_citations_by_chunk_ids(
        citations=citations,
        valid_chunk_ids={item.chunk_id for item in reranked},
    )
    citations = score_citations(question=payload.message, records=reranked, citations=citations)

    memory_service = MemoryService(db)
    try:
        memory_summary, _ = memory_service.summarize_session(user_id=user.id, session_id=session.id)
    except Exception:  # noqa: BLE001
        memory_summary = ""
    try:
        answer_text, model_info, confidence = ResponseGenerator().generate_answer(
            question=payload.message,
            contexts=reranked,
            citations=citations,
            memory_context=memory_summary,
        )
    except Exception:  # noqa: BLE001
        return error_response(code="GENERATION_FAILED", message="Answer generation failed", request_id=request_id, status_code=500)
    model_info["confidence"] = confidence
    chat_repo.add_message(
        session=session,
        role="assistant",
        content=answer_text,
        citations=[citation.model_dump() for citation in citations],
        model_info=model_info,
    )

    try:
        memory_service.store_message(user_id=user.id, session_id=session.id, role="user", content=payload.message)
        memory_service.store_message(user_id=user.id, session_id=session.id, role="assistant", content=answer_text)
    except Exception:  # noqa: BLE001
        logger.exception("Memory store failed session_id=%s", session.id)
    try:
        SessionSummaryService(db).maybe_update(user_id=user.id, session_id=session.id)
    except Exception:  # noqa: BLE001
        logger.exception("Session summary update failed session_id=%s", session.id)
    _update_usage_stats(
        db=db,
        notebook_id=notebook_id,
        prompt_text=payload.message,
        response_text=answer_text,
    )

    stream = _stream_answer(
        answer_text=answer_text,
        citations=[citation.model_dump() for citation in citations],
        model_info=model_info,
        confidence=confidence,
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get("/chat/sessions/{session_id}/messages")
def list_messages(
    session_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    messages = ChatRepository(db).list_messages(user_id=user.id, session_id=session_id)
    data = [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "citations": message.citations_json,
            "model_info": message.model_info_json,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
    return success_response(data=data, request_id=request_id)


@router.post("/notebooks/{notebook_id}/chat/sessions", dependencies=[rate_limit_dependency(times=5, seconds=60)])
def create_notebook_session(
    notebook_id: str,
    payload: CreateSessionRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    session = ChatRepository(db).create_session(user_id=user.id, notebook_id=resolved_notebook_id, title=payload.title)
    data = {
        "id": session.id,
        "notebook_id": session.notebook_id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }
    return success_response(data=data, request_id=request_id, status_code=201)


@router.get("/notebooks/{notebook_id}/chat/sessions")
def list_notebook_sessions(
    notebook_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    sessions = ChatRepository(db).list_sessions_for_notebook(user_id=user.id, notebook_id=resolved_notebook_id)
    data = [
        {
            "id": session.id,
            "notebook_id": session.notebook_id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "summary": session.summary,
            "summary_updated_at": session.summary_updated_at.isoformat() if session.summary_updated_at else None,
        }
        for session in sessions
    ]
    return success_response(data=data, request_id=request_id)


@router.post("/notebooks/{notebook_id}/chat/sessions/{session_id}/messages", dependencies=[rate_limit_dependency(times=10, seconds=60)])
def send_notebook_message(
    notebook_id: str,
    session_id: str,
    payload: ChatMessageRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    session = ChatRepository(db).get_session_for_notebook(user_id=user.id, notebook_id=resolved_notebook_id, session_id=session_id)
    if session is None:
        request_id = getattr(request.state, "request_id", "")
        return error_response(code="NOT_FOUND", message="Session not found", request_id=request_id, status_code=404)
    request.state.notebook_id = resolved_notebook_id
    return send_message(session_id=session_id, payload=payload, request=request, user=user, db=db)


@router.get("/notebooks/{notebook_id}/chat/sessions/{session_id}/messages")
def list_notebook_messages(
    notebook_id: str,
    session_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    messages = ChatRepository(db).list_messages_for_notebook(
        user_id=user.id,
        notebook_id=resolved_notebook_id,
        session_id=session_id,
    )
    data = [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "citations": message.citations_json,
            "model_info": message.model_info_json,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
    return success_response(data=data, request_id=request_id)


@router.get("/notebooks/{notebook_id}/chat/search")
def search_notebook_messages(
    notebook_id: str,
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    messages = ChatRepository(db).search_messages_for_notebook(
        user_id=user.id,
        notebook_id=resolved_notebook_id,
        query=q,
        limit=limit,
    )
    data = [
        {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
    return success_response(data=data, request_id=request_id)


@router.get("/notebooks/{notebook_id}/chat/sessions/{session_id}/export")
def export_session(
    notebook_id: str,
    session_id: str,
    request: Request,
    format: str = Query(default="md"),
    top_k: int | None = Query(default=None, ge=1, le=50),
    similarity_threshold: float | None = Query(default=None, ge=0.0, le=1.0),
    model: str | None = Query(default=None, max_length=64),
    memory_enabled: bool | None = Query(default=None),
    attached_sources: str | None = Query(default=None, max_length=2000),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    session = ChatRepository(db).get_session_for_notebook(
        user_id=user.id,
        notebook_id=resolved_notebook_id,
        session_id=session_id,
    )
    if session is None:
        return error_response(code="NOT_FOUND", message="Session not found", request_id=request_id, status_code=404)
    notebook = NotebookRepository(db).get_for_user(resolved_notebook_id, user.id)
    if notebook is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    messages = ChatRepository(db).list_messages_for_notebook(
        user_id=user.id,
        notebook_id=resolved_notebook_id,
        session_id=session_id,
    )
    exporter = ChatExportService()
    context = _build_export_context(
        attached_sources=attached_sources,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        model=model,
        memory_enabled=memory_enabled,
    )
    sources, chunks = _load_export_sources_and_chunks(
        db=db,
        user_id=user.id,
        notebook_id=resolved_notebook_id,
        messages=messages,
        context=context,
    )
    markdown_text = exporter.render_markdown(
        session=session,
        notebook=notebook,
        messages=messages,
        sources=sources,
        chunks=chunks,
        context=context,
    )
    if format == "md":
        headers = {"Content-Disposition": f"attachment; filename={session.title or 'session'}.md"}
        return Response(content=markdown_text, media_type="text/markdown", headers=headers)
    if format == "pdf":
        try:
            pdf_bytes = exporter.render_pdf(markdown_text)
            headers = {"Content-Disposition": f"attachment; filename={session.title or 'session'}.pdf"}
            return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
        except Exception as exc:  # noqa: BLE001
            logger.exception("PDF export failed", extra={"session_id": session_id, "notebook_id": resolved_notebook_id})
            return error_response(code="PDF_EXPORT_FAILED", message=str(exc), request_id=request_id, status_code=500)
    return error_response(code="INVALID_FORMAT", message="Unsupported export format", request_id=request_id, status_code=400)



def _filter_candidates(candidates: list[VectorRecord], source_ids: list[str]) -> list[VectorRecord]:
    if not source_ids:
        return candidates
    source_set = set(source_ids)
    return [candidate for candidate in candidates if candidate.source_id in source_set]


def _build_export_context(
    *,
    attached_sources: str | None,
    top_k: int | None,
    similarity_threshold: float | None,
    model: str | None,
    memory_enabled: bool | None,
) -> ExportContext:
    attached_ids = _parse_attached_sources(attached_sources)
    return ExportContext(
        attached_source_ids=attached_ids,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        model=model,
        memory_enabled=memory_enabled,
    )


def _parse_attached_sources(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_export_sources_and_chunks(
    *,
    db: Session,
    user_id: str,
    notebook_id: str,
    messages: list[ChatMessage],
    context: ExportContext,
) -> tuple[dict[str, ExportSourceRecord], dict[str, ExportChunkRecord]]:
    citation_source_ids, citation_chunk_ids = _collect_citation_ids(messages)
    source_ids = sorted(set(citation_source_ids).union(context.attached_source_ids))
    sources = SourceRepository(db).list_by_ids_for_notebook(
        user_id=user_id,
        notebook_id=notebook_id,
        source_ids=source_ids,
    )
    source_map = {
        source.id: ExportSourceRecord(
            id=source.id,
            title=source.name,
            source_type=source.source_type,
            status=source.status,
            path_or_url=source.path_or_url,
            metadata=source.metadata_json or {},
        )
        for source in sources
    }
    chunks = ChunkRepository(db).list_by_ids(
        user_id=user_id,
        notebook_id=notebook_id,
        chunk_ids=sorted(citation_chunk_ids),
    )
    chunk_map = {
        chunk.id: ExportChunkRecord(
            id=chunk.id,
            source_id=chunk.source_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            citation=chunk.citation_json or {},
        )
        for chunk in chunks
    }
    return source_map, chunk_map


def _collect_citation_ids(messages: list[ChatMessage]) -> tuple[set[str], set[str]]:
    source_ids: set[str] = set()
    chunk_ids: set[str] = set()
    for message in messages:
        for citation in message.citations_json:
            source_id = citation.get("source_id")
            chunk_id = citation.get("chunk_id")
            if isinstance(source_id, str) and source_id:
                source_ids.add(source_id)
            if isinstance(chunk_id, str) and chunk_id:
                chunk_ids.add(chunk_id)
    return source_ids, chunk_ids


def _fallback_candidates_from_chunks(
    *,
    db: Session,
    chunk_repo: ChunkRepository,
    user_id: str,
    notebook_id: str,
    requested_source_ids: list[str],
    max_candidates: int = 200,
) -> list[VectorRecord]:
    source_ids = requested_source_ids
    if not source_ids:
        source_ids = [source.id for source in SourceRepository(db).list_for_notebook(user_id=user_id, notebook_id=notebook_id)]
    chunk_rows = chunk_repo.list_for_sources(source_ids=source_ids, user_id=user_id, notebook_id=notebook_id)[:max_candidates]
    candidates: list[VectorRecord] = []
    for chunk in chunk_rows:
        candidates.append(
            VectorRecord(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                user_id=chunk.user_id,
                notebook_id=chunk.notebook_id or notebook_id,
                text=chunk.text,
                vector=[],
                metadata=chunk.citation_json,
            )
        )
    return candidates


def _stream_answer(
    answer_text: str,
    citations: list[dict[str, str | int | float | None]],
    model_info: dict[str, str],
    confidence: Literal["low", "medium", "high"],
) -> Iterator[str]:
    for token in answer_text.split(" "):
        data = {"type": "token", "value": token + " "}
        yield f"data: {json.dumps(data)}\n\n"
    final_data = {
        "type": "final",
        "content": answer_text,
        "citations": citations,
        "model_info": model_info,
        "confidence": confidence,
    }
    yield f"data: {json.dumps(final_data)}\n\n"



def _vector_store_from_request(request: Request) -> VectorStoreClient:
    vector_store = getattr(request.app.state, "vector_store", None)
    if isinstance(vector_store, VectorStoreClient):
        return vector_store
    raise RuntimeError("Vector store not initialized")

def _resolved_notebook_id(db: Session, user_id: str, notebook_id: str | None) -> str:
    repo = NotebookRepository(db)
    if notebook_id is None:
        return repo.ensure_default_for_user(user_id).id
    notebook = repo.get_for_user(notebook_id, user_id)
    if notebook is None:
        return repo.ensure_default_for_user(user_id).id
    return notebook.id


def _update_usage_stats(*, db: Session, notebook_id: str, prompt_text: str, response_text: str) -> None:
    from app.core.config import get_settings

    prompt_tokens = estimate_tokens(prompt_text)
    response_tokens = estimate_tokens(response_text)
    settings = get_settings()
    cost = (prompt_tokens / 1000 * settings.usage_cost_per_1k_prompt) + (
        response_tokens / 1000 * settings.usage_cost_per_1k_response
    )
    try:
        NotebookUsageRepository(db).increment_messages(
            notebook_id=notebook_id,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            cost_usd=cost,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Usage update failed notebook_id=%s", notebook_id)
