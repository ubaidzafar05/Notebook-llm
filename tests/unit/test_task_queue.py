from __future__ import annotations

import pytest

from app.core.config import reset_settings_cache
from app.jobs.queue import JobQueue, TaskQueue
from app.jobs.queue_state_store import QueueDispatch, QueueStateStore


def test_task_queue_routes_core_jobs_to_core_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RQ_QUEUE_NAME_CORE", "core-queue")
    monkeypatch.setenv("RQ_QUEUE_NAME_PODCAST", "podcast-queue")
    reset_settings_cache()
    seen: list[str] = []

    def _fake_enqueue(self: QueueStateStore, *args: object, **kwargs: object) -> QueueDispatch:
        _ = (args, kwargs)
        seen.append(self.queue_name)
        return QueueDispatch(queue_job_id="job-1", queue_name=self.queue_name)

    monkeypatch.setattr(QueueStateStore, "enqueue", _fake_enqueue)

    dispatch = TaskQueue.enqueue(lambda: None, queue=JobQueue.CORE)

    assert dispatch["queue_name"] == "core-queue"
    assert seen == ["core-queue"]
    reset_settings_cache()


def test_task_queue_routes_podcast_jobs_to_podcast_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RQ_QUEUE_NAME_CORE", "core-queue")
    monkeypatch.setenv("RQ_QUEUE_NAME_PODCAST", "podcast-queue")
    reset_settings_cache()
    seen: list[str] = []

    def _fake_enqueue(self: QueueStateStore, *args: object, **kwargs: object) -> QueueDispatch:
        _ = (args, kwargs)
        seen.append(self.queue_name)
        return QueueDispatch(queue_job_id="job-2", queue_name=self.queue_name)

    monkeypatch.setattr(QueueStateStore, "enqueue", _fake_enqueue)

    dispatch = TaskQueue.enqueue(lambda: None, queue=JobQueue.PODCAST)

    assert dispatch["queue_name"] == "podcast-queue"
    assert seen == ["podcast-queue"]
    reset_settings_cache()
