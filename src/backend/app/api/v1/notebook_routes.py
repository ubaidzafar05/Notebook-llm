from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.response_envelope import error_response, success_response
from app.db.models import Notebook
from app.db.repositories.notebook_repo import NotebookRepository
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
    updated = repo.update(notebook, title=payload.title, description=payload.description)
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


def _serialize_notebook(notebook: Notebook) -> dict[str, object]:
    return {
        "id": notebook.id,
        "title": notebook.title,
        "description": notebook.description,
        "is_default": notebook.is_default,
        "created_at": notebook.created_at.isoformat(),
        "updated_at": notebook.updated_at.isoformat(),
    }
