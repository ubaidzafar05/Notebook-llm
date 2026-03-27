from __future__ import annotations

import importlib

import pytest

from app.core.exceptions import AppError
from app.podcast import tts_service


class _FakePipelineFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return object()


def test_load_kokoro_engine_requires_spacy_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_kokoro = type("FakeKokoro", (), {"KPipeline": _FakePipelineFactory()})()
    fake_spacy = type("FakeSpacy", (), {"util": type("Util", (), {"is_package": staticmethod(lambda name: False)})})()

    def _fake_import(name: str):
        if name == "kokoro":
            return fake_kokoro
        if name == "spacy":
            return fake_spacy
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    with pytest.raises(AppError) as exc:
        tts_service._load_kokoro_engine()

    assert exc.value.code == "KOKORO_DEPENDENCY_MISSING"
    assert "spaCy model" in exc.value.message


def test_load_kokoro_engine_passes_configured_repo_id(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _FakePipelineFactory()
    fake_kokoro = type("FakeKokoro", (), {"KPipeline": factory})()
    fake_spacy = type("FakeSpacy", (), {"util": type("Util", (), {"is_package": staticmethod(lambda name: True)})})()

    def _fake_import(name: str):
        if name == "kokoro":
            return fake_kokoro
        if name == "spacy":
            return fake_spacy
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", _fake_import)

    tts_service._load_kokoro_engine()

    assert factory.calls == [{"lang_code": "a", "repo_id": "hexgrad/Kokoro-82M"}]


def test_warm_runtime_loads_both_voices(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class _FakeEngine:
        def load_voice(self, voice: str) -> None:
            calls.append(voice)

    monkeypatch.setattr(tts_service, "_get_cached_kokoro_engine", lambda: _FakeEngine())

    tts_service.TtsService().warm_runtime()

    assert calls == ["af_heart", "am_adam"]
