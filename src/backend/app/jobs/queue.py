from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.jobs.queue_state_store import QueueStateStore


class JobQueue(StrEnum):
    CORE = "core"
    PODCAST = "podcast"


class TaskQueue:
    @staticmethod
    def enqueue(
        fn: Callable[..., None],
        *args: Any,
        queue: JobQueue = JobQueue.CORE,
        retry_max: int = 2,
        job_timeout_seconds: int | None = None,
    ) -> dict[str, str | None]:
        settings = get_settings()
        if not settings.rq_strict_mode:
            raise AppError(
                code="INVALID_QUEUE_MODE",
                message="Only strict RQ queue mode is supported",
                status_code=500,
            )
        dispatch = QueueStateStore(_resolve_queue_name(queue=queue)).enqueue(
            fn,
            *args,
            retry_max=retry_max,
            job_timeout_seconds=job_timeout_seconds,
        )
        return {
            "mode": "rq",
            "queue_job_id": dispatch.queue_job_id,
            "queue_name": dispatch.queue_name,
        }


def _resolve_queue_name(*, queue: JobQueue) -> str:
    settings = get_settings()
    if queue is JobQueue.PODCAST:
        return settings.rq_queue_name_podcast
    return settings.rq_queue_name_core
