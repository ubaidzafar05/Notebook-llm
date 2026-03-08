from __future__ import annotations

import json
import importlib
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import UUID

import requests
from dotenv import load_dotenv
from redis import Redis
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src/backend"))

from app.core.config import get_settings, reset_settings_cache, validate_required_runtime_settings  # noqa: E402

Status = Literal["pass", "fail", "warn", "skip"]


@dataclass(slots=True)
class CheckResult:
    name: str
    status: Status
    detail: str
    required: bool
    latency_ms: int | None


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    reset_settings_cache()
    settings = get_settings()
    checks = [
        _check_runtime_config(),
        _check_postgres(settings.database_url),
        _check_schema_migration(settings.database_url),
        _check_redis(settings.redis_url),
        _check_milvus(settings.milvus_uri, settings.milvus_collection),
        _check_ollama(settings.ollama_base_url),
        _check_openrouter(settings.openrouter_base_url, settings.openrouter_api_key),
        _check_zep(settings.zep_project_id, settings.zep_api_key),
        _check_ffmpeg(),
        _check_kokoro(),
    ]
    checks.append(_check_provider_gate(checks))
    failures = [item for item in checks if item.required and item.status == "fail"]
    payload = {
        "ok": not failures,
        "required_failures": [item.name for item in failures],
        "checks": [asdict(item) for item in checks],
    }
    print(json.dumps(payload, indent=2))
    return 1 if failures else 0


def _check_runtime_config() -> CheckResult:
    start = perf_counter()
    try:
        validate_required_runtime_settings(get_settings())
    except RuntimeError as exc:
        return _result(name="runtime_config", status="fail", detail=str(exc), required=True, start=start)
    return _result(name="runtime_config", status="pass", detail="Required runtime config is valid", required=True, start=start)


def _check_postgres(database_url: str) -> CheckResult:
    start = perf_counter()
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        return _result(name="postgres", status="fail", detail=f"Postgres unreachable: {exc}", required=True, start=start)
    return _result(name="postgres", status="pass", detail="Postgres reachable", required=True, start=start)


def _check_schema_migration(database_url: str) -> CheckResult:
    start = perf_counter()
    try:
        config = Config(str(ROOT_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()
        if head_revision is None:
            return _result(
                name="db_migration",
                status="fail",
                detail="Alembic head revision is not defined",
                required=True,
                start=start,
            )

        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
    except Exception as exc:  # noqa: BLE001
        return _result(
            name="db_migration",
            status="fail",
            detail=f"Migration check failed: {exc}",
            required=True,
            start=start,
        )

    current_revision = row[0] if row is not None else ""
    if current_revision != head_revision:
        return _result(
            name="db_migration",
            status="fail",
            detail=f"Schema revision mismatch current={current_revision or 'none'} expected={head_revision}",
            required=True,
            start=start,
        )
    return _result(
        name="db_migration",
        status="pass",
        detail=f"Schema at Alembic head {head_revision}",
        required=True,
        start=start,
    )


def _check_redis(redis_url: str) -> CheckResult:
    start = perf_counter()
    try:
        Redis.from_url(redis_url).ping()
    except Exception as exc:  # noqa: BLE001
        return _result(name="redis", status="fail", detail=f"Redis unreachable: {exc}", required=True, start=start)
    return _result(name="redis", status="pass", detail="Redis reachable", required=True, start=start)


def _check_milvus(milvus_uri: str, collection_name: str) -> CheckResult:
    start = perf_counter()
    try:
        from pymilvus import Collection, connections, utility
    except ImportError as exc:
        return _result(
            name="milvus",
            status="fail",
            detail=f"Milvus import failure: {exc}",
            required=True,
            start=start,
        )
    try:
        connections.connect(alias="preflight", uri=milvus_uri, timeout=5)
        if utility.has_collection(collection_name, using="preflight"):
            Collection(collection_name, using="preflight")
    except Exception as exc:  # noqa: BLE001
        return _result(
            name="milvus",
            status="fail",
            detail=f"Milvus connection failure: {exc}",
            required=True,
            start=start,
        )
    return _result(name="milvus", status="pass", detail="Milvus reachable", required=True, start=start)


def _check_ollama(base_url: str) -> CheckResult:
    start = perf_counter()
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=4)
    except requests.RequestException as exc:
        return _result(name="ollama", status="fail", detail=f"Ollama unreachable: {exc}", required=False, start=start)
    if response.status_code < 500:
        return _result(name="ollama", status="pass", detail=f"Ollama reachable ({response.status_code})", required=False, start=start)
    return _result(name="ollama", status="fail", detail=f"Ollama returned {response.status_code}", required=False, start=start)


def _check_openrouter(base_url: str, api_key: str) -> CheckResult:
    start = perf_counter()
    if not api_key:
        return _result(name="openrouter", status="skip", detail="OPENROUTER_API_KEY not configured", required=False, start=start)
    try:
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=4,
        )
    except requests.RequestException as exc:
        return _result(name="openrouter", status="fail", detail=f"OpenRouter unreachable: {exc}", required=False, start=start)
    if response.status_code == 200:
        return _result(name="openrouter", status="pass", detail="OpenRouter reachable", required=False, start=start)
    if response.status_code in {401, 403}:
        return _result(name="openrouter", status="fail", detail="OpenRouter auth failed", required=False, start=start)
    return _result(name="openrouter", status="fail", detail=f"OpenRouter returned {response.status_code}", required=False, start=start)


