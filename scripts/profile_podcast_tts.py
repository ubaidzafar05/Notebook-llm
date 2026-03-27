from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from time import perf_counter

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src" / "backend"))

from app.podcast.tts_service import TtsService  # noqa: E402
from schemas.podcast_script import PodcastScript, PodcastTurn  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile podcast TTS synthesis throughput.")
    parser.add_argument("--output-dir", default=str(ROOT_DIR / "outputs" / "tts-profile"))
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    service = TtsService()
    report = {
        "short": _profile_case(service, output_dir, "short", turn_count=12, sentence_count=2),
        "long": _profile_case(service, output_dir, "long", turn_count=20, sentence_count=4),
    }
    print(json.dumps(report, indent=2))


def _profile_case(
    service: TtsService,
    output_dir: Path,
    case_name: str,
    *,
    turn_count: int,
    sentence_count: int,
) -> dict[str, float | int]:
    case_dir = output_dir / case_name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    script = PodcastScript(turns=_build_turns(turn_count=turn_count, sentence_count=sentence_count))
    started_at = perf_counter()
    tracks = service.synthesize_script(script=script, output_dir=case_dir)
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    total_bytes = sum(track.stat().st_size for track in tracks)
    return {
        "turn_count": len(script.turns),
        "elapsed_ms": elapsed_ms,
        "avg_turn_ms": round(elapsed_ms / max(len(script.turns), 1), 2),
        "track_count": len(tracks),
        "total_bytes": total_bytes,
    }


def _build_turns(*, turn_count: int, sentence_count: int) -> list[PodcastTurn]:
    turns: list[PodcastTurn] = []
    for index in range(turn_count):
        speaker = "HOST" if index % 2 == 0 else "ANALYST"
        turns.append(
            PodcastTurn(
                speaker=speaker,
                text=_turn_text(speaker=speaker, index=index + 1, sentence_count=sentence_count),
            )
        )
    return turns


def _turn_text(*, speaker: str, index: int, sentence_count: int) -> str:
    base = [
        f"{speaker} turn {index} explains how notebook sources become grounded answers.",
        "The passage mentions retrieval, citation scoring, and source-backed synthesis for the research workflow.",
        "It also calls out queue isolation for podcast jobs and why warm model startup matters for responsiveness.",
        "This benchmark sentence exists to create a realistic local TTS workload without depending on external files.",
    ]
    return " ".join(base[:sentence_count])


if __name__ == "__main__":
    main()
