from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Literal
from uuid import UUID

import requests
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.vector_store.milvus_client import VectorStoreClient


DependencyState = Literal["up", "down", "degraded", "skipped"]


@dataclass(slots=True)
class DependencyStatus:
    state: DependencyState
    detail: str
    latency_ms: int | None

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "status": self.state,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
        }


def collect_dependency_health(
    *,
    vector_store: VectorStoreClient | None = None,
) -> dict[str, DependencyStatus]:
    statuses: dict[str, DependencyStatus] = {}
    statuses["postgres"] = _check_postgres()
    statuses["redis"] = _check_redis()
    statuses["milvus"] = _check_milvus(vector_store=vector_store)
    statuses["ollama"] = _check_http_service(path="/api/tags", service_name="ollama")
    statuses["openrouter"] = _check_openrouter()
    statuses["zep"] = _check_zep()
    statuses["provider_gate"] = _check_provider_gate(statuses)
    return statuses


def overall_system_state(statuses: dict[str, DependencyStatus]) -> Literal["ok", "degraded"]:
    required = ("postgres", "redis", "milvus", "zep", "provider_gate")
    for name in required:
        if statuses[name].state != "up":
            return "degraded"
    return "ok"


def _check_postgres() -> DependencyStatus:
    start = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = int((perf_counter() - start) * 1000)
        return DependencyStatus(state="up", detail="Postgres reachable", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus(state="down", detail=f"Postgres check failed: {exc}", latency_ms=None)


def _check_redis() -> DependencyStatus:
    settings = get_settings()
    start = perf_counter()
    try:
        client = Redis.from_url(settings.redis_url)
        client.ping()
        latency_ms = int((perf_counter() - start) * 1000)
        return DependencyStatus(state="up", detail="Redis reachable", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus(state="down", detail=f"Redis check failed: {exc}", latency_ms=None)


def _check_milvus(vector_store: VectorStoreClient | None) -> DependencyStatus:
    if vector_store is not None:
        reason, detail = vector_store.milvus_diagnostics()
        if vector_store.is_milvus_ready():
            return DependencyStatus(state="up", detail=detail, latency_ms=None)
        return DependencyStatus(state="degraded", detail=f"{reason}: {detail}", latency_ms=None)
    return DependencyStatus(
        state="degraded",
        detail="Milvus unavailable; using in-memory vector fallback",
        latency_ms=None,
    )


def _check_http_service(path: str, service_name: Literal["ollama"]) -> DependencyStatus:
    settings = get_settings()
    if settings.environment == "test":
        return DependencyStatus(
            state="skipped",
            detail=f"{service_name} check skipped in test environment",
            latency_ms=None,
        )
    base_url = settings.ollama_base_url
    start = perf_counter()
    try:
        response = requests.get(f"{base_url}{path}", timeout=3)
        latency_ms = int((perf_counter() - start) * 1000)
        if response.status_code < 500:
            return DependencyStatus(
                state="up",
                detail=f"{service_name} reachable (status={response.status_code})",
                latency_ms=latency_ms,
            )
        return DependencyStatus(
            state="down",
            detail=f"{service_name} returned {response.status_code}",
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus(state="down", detail=f"{service_name} check failed: {exc}", latency_ms=None)


def _check_openrouter() -> DependencyStatus:
    settings = get_settings()
    if settings.environment == "test":
        return DependencyStatus(state="skipped", detail="OpenRouter check skipped in test environment", latency_ms=None)
    if not settings.openrouter_api_key:
        return DependencyStatus(
            state="skipped",
            detail="OpenRouter API key not configured",
            latency_ms=None,
        )

    start = perf_counter()
    try:
        response = requests.get(
            f"{settings.openrouter_base_url}/models",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            timeout=4,
        )
        latency_ms = int((perf_counter() - start) * 1000)
        if response.status_code == 200:
            return DependencyStatus(
                state="up",
                detail="OpenRouter reachable",
                latency_ms=latency_ms,
            )
        if response.status_code in {401, 403}:
            return DependencyStatus(
                state="degraded",
                detail=f"OpenRouter reachable but auth failed ({response.status_code})",
                latency_ms=latency_ms,
            )
        if response.status_code < 500:
            return DependencyStatus(
                state="degraded",
                detail=f"OpenRouter returned {response.status_code}",
                latency_ms=latency_ms,
            )
        return DependencyStatus(
            state="down",
            detail=f"OpenRouter returned {response.status_code}",
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus(state="down", detail=f"OpenRouter check failed: {exc}", latency_ms=None)


def _check_zep() -> DependencyStatus:
    settings = get_settings()
    if not settings.zep_api_key:
        return DependencyStatus(state="down", detail="ZEP_API_KEY is missing", latency_ms=None)
    if not settings.zep_project_id:
        return DependencyStatus(state="down", detail="ZEP_PROJECT_ID is missing", latency_ms=None)
    try:
        UUID(settings.zep_project_id)
    except ValueError:
        return DependencyStatus(state="down", detail="ZEP_PROJECT_ID must be a valid UUID", latency_ms=None)
    if settings.environment == "test":
        return DependencyStatus(state="up", detail="Zep check skipped in test environment", latency_ms=None)

    start = perf_counter()
    try:
        response = requests.get(
            "https://api.getzep.com/api/v2/projects/info",
            headers={"Authorization": f"Api-Key {settings.zep_api_key}"},
            timeout=4,
        )
        latency_ms = int((perf_counter() - start) * 1000)
        if response.status_code == 200:
            body = response.json()
            project_uuid = str(body.get("project", {}).get("uuid", ""))
            if project_uuid and project_uuid != settings.zep_project_id:
                return DependencyStatus(
                    state="down",
                    detail=f"Zep key project mismatch ({project_uuid})",
                    latency_ms=latency_ms,
                )
            return DependencyStatus(state="up", detail="Zep reachable", latency_ms=latency_ms)
        if response.status_code in {401, 403}:
            return DependencyStatus(state="down", detail="Zep auth failed", latency_ms=latency_ms)
        if response.status_code == 404:
            return DependencyStatus(state="down", detail="Zep project not found", latency_ms=latency_ms)
        if response.status_code < 500:
            return DependencyStatus(
                state="degraded",
                detail=f"Zep returned {response.status_code}",
                latency_ms=latency_ms,
            )
        return DependencyStatus(state="down", detail=f"Zep returned {response.status_code}", latency_ms=latency_ms)
    except requests.Timeout:
        return DependencyStatus(state="down", detail="Zep check timed out", latency_ms=None)
    except requests.RequestException as exc:
        return DependencyStatus(state="down", detail=f"Zep check failed: {exc}", latency_ms=None)


def _check_provider_gate(statuses: dict[str, DependencyStatus]) -> DependencyStatus:
    provider_names = ("ollama", "openrouter")
    if any(statuses[name].state == "up" for name in provider_names):
        healthy = [name for name in provider_names if statuses[name].state == "up"]
        return DependencyStatus(state="up", detail=f"Providers available: {', '.join(healthy)}", latency_ms=None)
    settings = get_settings()
    if settings.environment == "test" and any(statuses[name].state == "skipped" for name in provider_names):
        return DependencyStatus(state="up", detail="Provider checks skipped in test environment", latency_ms=None)
    failing = [f"{name}={statuses[name].state}" for name in provider_names]
    return DependencyStatus(state="down", detail=f"No generation provider available ({', '.join(failing)})", latency_ms=None)
