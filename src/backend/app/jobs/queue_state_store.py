from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from rq import Queue, Retry
from rq.job import Job
from rq.registry import FailedJobRegistry

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.redis_client import get_redis_client


@dataclass(slots=True)
class QueueDispatch:
    queue_job_id: str
    queue_name: str


class QueueStateStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.queue_name = self.settings.rq_queue_name

    def enqueue(
        self,
        fn: Callable[..., None],
        *args: Any,
        retry_max: int,
        job_timeout_seconds: int | None = None,
    ) -> QueueDispatch:
        redis = self._redis()
        queue = Queue(self.queue_name, connection=redis)
        retry = Retry(max=retry_max, interval=[15, 45])
        rq_job = queue.enqueue(fn, *args, retry=retry, job_timeout=job_timeout_seconds)
        return QueueDispatch(queue_job_id=rq_job.id, queue_name=self.queue_name)

    def cancel(self, queue_job_id: str) -> bool:
        redis = self._redis()
        try:
            job = Job.fetch(queue_job_id, connection=redis)
        except Exception:
            return False
        try:
            job.cancel()
            return True
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="QUEUE_UNAVAILABLE",
                message="Failed to cancel queued job",
                status_code=503,
            ) from exc

    def is_dead_lettered(self, queue_job_id: str) -> bool:
        redis = self._redis()
        queue = Queue(self.queue_name, connection=redis)
        failed_registry = FailedJobRegistry(queue=queue)
        return queue_job_id in failed_registry.get_job_ids()

    def _redis(self) -> Any:
        try:
            return get_redis_client()
        except AppError as exc:
            raise AppError(
                code="QUEUE_UNAVAILABLE",
                message="Queue backend is unavailable",
                status_code=503,
                details={"cause": exc.code},
            ) from exc
