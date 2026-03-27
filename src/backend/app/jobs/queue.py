from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.jobs.queue_state_store import QueueStateStore


class TaskQueue:
    @staticmethod
    def enqueue(
        fn: Callable[..., None],
        *args: Any,
        retry_max: int = 2,
        job_timeout_seconds: int | None = None,
    ) -> dict[str, str | None]:
        if not get_settings().rq_strict_mode:
            raise AppError(
                code="INVALID_QUEUE_MODE",
                message="Only strict RQ queue mode is supported",
                status_code=500,
            )
        dispatch = QueueStateStore().enqueue(
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
