from __future__ import annotations

from pathlib import Path
from time import sleep

import requests

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.ingestion.source_registry import ParsedSegment


class AudioParser:
    def parse(self, file_path: Path) -> list[ParsedSegment]:
        settings = get_settings()
        if settings.assemblyai_api_key:
            return self._parse_with_assemblyai(file_path=file_path, api_key=settings.assemblyai_api_key)

        return self._parse_with_local_whisper(file_path=file_path)

    def _parse_with_local_whisper(self, file_path: Path) -> list[ParsedSegment]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise AppError(
                code="AUDIO_UPSTREAM_FAILED",
                message="faster-whisper is not installed",
                status_code=503,
                details={"failure_stage": "parse"},
            ) from exc

        model = WhisperModel("base", compute_type="int8")
        segments, _ = model.transcribe(str(file_path), vad_filter=True)
        parsed_segments: list[ParsedSegment] = []
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            citation: dict[str, str | int | float | None] = {
                "source": file_path.name,
                "start_timestamp": float(segment.start),
                "end_timestamp": float(segment.end),
            }
            parsed_segments.append(ParsedSegment(text=text, citation=citation))

        if not parsed_segments:
            raise AppError(
                code="AUDIO_PARSE_FAILED",
                message="No transcription segments produced",
                status_code=400,
                details={"failure_stage": "parse"},
            )
        return parsed_segments

    def _parse_with_assemblyai(self, file_path: Path, api_key: str) -> list[ParsedSegment]:
        headers = {"authorization": api_key}
        try:
            with file_path.open("rb") as file_obj:
                upload_response = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers=headers,
                    data=file_obj,
                    timeout=120,
                )
            upload_response.raise_for_status()
        except requests.Timeout as exc:
            raise AppError(
                code="AUDIO_TIMEOUT",
                message="AssemblyAI upload timed out",
                status_code=504,
                details={"failure_stage": "fetch"},
            ) from exc
        except requests.RequestException as exc:
            raise AppError(
                code="AUDIO_UPSTREAM_FAILED",
                message="AssemblyAI upload failed",
                status_code=502,
                details={"failure_stage": "fetch"},
            ) from exc
        upload_url = upload_response.json().get("upload_url")
        if not isinstance(upload_url, str):
            raise AppError(
                code="AUDIO_UPSTREAM_FAILED",
                message="AssemblyAI upload failed",
                status_code=502,
                details={"failure_stage": "fetch"},
            )

        try:
            transcript_response = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                headers=headers,
                json={"audio_url": upload_url, "speaker_labels": True},
                timeout=30,
            )
            transcript_response.raise_for_status()
        except requests.Timeout as exc:
            raise AppError(
                code="AUDIO_TIMEOUT",
                message="AssemblyAI transcript initialization timed out",
                status_code=504,
                details={"failure_stage": "fetch"},
            ) from exc
        except requests.RequestException as exc:
            raise AppError(
                code="AUDIO_UPSTREAM_FAILED",
                message="AssemblyAI transcript initialization failed",
                status_code=502,
                details={"failure_stage": "fetch"},
            ) from exc
        transcript_id = transcript_response.json().get("id")
        if not isinstance(transcript_id, str):
            raise AppError(
                code="AUDIO_UPSTREAM_FAILED",
                message="AssemblyAI transcript init failed",
                status_code=502,
                details={"failure_stage": "fetch"},
            )

        status_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        for _ in range(40):
            try:
                poll = requests.get(status_url, headers=headers, timeout=20)
                poll.raise_for_status()
            except requests.Timeout as exc:
                raise AppError(
                    code="AUDIO_TIMEOUT",
                    message="AssemblyAI polling timed out",
                    status_code=504,
                    details={"failure_stage": "fetch"},
                ) from exc
            except requests.RequestException as exc:
                raise AppError(
                    code="AUDIO_UPSTREAM_FAILED",
                    message="AssemblyAI polling failed",
                    status_code=502,
                    details={"failure_stage": "fetch"},
                ) from exc
            body = poll.json()
            status = body.get("status")
            if status == "completed":
                text = str(body.get("text", "")).strip()
                if not text:
                    raise AppError(
                        code="AUDIO_PARSE_FAILED",
                        message="AssemblyAI returned empty transcript",
                        status_code=400,
                        details={"failure_stage": "parse"},
                    )
                citation: dict[str, str | int | float | None] = {"source": file_path.name}
                return [ParsedSegment(text=text, citation=citation)]
            if status == "error":
                raise AppError(
                    code="AUDIO_UPSTREAM_FAILED",
                    message="AssemblyAI transcription failed",
                    status_code=502,
                    details={"failure_stage": "parse"},
                )
            sleep(1.5)
        raise AppError(
            code="AUDIO_TIMEOUT",
            message="AssemblyAI transcription timeout",
            status_code=504,
            details={"failure_stage": "fetch"},
        )
