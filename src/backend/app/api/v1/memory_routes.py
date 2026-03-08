from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.core.response_envelope import success_response
from app.db.session import get_db
from app.memory.memory_service import MemoryService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.get("/sessions/{session_id}")
def get_session_memory(
    session_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    summary, provider = MemoryService(db).summarize_session(user_id=user.id, session_id=session_id)
    return success_response(
        data={"session_id": session_id, "summary": summary, "provider": provider},
        request_id=request_id,
    )


@router.post("/sessions/{session_id}/summarize")
def summarize_session(
    session_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    summary, provider = MemoryService(db).summarize_session(user_id=user.id, session_id=session_id)
    return success_response(
        data={"session_id": session_id, "summary": summary, "provider": provider},
        request_id=request_id,
    )
