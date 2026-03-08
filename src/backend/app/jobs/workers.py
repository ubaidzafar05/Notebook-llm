from __future__ import annotations

import logging

from app.core.exceptions import AppError
from app.db.repositories.job_repo import PodcastRepository
from app.db.repositories.source_repo import SourceRepository
from app.db.session import SessionLocal
from app.embeddings.embedding_service import EmbeddingService
from app.ingestion.ingestion_service import IngestionService
from app.jobs.job_service import JobService
from app.podcast.podcast_service import PodcastService
from app.vector_store.milvus_client import VectorStoreClient

logger = logging.getLogger(__name__)


def process_ingestion_job(user_id: str, job_id: str, source_id: str) -> None:
    db = SessionLocal()
    try:
        vector_store = VectorStoreClient()
        ingestion = IngestionService(
            db=db,
            vector_store=vector_store,
            embedding_service=EmbeddingService(),
        )
        jobs = JobService(db)
        source_repo = SourceRepository(db)
        jobs.start(user_id=user_id, job_id=job_id)
        if jobs.is_cancel_requested(user_id=user_id, job_id=job_id):
            jobs.cancel(user_id=user_id, job_id=job_id, message="Cancelled before processing")
            return
        jobs.set_progress(user_id=user_id, job_id=job_id, progress=30)
        source = source_repo.get_by_id_for_user(source_id=source_id, user_id=user_id)
        if source is None:
            jobs.fail(
                user_id=user_id,
                job_id=job_id,
                message="Source not found",
                failure_code="SOURCE_NOT_FOUND",
                dead_lettered=True,
            )
            return

        chunk_count = ingestion.ingest_source(source)
        if jobs.is_cancel_requested(user_id=user_id, job_id=job_id):
            jobs.cancel(user_id=user_id, job_id=job_id, message="Cancelled during processing")
            return
        jobs.complete(
            user_id=user_id,
            job_id=job_id,
            result={"chunk_count": chunk_count, "source_id": source.id},
        )
    except AppError as exc:
        logger.exception("Ingestion worker failed job_id=%s code=%s", job_id, exc.code)
        jobs = JobService(db)
        job = jobs.get(user_id=user_id, job_id=job_id)
        should_dead_letter = False
        if job is not None:
            should_dead_letter = (job.retry_count + 1) >= job.max_retries
        jobs.fail(
            user_id=user_id,
            job_id=job_id,
            message=exc.message,
            failure_code=exc.code,
            increment_retry=True,
            dead_lettered=should_dead_letter,
        )
        if not should_dead_letter:
            raise
    except Exception:  # noqa: BLE001
        logger.exception("Ingestion worker failed job_id=%s", job_id)
        jobs = JobService(db)
        job = jobs.get(user_id=user_id, job_id=job_id)
        should_dead_letter = False
        if job is not None:
            should_dead_letter = (job.retry_count + 1) >= job.max_retries
        jobs.fail(
            user_id=user_id,
            job_id=job_id,
            message="Unexpected worker failure",
            failure_code="INGESTION_WORKER_FAILED",
            increment_retry=True,
            dead_lettered=should_dead_letter,
        )
        if not should_dead_letter:
            raise
    finally:
        db.close()


def process_podcast_job(user_id: str, podcast_id: str, title: str) -> None:
    db = SessionLocal()
    try:
        service = PodcastService(db)
        service.process_job(user_id=user_id, podcast_id=podcast_id, title=title)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Podcast worker failed podcast_id=%s", podcast_id)
        service = PodcastService(db)
        failure_code = exc.code if isinstance(exc, AppError) else "PODCAST_JOB_FAILED"
        message = exc.message if isinstance(exc, AppError) else str(exc)
        service.fail_job(user_id=user_id, podcast_id=podcast_id, message=message, failure_code=failure_code)
        podcast = PodcastRepository(db).get_for_user(podcast_id=podcast_id, user_id=user_id)
        if podcast is not None and podcast.status != "completed":
            raise
    finally:
        db.close()
