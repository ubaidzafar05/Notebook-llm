from __future__ import annotations

import pytest

from app.core.exceptions import AppError
from app.db.models import Notebook, User
from app.db.repositories.job_repo import PodcastRepository
from app.db.session import SessionLocal
from app.jobs.workers import process_podcast_job
from app.podcast.podcast_service import PodcastService


def test_podcast_worker_marks_job_failed_on_app_error(monkeypatch) -> None:
    db = SessionLocal()
    try:
        user = User(email="podcast-worker@example.com", password_hash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)

        notebook = Notebook(user_id=user.id, title="Notebook")
        db.add(notebook)
        db.commit()
        db.refresh(notebook)

        podcast = PodcastRepository(db).create(
            user_id=user.id,
            notebook_id=notebook.id,
            source_ids=["src-1"],
        )
        user_id = user.id
        podcast_id = podcast.id
    finally:
        db.close()

    def _raise_timeout(self: PodcastService, user_id: str, podcast_id: str, title: str, voice_label: str | None = None) -> None:
        _ = (self, user_id, podcast_id, title, voice_label)
        raise AppError(code="PODCAST_SCRIPT_TIMEOUT", message="Podcast script generation timed out", status_code=504)

    monkeypatch.setattr(PodcastService, "process_job", _raise_timeout)

    with pytest.raises(AppError) as exc:
        process_podcast_job(user_id=user_id, podcast_id=podcast_id, title="Timeout case")
    assert exc.value.code == "PODCAST_SCRIPT_TIMEOUT"

    verify_db = SessionLocal()
    try:
        failed = PodcastRepository(verify_db).get_for_user(podcast_id=podcast_id, user_id=user_id)
        assert failed is not None
        assert failed.status == "failed"
        assert failed.failure_code == "PODCAST_SCRIPT_TIMEOUT"
        assert failed.error_message == "Podcast script generation timed out"
    finally:
        verify_db.close()


def test_recover_interrupted_podcast_jobs_marks_processing_rows_failed() -> None:
    db = SessionLocal()
    try:
        user = User(email="podcast-recovery@example.com", password_hash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)

        notebook = Notebook(user_id=user.id, title="Notebook")
        db.add(notebook)
        db.commit()
        db.refresh(notebook)

        repo = PodcastRepository(db)
        processing = repo.create(user_id=user.id, notebook_id=notebook.id, source_ids=["src-1"])
        completed = repo.create(user_id=user.id, notebook_id=notebook.id, source_ids=["src-2"])
        processing.status = "processing"
        completed.status = "completed"
        repo.save(processing)
        repo.save(completed)

        recovered = PodcastService(db).recover_interrupted_jobs()
        assert recovered == 1

        refreshed_processing = repo.get_for_user(processing.id, user.id)
        refreshed_completed = repo.get_for_user(completed.id, user.id)
        assert refreshed_processing is not None
        assert refreshed_processing.status == "failed"
        assert refreshed_processing.failure_code == "PODCAST_WORKER_INTERRUPTED"
        assert refreshed_completed is not None
        assert refreshed_completed.status == "completed"
    finally:
        db.close()
