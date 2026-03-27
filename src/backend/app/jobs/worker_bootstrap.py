from __future__ import annotations

import os

from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.podcast.podcast_service import PodcastService


def main() -> None:
    configure_logging()
    init_db()
    db = SessionLocal()
    try:
        PodcastService(db).recover_interrupted_jobs()
    finally:
        db.close()
    os.execvp("rq", ["rq", "worker", "notebooklm-default", "--url", "redis://redis:6379/0"])


if __name__ == "__main__":
    main()
