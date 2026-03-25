from __future__ import annotations

import pytest

from app.core.config import get_settings, reset_settings_cache, validate_required_runtime_settings


def test_runtime_config_does_not_crash_without_zep_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zep credentials missing should NOT crash — graceful degradation."""
    with monkeypatch.context() as scoped:
        scoped.setenv("ZEP_API_KEY", "")
        scoped.setenv("ZEP_PROJECT_ID", "")
        reset_settings_cache()
        settings = get_settings()
        # Should complete without raising
        validate_required_runtime_settings(settings)
    reset_settings_cache()


def test_runtime_config_does_not_crash_with_invalid_zep_project_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid ZEP_PROJECT_ID should warn, not crash."""
    with monkeypatch.context() as scoped:
        scoped.setenv("ZEP_API_KEY", "valid-key")
        scoped.setenv("ZEP_PROJECT_ID", "not-a-uuid")
        reset_settings_cache()
        settings = get_settings()
        # Should complete without raising
        validate_required_runtime_settings(settings)
    reset_settings_cache()
