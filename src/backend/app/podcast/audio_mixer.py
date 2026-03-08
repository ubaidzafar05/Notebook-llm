from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment


class AudioMixer:
    def merge_tracks(self, tracks: list[Path], output_path: Path) -> int:
        combined = AudioSegment.silent(duration=0)
        for track in tracks:
            segment = AudioSegment.from_file(track)
            combined += segment + AudioSegment.silent(duration=400)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.export(output_path, format="mp3")
        return len(combined)
