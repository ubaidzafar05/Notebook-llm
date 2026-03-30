from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from starlette.responses import Response

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.chat_routes import router as chat_router
from app.api.v1.export_routes import router as export_router
from app.api.v1.health_routes import router as health_router
from app.api.v1.memory_routes import router as memory_router
from app.api.v1.notebook_routes import router as notebook_router
from app.api.v1.podcast_routes import router as podcast_router
from app.api.v1.source_routes import router as source_router
from app.core.config import get_settings, validate_required_runtime_settings
from app.core.exceptions import AppError
from app.core.health_checks import collect_dependency_health, overall_system_state
from app.core.logging import configure_logging
from app.core.metrics import metrics_middleware
from app.core.metrics import router as metrics_router
from app.core.redis_client import get_async_redis_client
from app.db.session import init_db
from app.generation.ollama_client import OllamaClient
from app.vector_store.milvus_client import VectorStoreClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    validate_required_runtime_settings(settings)
    init_db()
    vector_store = VectorStoreClient()
    app_instance.state.vector_store = vector_store

    redis_client = None
    try:
        redis_client = get_async_redis_client()
        await FastAPILimiter.init(redis_client)
        app_instance.state.rate_limiter_ready = True
    except Exception as exc:  # noqa: BLE001
        logger.error("Rate limiter disabled: %s", exc)
        app_instance.state.rate_limiter_ready = False

    dependency_status = collect_dependency_health(vector_store=vector_store)
    overall_status = overall_system_state(dependency_status)
    if overall_status == "degraded":
        logger.warning("Dependency health degraded: %s", dependency_status)
    if settings.ollama_prewarm_on_startup and settings.environment != "test":
        try:
            OllamaClient().warm_model(timeout_seconds=settings.ollama_prewarm_timeout_seconds)
            logger.info("Ollama model prewarm completed model=%s", settings.ollama_chat_model)
        except AppError as exc:
            logger.warning("Ollama model prewarm failed code=%s message=%s", exc.code, exc.message)

    try:
        yield
    finally:
        if redis_client is not None:
            close = getattr(redis_client, "close", None)
            if callable(close):
                await close()


app = FastAPI(title="NotebookLM API", lifespan=lifespan)

settings = get_settings()
if settings.environment != "test":
    allow_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins else [settings.ui_url]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next: callable) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


app.middleware("http")(metrics_middleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    details = []
    for item in exc.errors():
        loc = item.get("loc", [])
        field = ".".join(str(part) for part in loc)
        details.append(
            {
                "field": field,
                "message": item.get("msg", "Invalid value"),
                "type": item.get("type", "validation_error"),
            }
        )
    payload = {
        "data": None,
        "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": details},
        "meta": {"request_id": request_id},
    }
    return JSONResponse(content=payload, status_code=422)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    payload = {
        "data": None,
        "error": {"code": exc.code, "message": exc.message, "details": exc.details},
        "meta": {"request_id": request_id},
    }
    return JSONResponse(content=payload, status_code=exc.status_code)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    if exc.status_code == 429:
        payload = {
            "data": None,
            "error": {"code": "TOO_MANY_REQUESTS", "message": "Rate limit exceeded. Please try again later."},
            "meta": {"request_id": request_id},
        }
        return JSONResponse(content=payload, status_code=429)

    payload = {
        "data": None,
        "error": {"code": "HTTP_ERROR", "message": str(exc.detail)},
        "meta": {"request_id": request_id},
    }
    return JSONResponse(content=payload, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    payload = {
        "data": None,
        "error": {"code": "INTERNAL_ERROR", "message": "Internal server error"},
        "meta": {"request_id": request_id},
    }
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(content=payload, status_code=500)


app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(notebook_router)
app.include_router(source_router)
app.include_router(chat_router)
app.include_router(podcast_router)
app.include_router(memory_router)
app.include_router(export_router)
