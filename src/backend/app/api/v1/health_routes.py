from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.health_checks import collect_dependency_health, overall_system_state
from app.core.response_envelope import success_response

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health_check(request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    vector_store = getattr(request.app.state, "vector_store", None)
    statuses = collect_dependency_health(vector_store=vector_store)
    dependencies = {name: status.to_dict() for name, status in statuses.items()}
    return success_response(
        data={"status": overall_system_state(statuses), "dependencies": dependencies},
        request_id=request_id,
    )


@router.get("/health/dependencies")
def dependency_health_check(request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    vector_store = getattr(request.app.state, "vector_store", None)
    statuses = collect_dependency_health(vector_store=vector_store)
    return success_response(
        data={name: status.to_dict() for name, status in statuses.items()},
        request_id=request_id,
    )


@router.get("/health/readiness")
def readiness_check(request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    vector_store = getattr(request.app.state, "vector_store", None)
    statuses = collect_dependency_health(vector_store=vector_store)
    overall = overall_system_state(statuses)
    status_code = 200 if overall == "ok" else 503
    return success_response(
        data={
            "status": "ready" if overall == "ok" else "not_ready",
            "required_dependencies": {
                "postgres": statuses["postgres"].to_dict(),
                "redis": statuses["redis"].to_dict(),
                "milvus": statuses["milvus"].to_dict(),
                "provider_gate": statuses["provider_gate"].to_dict(),
            },
            "optional_dependencies": {
                "zep": statuses["zep"].to_dict(),
            },
        },
        request_id=request_id,
        status_code=status_code,
    )
