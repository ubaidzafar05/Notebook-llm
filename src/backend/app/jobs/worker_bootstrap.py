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
    os.execvp("rq", ["rq", "worker", "notebooklm-default", "--url", "redis://redis:6379/0"])


if __name__ == "__main__":
    main()
