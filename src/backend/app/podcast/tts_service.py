from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from app.core.circuit_breaker import CircuitBreaker
from app.core.config import get_settings
from app.core.exceptions import AppError
from schemas.podcast_script import PodcastScript, PodcastTurn


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
        engine = _load_kokoro_engine()
        output_dir.mkdir(parents=True, exist_ok=True)
        tracks: list[Path] = []
        for idx, turn in enumerate(script.turns, start=1):
            wav_path = output_dir / f"line_{idx:03d}.wav"
            _synthesize_turn(engine=engine, turn=turn, output_path=wav_path, voice_label=voice_label)
            tracks.append(wav_path)
        return tracks


def _load_kokoro_engine() -> Any:
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
    return module.KPipeline(lang_code="a")


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
