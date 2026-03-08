from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.chat_routes import router as chat_router
from app.api.v1.health_routes import router as health_router
from app.api.v1.memory_routes import router as memory_router
from app.api.v1.notebook_routes import router as notebook_router
from app.api.v1.podcast_routes import router as podcast_router
from app.api.v1.source_routes import router as source_router
from app.core.config import get_settings, validate_required_runtime_settings
from app.core.exceptions import AppError
from app.core.health_checks import collect_dependency_health, overall_system_state
from app.core.logging import configure_logging
from app.db.session import init_db
from app.vector_store.milvus_client import VectorStoreClient

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    validate_required_runtime_settings(settings)
    init_db()
    vector_store = VectorStoreClient()
    app_instance.state.vector_store = vector_store
    dependency_status = collect_dependency_health(vector_store=vector_store)
    overall_status = overall_system_state(dependency_status)
    if overall_status == "degraded":
        logger.warning(
            "Startup checks detected degraded dependencies",
            extra={
                "correlation_id": "",
                "dependencies": {
                    name: status.to_dict() for name, status in dependency_status.items()
                },
            },
        )
    else:
        logger.info("Startup checks healthy", extra={"correlation_id": ""})
    logger.info("Application startup complete")
    yield


app = FastAPI(title="NotebookLM Clone API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.ui_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "x-request-id"],
)


@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    error: dict[str, object] = {"code": exc.code, "message": exc.message}
    if exc.details:
        error["details"] = exc.details
    payload = {
        "data": None,
        "error": error,
        "meta": {"request_id": request_id},
    }
    logger.warning("Handled AppError", extra={"correlation_id": request_id})
    return JSONResponse(content=payload, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    details = [
        {"field": ".".join(str(part) for part in err.get("loc", [])), "message": err.get("msg", "Invalid value")}
        for err in exc.errors()
    ]
    payload = {
        "data": None,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": details,
        },
        "meta": {"request_id": request_id},
    }
    logger.warning("Handled request validation error", extra={"correlation_id": request_id})
    return JSONResponse(content=payload, status_code=422)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    logger.exception("Unhandled exception", extra={"correlation_id": request_id})
    payload = {
        "data": None,
        "error": {"code": "INTERNAL_ERROR", "message": "Unexpected error"},
        "meta": {"request_id": request_id},
    }
    return JSONResponse(content=payload, status_code=500)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(notebook_router)
app.include_router(source_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(podcast_router)
