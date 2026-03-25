"""Lightweight Prometheus-style metrics exposed at /metrics.

Counters and histograms are stored in-process (no external dependency).
For production deployments behind multiple workers, use a proper
prometheus_client with multi-process mode or push-gateway.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from starlette.responses import Response

router = APIRouter(tags=["metrics"])

# ── In-process counters ──────────────────────────────────────────────

_counters: dict[str, int] = defaultdict(int)
_histograms: dict[str, list[float]] = defaultdict(list)


def inc(name: str, amount: int = 1) -> None:
    _counters[name] += amount


def observe(name: str, value: float) -> None:
    bucket = _histograms[name]
    bucket.append(value)
    # Keep at most 10 000 observations per metric to limit memory
    if len(bucket) > 10_000:
        del bucket[: len(bucket) - 10_000]


# ── Middleware ────────────────────────────────────────────────────────

async def metrics_middleware(request: Request, call_next: Any) -> Response:
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed = time.perf_counter() - start

    method = request.method
    status = response.status_code
    path = request.url.path

    inc(f'http_requests_total{{method="{method}",status="{status}"}}')
    observe(f'http_request_duration_seconds{{method="{method}",path="{path}"}}', elapsed)

    return response


# ── /metrics endpoint ─────────────────────────────────────────────────

@router.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> PlainTextResponse:
    lines: list[str] = []

    # Counters
    for key in sorted(_counters):
        lines.append(f"{key} {_counters[key]}")

    # Histograms (emit sum and count)
    for key in sorted(_histograms):
        bucket = _histograms[key]
        if bucket:
            total = sum(bucket)
            count = len(bucket)
            base = key.split("{")[0]
            labels = key[len(base):]
            lines.append(f"{base}_sum{labels} {total:.6f}")
            lines.append(f"{base}_count{labels} {count}")

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; charset=utf-8")
