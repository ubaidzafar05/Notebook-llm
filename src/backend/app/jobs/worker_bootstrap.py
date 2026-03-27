from __future__ import annotations

import logging
import os

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.podcast.podcast_service import PodcastService
from app.podcast.tts_service import TtsService

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    init_db()
    settings = get_settings()
    role = settings.rq_worker_role.strip().lower()
    if role == "podcast":
        _prepare_podcast_worker(settings)
    os.execvp("rq", ["rq", "worker", *_worker_queues(settings), "--url", settings.redis_url])


def _prepare_podcast_worker(settings) -> None:
    db = SessionLocal()
    try:
        PodcastService(db).recover_interrupted_jobs()
    finally:
        db.close()
    if settings.kokoro_prewarm_on_startup:
        try:
            TtsService().warm_runtime()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kokoro runtime prewarm failed: %s", exc)


def _worker_queues(settings) -> list[str]:
    configured = [item.strip() for item in settings.rq_worker_queues.split(",") if item.strip()]
    if configured:
        return configured
    if settings.rq_worker_role.strip().lower() == "podcast":
        return [settings.rq_queue_name_podcast]
    return [settings.rq_queue_name_core]


if __name__ == "__main__":
    main()
