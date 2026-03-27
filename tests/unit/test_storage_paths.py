from __future__ import annotations

from pathlib import Path

from app.api.v1.podcast_routes import _resolve_output_path
from app.core.config import ROOT_DIR
from app.ingestion.ingestion_service import _resolve_storage_path, _storage_record_path


def test_storage_record_path_stays_repo_relative() -> None:
    absolute_path = (ROOT_DIR / "data" / "uploads" / "user-1" / "notes.txt").resolve()
    recorded_path = _storage_record_path(absolute_path)
    assert recorded_path == Path("data/uploads/user-1/notes.txt")


def test_resolve_storage_path_recovers_absolute_path_from_relative_record() -> None:
    stored_path = Path("data/uploads/user-1/notes.txt")
    assert _resolve_storage_path(stored_path) == (ROOT_DIR / stored_path).resolve()


def test_resolve_output_path_supports_legacy_relative_paths() -> None:
    stored_path = "outputs/podcasts/demo.mp3"
    assert _resolve_output_path(stored_path) == (ROOT_DIR / stored_path).resolve()
