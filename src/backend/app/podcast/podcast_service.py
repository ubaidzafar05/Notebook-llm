from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models import PodcastJob, PodcastStatus
from app.db.repositories.job_repo import PodcastRepository
from app.db.repositories.source_repo import ChunkRepository
from app.podcast.audio_mixer import AudioMixer
from app.podcast.script_generator import ScriptGenerator
from app.podcast.tts_service import TtsService


class PodcastService:
    def __init__(self, db: Session) -> None:
        self.repo = PodcastRepository(db)
        self.chunks = ChunkRepository(db)
        self.script_generator = ScriptGenerator()
        self.tts_service = TtsService()
        self.mixer = AudioMixer()

    def create_job(
        self,
        user_id: str,
        notebook_id: str,
        source_ids: list[str],
        voice_label: str | None = None,
        retried_from_podcast_id: str | None = None,
    ) -> str:
        podcast = self.repo.create(
            user_id=user_id,
            notebook_id=notebook_id,
            source_ids=source_ids,
            voice_label=voice_label,
            retried_from_podcast_id=retried_from_podcast_id,
        )
        return podcast.id

    def process_job(self, user_id: str, podcast_id: str, title: str, voice_label: str | None = None) -> None:
        podcast = self.repo.get_for_user(podcast_id=podcast_id, user_id=user_id)
        if podcast is None:
            return
        if voice_label is not None and voice_label.strip():
            podcast.voice_label = voice_label.strip()
        podcast.status = PodcastStatus.PROCESSING.value
        self.repo.save(podcast)

        chunks = self.chunks.list_for_sources(
            source_ids=podcast.source_ids_json,
            user_id=user_id,
            notebook_id=podcast.notebook_id,
        )
        if not chunks:
            raise AppError(
                code="PODCAST_NO_SOURCE_CONTEXT",
                message="No source chunks available for podcast generation",
                status_code=400,
            )
        context = "\n\n".join(chunk.text for chunk in chunks)
        script, _ = self.script_generator.generate(title=title, source_context=context)
        tracks = self.tts_service.synthesize_script(
            script=script,
            output_dir=Path("outputs/podcasts") / podcast.id,
            voice_label=podcast.voice_label,
        )
        output_path = Path("outputs/podcasts") / f"{podcast.id}.mp3"
        duration_ms = self.mixer.merge_tracks(tracks=tracks, output_path=output_path)

        podcast.script = script.as_text()
        podcast.output_path = str(output_path)
        podcast.duration_ms = duration_ms
        podcast.status = PodcastStatus.COMPLETED.value
        self.repo.save(podcast)

    def fail_job(
        self,
        user_id: str,
        podcast_id: str,
        message: str,
        failure_code: str | None = None,
    ) -> None:
        podcast = self.repo.get_for_user(podcast_id=podcast_id, user_id=user_id)
        if podcast is None:
            return
        podcast.status = PodcastStatus.FAILED.value
        podcast.failure_code = failure_code
        podcast.failure_detail = message
        podcast.error_message = message
        self.repo.save(podcast)

    def get_job(self, user_id: str, podcast_id: str) -> PodcastJob | None:
        return self.repo.get_for_user(podcast_id=podcast_id, user_id=user_id)
