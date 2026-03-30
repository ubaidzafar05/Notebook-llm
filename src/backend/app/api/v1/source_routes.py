from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from app.api.dependencies import rate_limit_dependency
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.config import ROOT_DIR, get_settings
from app.core.exceptions import AppError
from app.core.response_envelope import error_response, success_response
from app.db.models import JobRecord, Source, SourceType
from app.db.repositories.job_repo import JobRepository
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.db.session import get_db
from app.embeddings.embedding_service import EmbeddingService
from app.ingestion.idempotency_store import IdempotencyStore
from app.ingestion.ingestion_service import IngestionService
from app.jobs.job_service import JobService
from app.jobs.queue import JobQueue, TaskQueue
from app.jobs.queue_state_store import QueueStateStore
from app.jobs.workers import process_ingestion_job
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.semantic_cache import SemanticCacheService
from app.vector_store.milvus_client import VectorStoreClient
from schemas.source import SourceCreateUrlRequest

router = APIRouter(prefix="/api/v1", tags=["sources"])


@router.post("/sources/upload", dependencies=[rate_limit_dependency(times=5, seconds=60)])
def upload_source(
    request: Request,
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    settings = get_settings()
    source_repo = SourceRepository(db)
    quota_error = _enforce_source_quota(
        source_repo=source_repo,
        user_id=user.id,
        max_sources=settings.max_sources_per_user,
    )
    if quota_error is not None:
        return error_response(
            code="SOURCE_QUOTA_EXCEEDED",
            message=quota_error,
            request_id=request_id,
            status_code=429,
        )

    key = _normalized_idempotency_key(idempotency_key)
    cached = _load_cached_payload(user_id=user.id, operation="upload", key=key)
    if cached is not None:
        cached["deduped"] = True
        return success_response(data=cached, request_id=request_id, status_code=202)

    content = file.file.read()
    if not content:
        return error_response(
            code="EMPTY_FILE",
            message="Uploaded file is empty",
            request_id=request_id,
            status_code=400,
        )
    if len(content) > settings.max_upload_bytes:
        return error_response(
            code="FILE_TOO_LARGE",
            message="Uploaded file exceeds limit",
            request_id=request_id,
            status_code=413,
        )

    uploads_dir = (ROOT_DIR / "data" / "uploads" / user.id).resolve()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    vector_store = _vector_store_from_request(request)
    ingestion = IngestionService(db=db, vector_store=vector_store)
    notebook_id = _resolved_notebook_id(request, db, user.id)
    checksum = ingestion.checksum_bytes(content)
    filename = file.filename or "upload.bin"
    target_path = uploads_dir / f"{checksum}_{filename}"
    target_path.write_bytes(content)

    source = ingestion.create_source_from_file(
        user_id=user.id,
        notebook_id=notebook_id,
        filename=filename,
        path=target_path,
        checksum=checksum,
    )
    jobs = JobService(db)
    job_id = jobs.create(
        user_id=user.id,
        notebook_id=notebook_id,
        job_type="ingestion",
        payload={"source_id": source.id, "checksum": checksum},
        max_retries=settings.job_max_retries_ingestion,
    )
    dispatch = _enqueue_ingestion_job(
        user_id=user.id,
        job_id=job_id,
        source_id=source.id,
        request_id=request_id,
        jobs=jobs,
        retry_max=settings.job_max_retries_ingestion,
    )
    if isinstance(dispatch, JSONResponse):
        return dispatch

    data = {
        "source_id": source.id,
        "job_id": job_id,
        "deduped": False,
        "dispatch_mode": dispatch["mode"],
        "queue_job_id": dispatch["queue_job_id"],
        "queue_name": dispatch["queue_name"],
    }
    _store_cached_payload(user_id=user.id, operation="upload", key=key, payload=data)
    return success_response(data=data, request_id=request_id, status_code=202)


@router.post("/sources/url", dependencies=[rate_limit_dependency(times=5, seconds=60)])
def ingest_url_source(
    payload: SourceCreateUrlRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    settings = get_settings()
    source_repo = SourceRepository(db)
    quota_error = _enforce_source_quota(
        source_repo=source_repo,
        user_id=user.id,
        max_sources=settings.max_sources_per_user,
    )
    if quota_error is not None:
        return error_response(
            code="SOURCE_QUOTA_EXCEEDED",
            message=quota_error,
            request_id=request_id,
            status_code=429,
        )

    source_type = SourceType.WEB if payload.source_type == "web" else SourceType.YOUTUBE
    key = _normalized_idempotency_key(idempotency_key)
    cached = _load_cached_payload(user_id=user.id, operation="url", key=key)
    if cached is not None:
        cached["deduped"] = True
        return success_response(data=cached, request_id=request_id, status_code=202)

    vector_store = _vector_store_from_request(request)
    ingestion = IngestionService(db=db, vector_store=vector_store)
    notebook_id = _resolved_notebook_id(request, db, user.id)
    source = ingestion.create_source_from_url(
        user_id=user.id,
        notebook_id=notebook_id,
        url=str(payload.url),
        source_type=source_type,
    )
    jobs = JobService(db)
    job_id = jobs.create(
        user_id=user.id,
        notebook_id=notebook_id,
        job_type="ingestion",
        payload={"source_id": source.id, "url": str(payload.url)},
        max_retries=settings.job_max_retries_ingestion,
    )
    dispatch = _enqueue_ingestion_job(
        user_id=user.id,
        job_id=job_id,
        source_id=source.id,
        request_id=request_id,
        jobs=jobs,
        retry_max=settings.job_max_retries_ingestion,
    )
    if isinstance(dispatch, JSONResponse):
        return dispatch

    data = {
        "source_id": source.id,
        "job_id": job_id,
        "deduped": False,
        "dispatch_mode": dispatch["mode"],
        "queue_job_id": dispatch["queue_job_id"],
        "queue_name": dispatch["queue_name"],
    }
    _store_cached_payload(user_id=user.id, operation="url", key=key, payload=data)
    return success_response(data=data, request_id=request_id, status_code=202)


@router.get("/sources")
def list_sources(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    sources = SourceRepository(db).list_for_user(user_id=user.id)
    jobs_by_source = _latest_ingestion_jobs_by_source(JobRepository(db).list_for_user(user_id=user.id, job_type="ingestion", limit=500))
    data = [_serialize_source(source=src, ingestion_job=jobs_by_source.get(src.id)) for src in sources]
    return success_response(data=data, request_id=request_id)


@router.post("/notebooks/{notebook_id}/sources/upload", dependencies=[rate_limit_dependency(times=5, seconds=60)])
def upload_source_for_notebook(
    notebook_id: str,
    request: Request,
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return _upload_source_for_notebook(
        notebook_id=notebook_id,
        request=request,
        file=file,
        idempotency_key=idempotency_key,
        user=user,
        db=db,
    )


@router.post("/notebooks/{notebook_id}/sources/url", dependencies=[rate_limit_dependency(times=5, seconds=60)])
def ingest_url_for_notebook(
    notebook_id: str,
    payload: SourceCreateUrlRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return _ingest_url_for_notebook(
        notebook_id=notebook_id,
        payload=payload,
        request=request,
        idempotency_key=idempotency_key,
        user=user,
        db=db,
    )


@router.get("/notebooks/{notebook_id}/sources")
def list_notebook_sources(
    notebook_id: str,
    request: Request,
    source_type: list[str] | None = Query(default=None),
    status: list[str] | None = Query(default=None),
    q: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    if _notebook_for_user(db, notebook_id, user.id) is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    sources = SourceRepository(db).list_for_notebook_filtered(
        user_id=user.id,
        notebook_id=notebook_id,
        source_types=source_type,
        statuses=status,
        created_from=from_date,
        created_to=to_date,
        query=q,
    )
    jobs_by_source = _latest_ingestion_jobs_by_source(
        JobRepository(db).list_for_notebook(
            user_id=user.id,
            notebook_id=notebook_id,
            job_type="ingestion",
            limit=500,
        )
    )
    data = [_serialize_source(source=src, ingestion_job=jobs_by_source.get(src.id)) for src in sources]
    return success_response(data=data, request_id=request_id)


@router.get("/notebooks/{notebook_id}/sources/search")
def search_notebook_sources(
    notebook_id: str,
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=30, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    if _notebook_for_user(db, notebook_id, user.id) is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    vector_store = _vector_store_from_request(request)
    chunk_repo = ChunkRepository(db)
    retriever = HybridRetriever(
        embedding_service=EmbeddingService(),
        vector_store=vector_store,
        chunk_repo=chunk_repo,
    )
    try:
        records = retriever.retrieve(user_id=user.id, notebook_id=notebook_id, query=q, top_k=limit).records
    except Exception:  # noqa: BLE001
        return error_response(code="SEARCH_FAILED", message="Search failed", request_id=request_id, status_code=500)
    source_ids = [record.source_id for record in records]
    sources = SourceRepository(db).list_for_notebook(user_id=user.id, notebook_id=notebook_id)
    source_map = {source.id: source for source in sources}
    ordered: list[Source] = []
    for source_id in source_ids:
        source = source_map.get(source_id)
        if source and source not in ordered:
            ordered.append(source)
    jobs_by_source = _latest_ingestion_jobs_by_source(
        JobRepository(db).list_for_notebook(user_id=user.id, notebook_id=notebook_id, job_type="ingestion", limit=500)
    )
    data = [_serialize_source(source=src, ingestion_job=jobs_by_source.get(src.id)) for src in ordered]
    return success_response(data=data, request_id=request_id)


@router.get("/sources/{source_id}")
def get_source(
    source_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    source = SourceRepository(db).get_by_id_for_user(source_id=source_id, user_id=user.id)
    if source is None:
        return error_response(code="NOT_FOUND", message="Source not found", request_id=request_id, status_code=404)
    jobs = JobRepository(db).list_for_user(user_id=user.id, job_type="ingestion", limit=500)
    data = _serialize_source(source=source, ingestion_job=_latest_ingestion_jobs_by_source(jobs).get(source.id))
    return success_response(data=data, request_id=request_id)


@router.get("/notebooks/{notebook_id}/sources/{source_id}")
def get_notebook_source(
    notebook_id: str,
    source_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    source = SourceRepository(db).get_by_id_for_notebook(source_id=source_id, user_id=user.id, notebook_id=notebook_id)
    if source is None:
        return error_response(code="NOT_FOUND", message="Source not found", request_id=request_id, status_code=404)
    jobs = JobRepository(db).list_for_notebook(
        user_id=user.id,
        notebook_id=notebook_id,
        job_type="ingestion",
        limit=200,
    )
    data = _serialize_source(source=source, ingestion_job=_latest_ingestion_jobs_by_source(jobs).get(source.id))
    return success_response(data=data, request_id=request_id)


@router.get("/sources/{source_id}/chunks")
def list_source_chunks(
    source_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    source = SourceRepository(db).get_by_id_for_user(source_id=source_id, user_id=user.id)
    if source is None:
        return error_response(code="NOT_FOUND", message="Source not found", request_id=request_id, status_code=404)

    rows = ChunkRepository(db).list_for_source_paginated(
        source_id=source_id,
        user_id=user.id,
        limit=limit,
        offset=offset,
    )
    data = {
        "source_id": source_id,
        "limit": limit,
        "offset": offset,
        "chunks": [
            {
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "excerpt": chunk.text[:320],
                "citation": chunk.citation_json,
            }
            for chunk in rows
        ],
    }
    return success_response(data=data, request_id=request_id)


@router.get("/notebooks/{notebook_id}/sources/{source_id}/chunks")
def list_notebook_source_chunks(
    notebook_id: str,
    source_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    source = SourceRepository(db).get_by_id_for_notebook(source_id=source_id, user_id=user.id, notebook_id=notebook_id)
    if source is None:
        return error_response(code="NOT_FOUND", message="Source not found", request_id=request_id, status_code=404)
    rows = ChunkRepository(db).list_for_source_paginated(
        source_id=source_id,
        user_id=user.id,
        notebook_id=notebook_id,
        limit=limit,
        offset=offset,
    )
    data = {
        "source_id": source_id,
        "notebook_id": notebook_id,
        "limit": limit,
        "offset": offset,
        "chunks": [
            {
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "excerpt": chunk.text[:320],
                "citation": chunk.citation_json,
            }
            for chunk in rows
        ],
    }
    return success_response(data=data, request_id=request_id)


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    repo = SourceRepository(db)
    source = repo.get_by_id_for_user(source_id=source_id, user_id=user.id)
    if source is None:
        return error_response(code="NOT_FOUND", message="Source not found", request_id=request_id, status_code=404)

    vector_store = _vector_store_from_request(request)
    vector_store.delete_source(user_id=user.id, source_id=source.id)
    SemanticCacheService().invalidate_for_source(source.id)
    repo.delete(source)
    return success_response(data={"deleted": True, "source_id": source_id}, request_id=request_id)


@router.delete("/notebooks/{notebook_id}/sources/{source_id}")
def delete_notebook_source(
    notebook_id: str,
    source_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    repo = SourceRepository(db)
    source = repo.get_by_id_for_notebook(source_id=source_id, user_id=user.id, notebook_id=notebook_id)
    if source is None:
        return error_response(code="NOT_FOUND", message="Source not found", request_id=request_id, status_code=404)
    vector_store = _vector_store_from_request(request)
    vector_store.delete_source(user_id=user.id, source_id=source.id)
    SemanticCacheService().invalidate_for_source(source.id)
    repo.delete(source)
    return success_response(data={"deleted": True, "source_id": source_id}, request_id=request_id)


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    service = JobService(db)
    job = service.get(user_id=user.id, job_id=job_id)
    if job is None:
        return error_response(code="NOT_FOUND", message="Job not found", request_id=request_id, status_code=404)

    if job.status == "failed" and not job.dead_lettered and job.queue_job_id:
        try:
            if job.queue_name and QueueStateStore(job.queue_name).is_dead_lettered(job.queue_job_id):
                service.mark_dead_lettered(user_id=user.id, job_id=job_id)
                job = service.get(user_id=user.id, job_id=job_id) or job
        except AppError:
            pass

    data = {
        "id": job.id,
        "status": job.status,
        "job_type": job.job_type,
        "progress": job.progress,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "queue_job_id": job.queue_job_id,
        "queue_name": job.queue_name,
        "dead_lettered": job.dead_lettered,
        "failure_code": job.failure_code,
        "failure_detail": job.error_message,
        "cancel_requested": job.cancel_requested,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "result": job.result_json,
        "error_message": job.error_message,
    }
    return success_response(data=data, request_id=request_id)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    service = JobService(db)
    job = service.get(user_id=user.id, job_id=job_id)
    if job is None:
        return error_response(code="NOT_FOUND", message="Job not found", request_id=request_id, status_code=404)

    if job.status == "queued":
        cancelled_in_queue = False
        if job.queue_job_id and job.queue_name:
            cancelled_in_queue = QueueStateStore(job.queue_name).cancel(job.queue_job_id)
        if cancelled_in_queue:
            service.cancel(user_id=user.id, job_id=job_id)
            return success_response(
                data={"cancelled": True, "cancel_requested": False, "job_id": job_id},
                request_id=request_id,
            )
        service.request_cancel(user_id=user.id, job_id=job_id)
        return success_response(
            data={"cancelled": False, "cancel_requested": True, "job_id": job_id},
            request_id=request_id,
            status_code=202,
        )

    if job.status == "running":
        service.request_cancel(user_id=user.id, job_id=job_id)
        return success_response(
            data={"cancelled": False, "cancel_requested": True, "job_id": job_id},
            request_id=request_id,
            status_code=202,
        )

    if job.status == "cancelled":
        return success_response(data={"cancelled": True, "job_id": job_id}, request_id=request_id)
    return error_response(
        code="INVALID_STATE",
        message=f"Cannot cancel job in status '{job.status}'",
        request_id=request_id,
        status_code=409,
    )


def _latest_ingestion_jobs_by_source(jobs: list[JobRecord]) -> dict[str, JobRecord]:
    mapping: dict[str, JobRecord] = {}
    for job in jobs:
        source_id = job.payload_json.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            continue
        if source_id not in mapping:
            mapping[source_id] = job
    return mapping


def _serialize_job(job: JobRecord) -> dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "job_type": job.job_type,
        "progress": job.progress,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "queue_job_id": job.queue_job_id,
        "queue_name": job.queue_name,
        "dead_lettered": job.dead_lettered,
        "failure_code": job.failure_code,
        "failure_detail": job.error_message,
        "cancel_requested": job.cancel_requested,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "result": job.result_json,
        "error_message": job.error_message,
    }


def _serialize_source(*, source: Source, ingestion_job: JobRecord | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": source.id,
        "notebook_id": source.notebook_id,
        "name": source.name,
        "source_type": source.source_type,
        "status": source.status,
        "path_or_url": source.path_or_url,
        "metadata": source.metadata_json,
        "created_at": source.created_at.isoformat(),
        "ingestion_job": None,
    }
    if ingestion_job is not None:
        payload["ingestion_job"] = _serialize_job(ingestion_job)
    return payload


def _vector_store_from_request(request: Request) -> VectorStoreClient:
    vector_store = getattr(request.app.state, "vector_store", None)
    if isinstance(vector_store, VectorStoreClient):
        return vector_store
    raise RuntimeError("Vector store not initialized")


def _normalized_idempotency_key(raw_key: str | None) -> str | None:
    if raw_key is None or not raw_key.strip():
        return None
    return raw_key.strip()


def _load_cached_payload(user_id: str, operation: str, key: str | None) -> dict[str, Any] | None:
    if key is None:
        return None
    return IdempotencyStore().load(user_id=user_id, operation=operation, idempotency_key=key)


def _store_cached_payload(user_id: str, operation: str, key: str | None, payload: dict[str, Any]) -> None:
    if key is None:
        return
    IdempotencyStore().store(user_id=user_id, operation=operation, idempotency_key=key, payload=payload)


def _enqueue_ingestion_job(
    *,
    user_id: str,
    job_id: str,
    source_id: str,
    request_id: str,
    jobs: JobService,
    retry_max: int,
) -> dict[str, str | None] | JSONResponse:
    try:
        dispatch = TaskQueue.enqueue(
            process_ingestion_job,
            user_id,
            job_id,
            source_id,
            queue=JobQueue.CORE,
            retry_max=retry_max,
        )
    except AppError:
        jobs.fail(
            user_id=user_id,
            job_id=job_id,
            message="Queue backend unavailable",
            failure_code="QUEUE_UNAVAILABLE",
            dead_lettered=True,
        )
        return error_response(
            code="QUEUE_UNAVAILABLE",
            message="Queue backend unavailable",
            request_id=request_id,
            status_code=503,
        )

    queue_job_id = dispatch.get("queue_job_id")
    queue_name = dispatch.get("queue_name")
    if isinstance(queue_job_id, str) and isinstance(queue_name, str):
        jobs.set_queue_info(user_id=user_id, job_id=job_id, queue_job_id=queue_job_id, queue_name=queue_name)
    return dispatch


def _enforce_source_quota(source_repo: SourceRepository, user_id: str, max_sources: int) -> str | None:
    total_sources = len(source_repo.list_for_user(user_id=user_id))
    if total_sources >= max_sources:
        return f"User source limit reached ({max_sources})"
    return None


def _default_notebook_id(db: Session, user_id: str) -> str:
    return NotebookRepository(db).ensure_default_for_user(user_id).id


def _notebook_for_user(db: Session, notebook_id: str, user_id: str) -> object | None:
    return NotebookRepository(db).get_for_user(notebook_id, user_id)


def _resolved_notebook_id(request: Request, db: Session, user_id: str) -> str:
    request_notebook_id = getattr(request.state, "notebook_id", None)
    if isinstance(request_notebook_id, str) and request_notebook_id:
        return request_notebook_id
    return _default_notebook_id(db, user_id)


def _upload_source_for_notebook(
    *,
    notebook_id: str,
    request: Request,
    file: UploadFile,
    idempotency_key: str | None,
    user: AuthenticatedUser,
    db: Session,
) -> JSONResponse:
    if _notebook_for_user(db, notebook_id, user.id) is None:
        request_id = getattr(request.state, "request_id", "")
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    request.state.notebook_id = notebook_id
    return upload_source(request=request, file=file, idempotency_key=idempotency_key, user=user, db=db)


def _ingest_url_for_notebook(
    *,
    notebook_id: str,
    payload: SourceCreateUrlRequest,
    request: Request,
    idempotency_key: str | None,
    user: AuthenticatedUser,
    db: Session,
) -> JSONResponse:
    if _notebook_for_user(db, notebook_id, user.id) is None:
        request_id = getattr(request.state, "request_id", "")
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    request.state.notebook_id = notebook_id
    return ingest_url_source(payload=payload, request=request, idempotency_key=idempotency_key, user=user, db=db)
