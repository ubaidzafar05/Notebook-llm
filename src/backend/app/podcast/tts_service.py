from __future__ import annotations

import importlib
import logging
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any

from app.core.circuit_breaker import CircuitBreaker
from app.core.config import get_settings
from app.core.exceptions import AppError
from schemas.podcast_script import PodcastScript, PodcastTurn

logger = logging.getLogger(__name__)


class TtsService:
    def __init__(self) -> None:
        self.settings = get_settings()
        provider = self.settings.podcast_tts_provider.lower().strip()
        if provider != "kokoro":
            raise AppError(
                code="PODCAST_TTS_PROVIDER_INVALID",
                message="Only Kokoro TTS provider is supported",
                status_code=500,
                details={"provider": provider},
            )

    @CircuitBreaker(name="kokoro_tts", failure_threshold=2, recovery_timeout=120, exceptions=(AppError, Exception))
    def synthesize_script(self, script: PodcastScript, output_dir: Path, voice_label: str | None = None) -> list[Path]:
        engine = _get_cached_kokoro_engine()
        output_dir.mkdir(parents=True, exist_ok=True)
        tracks: list[Path] = []
        for idx, turn in enumerate(script.turns, start=1):
            wav_path = output_dir / f"line_{idx:03d}.wav"
            logger.info(
                "Podcast TTS turn started turn=%s speaker=%s voice_label=%s output=%s",
                idx,
                turn.speaker,
                voice_label,
                wav_path.name,
            )
            started_at = perf_counter()
            _synthesize_turn(engine=engine, turn=turn, output_path=wav_path, voice_label=voice_label)
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            logger.info(
                "Podcast TTS turn completed turn=%s elapsed_ms=%s bytes=%s",
                idx,
                elapsed_ms,
                wav_path.stat().st_size,
            )
            tracks.append(wav_path)
        return tracks


@lru_cache(maxsize=1)
def _get_cached_kokoro_engine() -> Any:
    return _load_kokoro_engine()


def _load_kokoro_engine() -> Any:
    settings = get_settings()
    try:
        module = importlib.import_module("kokoro")
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="KOKORO_UNAVAILABLE",
            message="Kokoro package is not installed or failed to import",
            status_code=500,
            details={"install_hint": "Install a compatible `kokoro` package in the backend environment"},
        ) from exc
    if not hasattr(module, "KPipeline"):
        raise AppError(
            code="KOKORO_UNAVAILABLE",
            message="Kokoro package does not expose KPipeline",
            status_code=500,
        )
    _require_spacy_model(settings.kokoro_spacy_model)
    try:
        return module.KPipeline(lang_code="a", repo_id=settings.kokoro_repo_id)
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="KOKORO_UNAVAILABLE",
            message="Kokoro pipeline initialization failed",
            status_code=500,
            details={
                "repo_id": settings.kokoro_repo_id,
                "spacy_model": settings.kokoro_spacy_model,
            },
        ) from exc


def _require_spacy_model(model_name: str) -> None:
    try:
        spacy = importlib.import_module("spacy")
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="KOKORO_DEPENDENCY_MISSING",
            message="spaCy is required for Kokoro podcast synthesis",
            status_code=500,
            details={"dependency": "spacy", "model": model_name},
        ) from exc
    if spacy.util.is_package(model_name):
        return
    raise AppError(
        code="KOKORO_DEPENDENCY_MISSING",
        message="Kokoro English spaCy model is missing from the runtime image",
        status_code=500,
        details={"dependency": model_name},
    )


def _synthesize_turn(*, engine: Any, turn: PodcastTurn, output_path: Path, voice_label: str | None) -> None:
    voice = _voice_for_speaker(turn.speaker, voice_label)
    try:
        generator = engine(turn.text, voice=voice)
        first = next(generator)
    except StopIteration as exc:
        raise AppError(code="KOKORO_SYNTH_FAILED", message="Kokoro generated no audio", status_code=502) from exc
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="KOKORO_SYNTH_FAILED",
            message=f"Kokoro synthesis failed for {turn.speaker}",
            status_code=502,
        ) from exc
    audio = first[2]
    try:
        import soundfile as sf
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="KOKORO_DEPENDENCY_MISSING",
            message="soundfile is required to write Kokoro audio",
            status_code=500,
        ) from exc
    sf.write(file=str(output_path), data=audio, samplerate=24000)


def _voice_for_speaker(speaker: str, voice_label: str | None) -> str:
    settings = get_settings()
    normalized_label = (voice_label or "").strip().lower()
    if normalized_label == "verse analyst":
        return settings.kokoro_voice_analyst
    if normalized_label == "nova narrator":
        return settings.kokoro_voice_host
    if speaker == "HOST":
        return settings.kokoro_voice_host
    return settings.kokoro_voice_analyst
