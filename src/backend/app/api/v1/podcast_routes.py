from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.config import get_settings
from app.core.response_envelope import error_response, success_response
from app.db.models import PodcastJob
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.session import get_db
from app.jobs.queue import TaskQueue
from app.jobs.workers import process_podcast_job
from app.podcast.podcast_service import PodcastService
from schemas.podcast import CreatePodcastRequest, RetryPodcastRequest

router = APIRouter(prefix="/api/v1", tags=["podcasts"])


@router.post("/podcasts")
def create_podcast(
    payload: CreatePodcastRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    settings = get_settings()
    service = PodcastService(db)
    notebook_id = _resolved_notebook_id(db, user.id, None)
    podcast_id = service.create_job(user_id=user.id, notebook_id=notebook_id, source_ids=payload.source_ids)
    dispatch = TaskQueue.enqueue(
        process_podcast_job,
        user.id,
        podcast_id,
        payload.title,
        retry_max=settings.job_max_retries_podcast,
    )
    return success_response(
        data={
            "podcast_id": podcast_id,
            "dispatch_mode": dispatch["mode"],
            "queue_job_id": dispatch["queue_job_id"],
            "queue_name": dispatch["queue_name"],
        },
        request_id=request_id,
        status_code=202,
    )


@router.get("/podcasts")
def list_podcasts(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    podcasts = PodcastService(db).repo.list_for_user(user.id)
    return success_response(data=[_serialize_podcast(item) for item in podcasts], request_id=request_id)


@router.get("/podcasts/{podcast_id}")
def get_podcast(
    podcast_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    podcast = PodcastService(db).get_job(user_id=user.id, podcast_id=podcast_id)
    if podcast is None:
        return error_response(code="NOT_FOUND", message="Podcast not found", request_id=request_id, status_code=404)

    return success_response(data=_serialize_podcast(podcast), request_id=request_id)


@router.get("/podcasts/{podcast_id}/audio")
def download_podcast_audio(
    podcast_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    request_id = getattr(request.state, "request_id", "")
    podcast = PodcastService(db).get_job(user_id=user.id, podcast_id=podcast_id)
    if podcast is None or not podcast.output_path:
        return error_response(code="NOT_FOUND", message="Audio not ready", request_id=request_id, status_code=404)

    output_path = Path(podcast.output_path)
    if not output_path.exists():
        return error_response(code="NOT_FOUND", message="Audio file missing", request_id=request_id, status_code=404)
    return FileResponse(path=output_path, media_type="audio/mpeg", filename=output_path.name)


@router.post("/podcasts/{podcast_id}/retry")
def retry_podcast(
    podcast_id: str,
    payload: RetryPodcastRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    settings = get_settings()
    service = PodcastService(db)
    original = service.get_job(user_id=user.id, podcast_id=podcast_id)
    if original is None:
        return error_response(code="NOT_FOUND", message="Podcast not found", request_id=request_id, status_code=404)

    new_podcast_id = service.create_job(
        user_id=user.id,
        notebook_id=original.notebook_id or _resolved_notebook_id(db, user.id, None),
        source_ids=original.source_ids_json,
        retried_from_podcast_id=podcast_id,
    )
    dispatch = TaskQueue.enqueue(
        process_podcast_job,
        user.id,
        new_podcast_id,
        payload.title,
        retry_max=settings.job_max_retries_podcast,
    )
    return success_response(
        data={
            "podcast_id": new_podcast_id,
            "retried_from_podcast_id": podcast_id,
            "dispatch_mode": dispatch["mode"],
            "queue_job_id": dispatch["queue_job_id"],
            "queue_name": dispatch["queue_name"],
        },
        request_id=request_id,
        status_code=202,
    )


@router.post("/notebooks/{notebook_id}/podcasts")
def create_notebook_podcast(
    notebook_id: str,
    payload: CreatePodcastRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    settings = get_settings()
    service = PodcastService(db)
    podcast_id = service.create_job(user_id=user.id, notebook_id=resolved_notebook_id, source_ids=payload.source_ids)
    dispatch = TaskQueue.enqueue(
        process_podcast_job,
        user.id,
        podcast_id,
        payload.title,
        retry_max=settings.job_max_retries_podcast,
    )
    return success_response(
        data={
            "podcast_id": podcast_id,
            "dispatch_mode": dispatch["mode"],
            "queue_job_id": dispatch["queue_job_id"],
            "queue_name": dispatch["queue_name"],
        },
        request_id=request_id,
        status_code=202,
    )


@router.get("/notebooks/{notebook_id}/podcasts")
def list_notebook_podcasts(
    notebook_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    podcasts = PodcastService(db).repo.list_for_notebook(user_id=user.id, notebook_id=resolved_notebook_id)
    return success_response(data=[_serialize_podcast(item) for item in podcasts], request_id=request_id)


@router.get("/notebooks/{notebook_id}/podcasts/{podcast_id}")
def get_notebook_podcast(
    notebook_id: str,
    podcast_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    podcast = PodcastService(db).repo.get_for_notebook(podcast_id=podcast_id, user_id=user.id, notebook_id=resolved_notebook_id)
    if podcast is None:
        return error_response(code="NOT_FOUND", message="Podcast not found", request_id=request_id, status_code=404)
    return success_response(data=_serialize_podcast(podcast), request_id=request_id)


@router.get("/notebooks/{notebook_id}/podcasts/{podcast_id}/audio")
def download_notebook_podcast_audio(
    notebook_id: str,
    podcast_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    podcast = PodcastService(db).repo.get_for_notebook(podcast_id=podcast_id, user_id=user.id, notebook_id=resolved_notebook_id)
    if podcast is None:
        request_id = getattr(request.state, "request_id", "")
        return error_response(code="NOT_FOUND", message="Podcast not found", request_id=request_id, status_code=404)
    return download_podcast_audio(podcast_id=podcast_id, request=request, user=user, db=db)


@router.post("/notebooks/{notebook_id}/podcasts/{podcast_id}/retry")
def retry_notebook_podcast(
    notebook_id: str,
    podcast_id: str,
    payload: RetryPodcastRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    settings = get_settings()
    resolved_notebook_id = _resolved_notebook_id(db, user.id, notebook_id)
    service = PodcastService(db)
    original = service.repo.get_for_notebook(podcast_id=podcast_id, user_id=user.id, notebook_id=resolved_notebook_id)
    if original is None:
        return error_response(code="NOT_FOUND", message="Podcast not found", request_id=request_id, status_code=404)
    new_podcast_id = service.create_job(
        user_id=user.id,
        notebook_id=resolved_notebook_id,
        source_ids=original.source_ids_json,
        retried_from_podcast_id=podcast_id,
    )
    dispatch = TaskQueue.enqueue(
        process_podcast_job,
        user.id,
        new_podcast_id,
        payload.title,
        retry_max=settings.job_max_retries_podcast,
    )
    return success_response(
        data={
            "podcast_id": new_podcast_id,
            "retried_from_podcast_id": podcast_id,
            "dispatch_mode": dispatch["mode"],
            "queue_job_id": dispatch["queue_job_id"],
            "queue_name": dispatch["queue_name"],
        },
        request_id=request_id,
        status_code=202,
    )


def _resolved_notebook_id(db: Session, user_id: str, notebook_id: str | None) -> str:
    repo = NotebookRepository(db)
    if notebook_id is None:
        return repo.ensure_default_for_user(user_id).id
    notebook = repo.get_for_user(notebook_id, user_id)
    if notebook is None:
        return repo.ensure_default_for_user(user_id).id
    return notebook.id


def _serialize_podcast(podcast: PodcastJob) -> dict[str, object]:
    return {
        "id": podcast.id,
        "notebook_id": podcast.notebook_id,
        "source_ids": podcast.source_ids_json,
        "status": podcast.status,
        "output_path": podcast.output_path,
        "duration_ms": podcast.duration_ms,
        "error_message": podcast.error_message,
        "failure_code": podcast.failure_code,
        "failure_detail": podcast.failure_detail,
        "retried_from_podcast_id": podcast.retried_from_podcast_id,
        "created_at": podcast.created_at.isoformat(),
        "updated_at": podcast.updated_at.isoformat(),
    }
