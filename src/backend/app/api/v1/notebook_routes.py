from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.response_envelope import error_response, success_response
from app.db.models import Notebook
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.source_repo import SourceRepository
from app.db.repositories.usage_repo import NotebookUsageRepository
from app.db.session import get_db
from schemas.notebook import NotebookCreateRequest, NotebookUpdateRequest

router = APIRouter(prefix="/api/v1/notebooks", tags=["notebooks"])


@router.post("")
def create_notebook(
    payload: NotebookCreateRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    notebook = NotebookRepository(db).create(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
    )
    return success_response(data=_serialize_notebook(notebook), request_id=request_id, status_code=201)


@router.get("")
def list_notebooks(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    notebooks = NotebookRepository(db).list_for_user(user.id)
    return success_response(data=[_serialize_notebook(item) for item in notebooks], request_id=request_id)


@router.get("/{notebook_id}")
def get_notebook(
    notebook_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    notebook = NotebookRepository(db).get_for_user(notebook_id, user.id)
    if notebook is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    return success_response(data=_serialize_notebook(notebook), request_id=request_id)


@router.patch("/{notebook_id}")
def update_notebook(
    notebook_id: str,
    payload: NotebookUpdateRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    repo = NotebookRepository(db)
    notebook = repo.get_for_user(notebook_id, user.id)
    if notebook is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    updated = repo.update(
        notebook,
        title=payload.title,
        description=payload.description,
        is_pinned=payload.is_pinned,
    )
    return success_response(data=_serialize_notebook(updated), request_id=request_id)


@router.delete("/{notebook_id}")
def delete_notebook(
    notebook_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    repo = NotebookRepository(db)
    notebook = repo.get_for_user(notebook_id, user.id)
    if notebook is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    if notebook.is_default:
        return error_response(
            code="DEFAULT_NOTEBOOK_PROTECTED",
            message="Default notebook cannot be deleted",
            request_id=request_id,
            status_code=409,
        )
    repo.delete(notebook)
    return success_response(data={"deleted": True, "notebook_id": notebook_id}, request_id=request_id)


@router.get("/{notebook_id}/usage")
def get_notebook_usage(
    notebook_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    notebook = NotebookRepository(db).get_for_user(notebook_id, user.id)
    if notebook is None:
        return error_response(code="NOT_FOUND", message="Notebook not found", request_id=request_id, status_code=404)
    usage = NotebookUsageRepository(db).get_or_create(notebook_id)
    sources = SourceRepository(db).list_for_notebook(user_id=user.id, notebook_id=notebook_id)
    top_sources = [
        {
            "id": source.id,
            "title": source.name,
            "chunks": int(source.metadata_json.get("chunks", 0)) if isinstance(source.metadata_json, dict) else 0,
        }
        for source in sources[:6]
    ]
    data = {
        "notebook_id": notebook_id,
        "total_messages": usage.total_messages,
        "total_sources": usage.total_sources,
        "total_prompt_tokens_est": usage.total_prompt_tokens_est,
        "total_response_tokens_est": usage.total_response_tokens_est,
        "estimated_cost_usd": usage.estimated_cost_usd,
        "last_activity_at": usage.last_activity_at.isoformat() if usage.last_activity_at else None,
        "top_sources": top_sources,
    }
    return success_response(data=data, request_id=request_id)


def _serialize_notebook(notebook: Notebook) -> dict[str, object]:
    return {
        "id": notebook.id,
        "title": notebook.title,
        "description": notebook.description,
        "is_default": notebook.is_default,
        "is_pinned": notebook.is_pinned,
        "pinned_at": notebook.pinned_at.isoformat() if notebook.pinned_at else None,
        "created_at": notebook.created_at.isoformat(),
        "updated_at": notebook.updated_at.isoformat(),
    }
