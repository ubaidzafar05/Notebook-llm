from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JobRecord, JobStatus, PodcastJob


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(
        self,
        user_id: str,
        notebook_id: str,
        job_type: str,
        payload: dict[str, Any],
        max_retries: int = 2,
        queue_job_id: str | None = None,
        queue_name: str | None = None,
    ) -> JobRecord:
        job = JobRecord(
            user_id=user_id,
            notebook_id=notebook_id,
            job_type=job_type,
            payload_json=payload,
            max_retries=max_retries,
            queue_job_id=queue_job_id,
            queue_name=queue_name,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_for_user(self, job_id: str, user_id: str) -> JobRecord | None:
        stmt = select(JobRecord).where(JobRecord.id == job_id, JobRecord.user_id == user_id)
        return self.db.scalar(stmt)

    def list_for_user(
        self,
        *,
        user_id: str,
        job_type: str | None = None,
        limit: int = 500,
    ) -> list[JobRecord]:
        stmt = (
            select(JobRecord)
            .where(JobRecord.user_id == user_id)
            .order_by(JobRecord.created_at.desc())
            .limit(limit)
        )
        if job_type is not None:
            stmt = stmt.where(JobRecord.job_type == job_type)
        return list(self.db.scalars(stmt).all())

    def get_for_notebook(self, job_id: str, user_id: str, notebook_id: str) -> JobRecord | None:
        stmt = select(JobRecord).where(
            JobRecord.id == job_id,
            JobRecord.user_id == user_id,
            JobRecord.notebook_id == notebook_id,
        )
        return self.db.scalar(stmt)

    def list_for_notebook(
        self,
        *,
        user_id: str,
        notebook_id: str,
        job_type: str | None = None,
        limit: int = 200,
    ) -> list[JobRecord]:
        stmt = (
            select(JobRecord)
            .where(JobRecord.user_id == user_id, JobRecord.notebook_id == notebook_id)
            .order_by(JobRecord.created_at.desc())
            .limit(limit)
        )
        if job_type is not None:
            stmt = stmt.where(JobRecord.job_type == job_type)
        return list(self.db.scalars(stmt).all())

    def update_status(
        self,
        job: JobRecord,
        status: JobStatus,
        result_json: dict[str, Any] | None = None,
        error_message: str | None = None,
        failure_code: str | None = None,
        progress: int | None = None,
        increment_retry: bool = False,
        dead_lettered: bool | None = None,
        cancel_requested: bool | None = None,
    ) -> JobRecord:
        job.status = status.value
        job.updated_at = datetime.now(UTC)
        if status == JobStatus.RUNNING and job.started_at is None:
            job.started_at = datetime.now(UTC)
        if status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            job.finished_at = datetime.now(UTC)
        if result_json is not None:
            job.result_json = result_json
        if error_message is not None:
            job.error_message = error_message
        if failure_code is not None:
            job.failure_code = failure_code
        if progress is not None:
            job.progress = max(0, min(progress, 100))
        if increment_retry:
            job.retry_count = job.retry_count + 1
        if dead_lettered is not None:
            job.dead_lettered = dead_lettered
        if cancel_requested is not None:
            job.cancel_requested = cancel_requested
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_queue_info(self, job: JobRecord, queue_job_id: str, queue_name: str) -> JobRecord:
        job.queue_job_id = queue_job_id
        job.queue_name = queue_name
        job.updated_at = datetime.now(UTC)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_dead_lettered(self, job: JobRecord) -> JobRecord:
        job.dead_lettered = True
        job.updated_at = datetime.now(UTC)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_cancel_requested(self, job: JobRecord) -> JobRecord:
        job.cancel_requested = True
        job.updated_at = datetime.now(UTC)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job


class PodcastRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        user_id: str,
        notebook_id: str,
        source_ids: list[str],
        voice_label: str | None = None,
        retried_from_podcast_id: str | None = None,
    ) -> PodcastJob:
        podcast = PodcastJob(
            user_id=user_id,
            notebook_id=notebook_id,
            source_ids_json=source_ids,
            voice_label=voice_label,
            retried_from_podcast_id=retried_from_podcast_id,
        )
        self.db.add(podcast)
        self.db.commit()
        self.db.refresh(podcast)
        return podcast

    def get_for_user(self, podcast_id: str, user_id: str) -> PodcastJob | None:
        stmt = select(PodcastJob).where(PodcastJob.id == podcast_id, PodcastJob.user_id == user_id)
        return self.db.scalar(stmt)

    def list_for_user(self, user_id: str) -> list[PodcastJob]:
        stmt = (
            select(PodcastJob)
            .where(PodcastJob.user_id == user_id)
            .order_by(PodcastJob.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_for_notebook(self, podcast_id: str, user_id: str, notebook_id: str) -> PodcastJob | None:
        stmt = select(PodcastJob).where(
            PodcastJob.id == podcast_id,
            PodcastJob.user_id == user_id,
            PodcastJob.notebook_id == notebook_id,
        )
        return self.db.scalar(stmt)

    def list_for_notebook(self, user_id: str, notebook_id: str) -> list[PodcastJob]:
        stmt = (
            select(PodcastJob)
            .where(PodcastJob.user_id == user_id, PodcastJob.notebook_id == notebook_id)
            .order_by(PodcastJob.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def save(self, podcast: PodcastJob) -> PodcastJob:
        podcast.updated_at = datetime.now(UTC)
        self.db.add(podcast)
        self.db.commit()
        self.db.refresh(podcast)
        return podcast
