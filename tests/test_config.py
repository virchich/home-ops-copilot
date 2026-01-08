"""Tests for application configuration."""

import pytest

from app.core.config import Settings


class TestSettingsDefaults:
    """Tests for default configuration values."""

    def test_default_model(self) -> None:
        """Should have gpt-5.2 as default model."""
        settings = Settings(openai_api_key="test-key")
        assert settings.openai_model == "gpt-5.2"

    def test_default_app_name(self) -> None:
        """Should have correct default app name."""
        settings = Settings(openai_api_key="test-key")
        assert settings.app_name == "Home Ops Copilot"

    def test_default_debug_false(self) -> None:
        """Debug should be False by default."""
        settings = Settings(openai_api_key="test-key")
        assert settings.debug is False

    def test_api_key_has_empty_default(self) -> None:
        """API key should have empty string as default value in schema."""
        # Check the field definition rather than runtime behavior
        # (runtime behavior depends on .env file which we can't control in tests)
        field_info = Settings.model_fields["openai_api_key"]
        assert field_info.default == ""


class TestSettingsFromEnv:
    """Tests for loading settings from environment variables."""

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load API key from environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
        settings = Settings()
        assert settings.openai_api_key == "sk-test-key-123"

    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load model from environment variable."""
        monkeypatch.setenv("OPENAI_MODEL", "gpt-5.2-pro")
        settings = Settings()
        assert settings.openai_model == "gpt-5.2-pro"

    def test_debug_from_env_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should parse debug=true from environment."""
        monkeypatch.setenv("DEBUG", "true")
        settings = Settings()
        assert settings.debug is True

    def test_debug_from_env_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should parse debug=false from environment."""
        monkeypatch.setenv("DEBUG", "false")
        settings = Settings()
        assert settings.debug is False

    def test_debug_from_env_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should parse debug=1 as True."""
        monkeypatch.setenv("DEBUG", "1")
        settings = Settings()
        assert settings.debug is True


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_extra_env_vars_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should ignore extra environment variables (extra='ignore')."""
        monkeypatch.setenv("UNKNOWN_SETTING", "some-value")
        # Should not raise an error
        settings = Settings()
        assert not hasattr(settings, "unknown_setting")

    def test_explicit_values_override_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit constructor values should override environment."""
        monkeypatch.setenv("OPENAI_MODEL", "gpt-5.2-pro")
        settings = Settings(openai_model="gpt-4o")
        assert settings.openai_model == "gpt-4o"