def _check_zep(project_id: str, api_key: str) -> CheckResult:
    start = perf_counter()
    if not api_key:
        return _result(name="zep", status="fail", detail="ZEP_API_KEY is missing", required=True, start=start)
    if not project_id:
        return _result(name="zep", status="fail", detail="ZEP_PROJECT_ID is missing", required=True, start=start)
    try:
        UUID(project_id)
    except ValueError:
        return _result(name="zep", status="fail", detail="ZEP_PROJECT_ID must be a valid UUID", required=True, start=start)
    try:
        response = requests.get(
            "https://api.getzep.com/api/v2/projects/info",
            headers={"Authorization": f"Api-Key {api_key}"},
            timeout=4,
        )
    except requests.Timeout:
        return _result(name="zep", status="fail", detail="Zep timeout", required=True, start=start)
    except requests.RequestException as exc:
        return _result(name="zep", status="fail", detail=f"Zep unreachable: {exc}", required=True, start=start)
    if response.status_code == 200:
        body = response.json()
        project_uuid = str(body.get("project", {}).get("uuid", ""))
        if project_uuid and project_uuid != project_id:
            return _result(
                name="zep",
                status="fail",
                detail=f"Zep key project mismatch ({project_uuid})",
                required=True,
                start=start,
            )
        return _result(name="zep", status="pass", detail="Zep reachable", required=True, start=start)
    if response.status_code in {401, 403}:
        return _result(name="zep", status="fail", detail="Zep auth failure", required=True, start=start)
    if response.status_code == 404:
        return _result(name="zep", status="fail", detail="Zep project not found", required=True, start=start)
    return _result(name="zep", status="fail", detail=f"Zep returned {response.status_code}", required=True, start=start)


def _check_ffmpeg() -> CheckResult:
    start = perf_counter()
    if shutil.which("ffmpeg") is None:
        return _result(name="ffmpeg", status="warn", detail="ffmpeg binary not found in PATH", required=False, start=start)
    return _result(name="ffmpeg", status="pass", detail="ffmpeg available", required=False, start=start)


def _check_kokoro() -> CheckResult:
    start = perf_counter()
    try:
        module = importlib.import_module("kokoro")
    except Exception as exc:  # noqa: BLE001
        return _result(
            name="kokoro",
            status="fail",
            detail=f"Kokoro import failed: {exc}",
            required=True,
            start=start,
        )
    if not hasattr(module, "KPipeline"):
        return _result(
            name="kokoro",
            status="fail",
            detail="Kokoro package does not expose KPipeline",
            required=True,
            start=start,
        )
    return _result(name="kokoro", status="pass", detail="Kokoro available", required=True, start=start)


def _check_provider_gate(checks: list[CheckResult]) -> CheckResult:
    ollama_ok = _status_of(checks, "ollama") == "pass"
    openrouter_ok = _status_of(checks, "openrouter") == "pass"
    if ollama_ok or openrouter_ok:
        return CheckResult(
            name="provider_gate",
            status="pass",
            detail="At least one generation provider is reachable",
            required=True,
            latency_ms=None,
        )
    return CheckResult(
        name="provider_gate",
        status="fail",
        detail="Neither Ollama nor OpenRouter is reachable",
        required=True,
        latency_ms=None,
    )


def _status_of(checks: list[CheckResult], name: str) -> Status:
    for check in checks:
        if check.name == name:
            return check.status
    return "fail"


def _result(name: str, status: Status, detail: str, required: bool, start: float) -> CheckResult:
    latency_ms = int((perf_counter() - start) * 1000)
    return CheckResult(name=name, status=status, detail=detail, required=required, latency_ms=latency_ms)


if __name__ == "__main__":
    raise SystemExit(main())
