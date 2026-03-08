from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.core.exceptions import AppError
from app.ingestion.parsers.audio_parser import AudioParser
from app.ingestion.source_registry import ParsedSegment


def _extract_subtitle_text(subtitle_path: Path) -> str:
    lines: list[str] = []
    for line in subtitle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("WEBVTT") or raw.startswith("NOTE"):
            continue
        if "-->" in raw or raw.isdigit():
            continue
        lines.append(raw)
    return " ".join(lines).strip()


class YouTubeParser:
    def __init__(self) -> None:
        self.audio_parser = AudioParser()

    def parse(self, url: str, work_dir: Path) -> list[ParsedSegment]:
        metadata_cmd = ["yt-dlp", "--dump-single-json", url]
        metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, check=False)
        if metadata_result.returncode != 0:
            raise AppError(
                code="YOUTUBE_FETCH_FAILED",
                message="Failed to fetch YouTube metadata",
                status_code=400,
                details={"failure_stage": "fetch"},
            )

        info = json.loads(metadata_result.stdout)
        title = str(info.get("title", "youtube"))

        subtitle_template = work_dir / "subtitle.%(ext)s"
        subtitle_cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang",
            "en",
            "--skip-download",
            "-o",
            str(subtitle_template),
            url,
        ]
        subprocess.run(subtitle_cmd, capture_output=True, text=True, check=False)
        vtt_files = sorted(work_dir.glob("subtitle*.vtt"))
        if vtt_files:
            subtitle_text = _extract_subtitle_text(vtt_files[0])
            if subtitle_text:
                citation: dict[str, str | int | float | None] = {"source": title, "url": url}
                return [ParsedSegment(text=subtitle_text, citation=citation)]

        audio_template = work_dir / "audio.%(ext)s"
        audio_cmd = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            str(audio_template),
            url,
        ]
        audio_result = subprocess.run(audio_cmd, capture_output=True, text=True, check=False)
        if audio_result.returncode != 0:
            raise AppError(
                code="YOUTUBE_AUDIO_DOWNLOAD_FAILED",
                message="Could not download YouTube audio",
                status_code=400,
                details={"failure_stage": "fetch"},
            )

        audio_files = sorted(work_dir.glob("audio*.mp3"))
        if not audio_files:
            raise AppError(
                code="YOUTUBE_AUDIO_DOWNLOAD_FAILED",
                message="Audio conversion produced no file",
                status_code=400,
                details={"failure_stage": "fetch"},
            )
        try:
            return self.audio_parser.parse(audio_files[0])
        except AppError as exc:
            raise AppError(
                code="YOUTUBE_TRANSCRIBE_FAILED",
                message=exc.message,
                status_code=exc.status_code,
                details={"failure_stage": "parse"},
            ) from exc
