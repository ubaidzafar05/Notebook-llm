from __future__ import annotations

import pytest

from app.core.config import get_settings, reset_settings_cache, validate_required_runtime_settings


def test_runtime_config_fails_without_zep_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as scoped:
        scoped.setenv("ZEP_API_KEY", "")
        reset_settings_cache()
        settings = get_settings()
        with pytest.raises(RuntimeError, match="ZEP_API_KEY is required"):
            validate_required_runtime_settings(settings)
    reset_settings_cache()


def test_runtime_config_fails_with_invalid_zep_project_id(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as scoped:
        scoped.setenv("ZEP_PROJECT_ID", "not-a-uuid")
        reset_settings_cache()
        settings = get_settings()
        with pytest.raises(RuntimeError, match="ZEP_PROJECT_ID must be a valid UUID"):
            validate_required_runtime_settings(settings)
    reset_settings_cache()
