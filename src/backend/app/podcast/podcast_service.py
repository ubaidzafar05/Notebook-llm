from __future__ import annotations

import logging
import signal
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.config import ROOT_DIR, get_settings
from app.core.exceptions import AppError
from app.db.models import Chunk, PodcastJob, PodcastStatus, Source
from app.db.repositories.job_repo import PodcastRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.podcast.audio_mixer import AudioMixer
from app.podcast.script_generator import ScriptGenerator
from app.podcast.tts_service import TtsService

logger = logging.getLogger(__name__)


class PodcastService:
    def __init__(self, db: Session) -> None:
        self.settings = get_settings()
        self.repo = PodcastRepository(db)
        self.chunks = ChunkRepository(db)
        self.sources = SourceRepository(db)
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
        podcast.failure_code = None
        podcast.failure_detail = None
        podcast.error_message = None
        self.repo.save(podcast)
        logger.info("Podcast job started podcast_id=%s notebook_id=%s", podcast.id, podcast.notebook_id)

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
        sources = self.sources.list_by_ids_for_notebook(
            user_id=user_id,
            notebook_id=podcast.notebook_id,
            source_ids=podcast.source_ids_json,
        )
        context = _build_podcast_context(
            sources=sources,
            chunks=chunks,
            max_chars=self.settings.podcast_context_max_chars,
            chunks_per_source=self.settings.podcast_chunks_per_source,
            excerpt_chars=self.settings.podcast_chunk_excerpt_chars,
        )
        script, _ = self._run_stage(
            stage_name="script_generation",
            timeout_seconds=self.settings.ollama_podcast_timeout_seconds,
            timeout_code="PODCAST_SCRIPT_TIMEOUT",
            timeout_message="Podcast script generation timed out",
            operation=lambda: self.script_generator.generate(title=title, source_context=context),
        )
        podcast_root = (ROOT_DIR / "outputs" / "podcasts").resolve()
        tracks = self._run_stage(
            stage_name="tts_synthesis",
            timeout_seconds=self.settings.podcast_tts_timeout_seconds,
            timeout_code="PODCAST_TTS_TIMEOUT",
            timeout_message="Podcast audio synthesis timed out",
            operation=lambda: self.tts_service.synthesize_script(
                script=script,
                output_dir=podcast_root / podcast.id,
                voice_label=podcast.voice_label,
            ),
        )
        output_path = podcast_root / f"{podcast.id}.mp3"
        duration_ms = self._run_stage(
            stage_name="audio_mix",
            timeout_seconds=self.settings.podcast_mix_timeout_seconds,
            timeout_code="PODCAST_MIX_TIMEOUT",
            timeout_message="Podcast mastering timed out",
            operation=lambda: self.mixer.merge_tracks(tracks=tracks, output_path=output_path),
        )

        podcast.script = script.as_text()
        podcast.output_path = str(_podcast_record_path(output_path))
        podcast.duration_ms = duration_ms
        podcast.status = PodcastStatus.COMPLETED.value
        self.repo.save(podcast)
        logger.info("Podcast job completed podcast_id=%s duration_ms=%s", podcast.id, duration_ms)

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

    def recover_interrupted_jobs(self) -> int:
        recovered = 0
        for podcast in self.repo.list_by_status(PodcastStatus.PROCESSING.value):
            podcast.status = PodcastStatus.FAILED.value
            podcast.failure_code = "PODCAST_WORKER_INTERRUPTED"
            podcast.failure_detail = "Podcast job was interrupted by a worker restart"
            podcast.error_message = "Podcast job was interrupted by a worker restart"
            self.repo.save(podcast)
            recovered += 1
        if recovered:
            logger.warning("Recovered interrupted podcast jobs count=%s", recovered)
        return recovered

    def _run_stage(
        self,
        *,
        stage_name: str,
        timeout_seconds: int,
        timeout_code: str,
        timeout_message: str,
        operation: Callable[[], object],
    ):
        start = perf_counter()
        logger.info("Podcast stage started podcast_stage=%s timeout_seconds=%s", stage_name, timeout_seconds)
        with _alarm_timeout(
            seconds=timeout_seconds,
            code=timeout_code,
            message=timeout_message,
            details={"stage": stage_name},
        ):
            result = operation()
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.info("Podcast stage completed podcast_stage=%s elapsed_ms=%s", stage_name, elapsed_ms)
        return result


def _build_podcast_context(
    *,
    sources: list[Source],
    chunks: list[Chunk],
    max_chars: int,
    chunks_per_source: int,
    excerpt_chars: int,
) -> str:
    # REASONING:
    # 1. Podcast prompts should receive a compact source brief, not raw notebook chunk dumps.
    # 2. Grouping excerpts by source preserves provenance while keeping the token budget bounded.
    # 3. Hard caps on section count and chars prevent local Ollama timeouts on long notebooks.
    chunks_by_source = _group_chunks_by_source(chunks)
    remaining_chars = max(max_chars, 500)
    sections: list[str] = []
    for source in sources:
        section = _build_source_section(
            source=source,
            chunks=chunks_by_source.get(source.id, []),
            chunks_per_source=chunks_per_source,
            excerpt_chars=excerpt_chars,
        )
        if not section:
            continue
        if len(section) > remaining_chars and sections:
            break
        clipped_section = _clip_section(section=section, max_chars=remaining_chars)
        sections.append(clipped_section)
        remaining_chars -= len(clipped_section) + 2
        if remaining_chars <= 0:
            break
    return "\n\n".join(sections)


def _group_chunks_by_source(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    grouped: dict[str, list[Chunk]] = {}
    for chunk in sorted(chunks, key=lambda item: (item.source_id, item.chunk_index)):
        grouped.setdefault(chunk.source_id, []).append(chunk)
    return grouped


def _build_source_section(
    *,
    source: Source,
    chunks: list[Chunk],
    chunks_per_source: int,
    excerpt_chars: int,
) -> str:
    if not chunks:
        return ""
    metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
    summary = _clean_excerpt(str(metadata.get("summary", "")), excerpt_chars)
    lines = [f"Source: {source.name}", f"Type: {source.source_type}"]
    if summary:
        lines.append(f"Summary: {summary}")
    lines.append("Key excerpts:")
    for index, chunk in enumerate(chunks[: max(chunks_per_source, 1)], start=1):
        citation = chunk.citation_json if isinstance(chunk.citation_json, dict) else {}
        page = citation.get("page")
        prefix = f"{index}. page {page}: " if page is not None else f"{index}. "
        lines.append(prefix + _clean_excerpt(chunk.text, excerpt_chars))
    return "\n".join(lines)


def _clean_excerpt(text: str, limit: int) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 16, 0)].rstrip() + " (truncated)"


def _clip_section(*, section: str, max_chars: int) -> str:
    if len(section) <= max_chars:
        return section
    clipped = section[: max(max_chars - 16, 0)].rstrip()
    return clipped + " (truncated)"


def _podcast_record_path(path: Path) -> Path:
    absolute_path = path.resolve()
    try:
        return absolute_path.relative_to(ROOT_DIR)
    except ValueError:
        return absolute_path


@contextmanager
def _alarm_timeout(*, seconds: int, code: str, message: str, details: dict[str, str]):
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handle_timeout(signum: int, frame: object) -> None:
        _ = (signum, frame)
        raise AppError(code=code, message=message, status_code=504, details=details)

    try:
        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _handle_timeout)
    except ValueError:
        yield
        return

    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
