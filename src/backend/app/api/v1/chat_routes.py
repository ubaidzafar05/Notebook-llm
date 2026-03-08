from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.response_envelope import error_response, success_response
from app.db.repositories.chat_repo import ChatRepository
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.db.session import get_db
from app.embeddings.embedding_service import EmbeddingService
from app.generation.response_generator import ResponseGenerator
from app.memory.memory_service import MemoryService
from app.retrieval.citation_builder import build_citations
from app.retrieval.citation_guard import filter_citations_by_chunk_ids
from app.retrieval.reranker import rerank
from app.retrieval.retriever import Retriever
from app.vector_store.collections import VectorRecord
from app.vector_store.milvus_client import VectorStoreClient
from schemas.chat import ChatMessageRequest, CreateSessionRequest

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat/sessions")
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
        }
        for session in sessions
    ]
    return success_response(data=data, request_id=request_id)


@router.post("/chat/sessions/{session_id}/messages")
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
    retriever = Retriever(embedding_service=EmbeddingService(), vector_store=vector_store)
    notebook_id = session.notebook_id or _resolved_notebook_id(db, user.id, None)
    candidates = retriever.retrieve(user_id=user.id, notebook_id=notebook_id, query=payload.message)
    chunk_repo = ChunkRepository(db)
    candidates = _merge_candidates(
        candidates,
        _lexical_candidates_from_chunks(
            chunk_repo=chunk_repo,
            user_id=user.id,
            notebook_id=notebook_id,
            query=payload.message,
            limit=6,
        ),
    )
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

    memory_service = MemoryService(db)
    memory_summary, _ = memory_service.summarize_session(user_id=user.id, session_id=session.id)
    answer_text, model_info, confidence = ResponseGenerator().generate_answer(
        question=payload.message,
        contexts=reranked,
        citations=citations,
        memory_context=memory_summary,
    )
    model_info["confidence"] = confidence
    chat_repo.add_message(
        session=session,
        role="assistant",
        content=answer_text,
        citations=[citation.model_dump() for citation in citations],
        model_info=model_info,
    )

    memory_service.store_message(user_id=user.id, session_id=session.id, role="user", content=payload.message)
    memory_service.store_message(user_id=user.id, session_id=session.id, role="assistant", content=answer_text)

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


@router.post("/notebooks/{notebook_id}/chat/sessions")
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
        }
        for session in sessions
    ]
    return success_response(data=data, request_id=request_id)


@router.post("/notebooks/{notebook_id}/chat/sessions/{session_id}/messages")
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



def _filter_candidates(candidates: list[VectorRecord], source_ids: list[str]) -> list[VectorRecord]:
    if not source_ids:
        return candidates
    source_set = set(source_ids)
    return [candidate for candidate in candidates if candidate.source_id in source_set]


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


def _lexical_candidates_from_chunks(
    *,
    chunk_repo: ChunkRepository,
    user_id: str,
    notebook_id: str,
    query: str,
    limit: int,
) -> list[VectorRecord]:
    rows = chunk_repo.lexical_candidates(user_id=user_id, notebook_id=notebook_id, query=query, limit=limit)
    return [
        VectorRecord(
            chunk_id=chunk.id,
            source_id=chunk.source_id,
            user_id=chunk.user_id,
            notebook_id=chunk.notebook_id or notebook_id,
            text=chunk.text,
            vector=[],
            metadata=chunk.citation_json,
        )
        for chunk in rows
    ]


def _merge_candidates(primary: list[VectorRecord], secondary: list[VectorRecord]) -> list[VectorRecord]:
    merged: dict[str, VectorRecord] = {record.chunk_id: record for record in primary}
    for record in secondary:
        merged.setdefault(record.chunk_id, record)
    return list(merged.values())



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
