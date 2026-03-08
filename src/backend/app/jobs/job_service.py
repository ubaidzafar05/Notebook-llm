from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import JobRecord, JobStatus
from app.db.repositories.job_repo import JobRepository


class JobService:
    def __init__(self, db: Session) -> None:
        self.repo = JobRepository(db)

    def create(
        self,
        user_id: str,
        notebook_id: str,
        job_type: str,
        payload: dict[str, Any],
        max_retries: int = 2,
    ) -> str:
        job = self.repo.create_job(
            user_id=user_id,
            notebook_id=notebook_id,
            job_type=job_type,
            payload=payload,
            max_retries=max_retries,
        )
        return job.id

    def set_queue_info(self, user_id: str, job_id: str, queue_job_id: str, queue_name: str) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.set_queue_info(job=job, queue_job_id=queue_job_id, queue_name=queue_name)

    def start(self, user_id: str, job_id: str) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        if job.cancel_requested:
            self.repo.update_status(
                job=job,
                status=JobStatus.CANCELLED,
                error_message="Cancelled before start",
                progress=100,
                cancel_requested=True,
            )
            return
        self.repo.update_status(job=job, status=JobStatus.RUNNING, progress=10)

    def set_progress(self, user_id: str, job_id: str, progress: int) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.update_status(job=job, status=JobStatus.RUNNING, progress=progress)

    def complete(self, user_id: str, job_id: str, result: dict[str, Any]) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.update_status(job=job, status=JobStatus.COMPLETED, result_json=result, progress=100)

    def fail(
        self,
        user_id: str,
        job_id: str,
        message: str,
        failure_code: str | None = None,
        increment_retry: bool = False,
        dead_lettered: bool | None = None,
    ) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.update_status(
            job=job,
            status=JobStatus.FAILED,
            error_message=message,
            failure_code=failure_code,
            progress=100,
            increment_retry=increment_retry,
            dead_lettered=dead_lettered,
        )

    def cancel(self, user_id: str, job_id: str, message: str = "Cancelled by user") -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.update_status(
            job=job,
            status=JobStatus.CANCELLED,
            error_message=message,
            progress=100,
            cancel_requested=True,
        )

    def request_cancel(self, user_id: str, job_id: str) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.mark_cancel_requested(job=job)

    def mark_dead_lettered(self, user_id: str, job_id: str) -> None:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return
        self.repo.mark_dead_lettered(job=job)

    def is_cancel_requested(self, user_id: str, job_id: str) -> bool:
        job = self.repo.get_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            return False
        return bool(job.cancel_requested)

    def get(self, user_id: str, job_id: str) -> JobRecord | None:
        return self.repo.get_for_user(job_id=job_id, user_id=user_id)
