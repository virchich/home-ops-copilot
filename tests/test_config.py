"""Tests for application configuration.

Tests the nested settings structure:
- settings.paths: PathSettings (data directories)
- settings.rag: RAGSettings (chunking, retrieval, embedding)
- settings.llm: LLMSettings (model, temperature, tokens)

Environment variables use __ delimiter for nested settings:
- LLM__MODEL=gpt-4o
- RAG__TOP_K=10
"""

from pathlib import Path

import pytest

from app.core.config import LLMSettings, RAGSettings, Settings


class TestSettingsDefaults:
    """Tests for default configuration values."""

    def test_default_model(self) -> None:
        """Should have gpt-5.2 as default model (nested in llm)."""
        settings = Settings(openai_api_key="test-key")
        assert settings.llm.model == "gpt-5.2"

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

    def test_default_rag_settings(self) -> None:
        """Should have sensible RAG defaults."""
        settings = Settings(openai_api_key="test-key")
        assert settings.rag.chunk_size == 512
        assert settings.rag.chunk_overlap == 50
        assert settings.rag.top_k == 5
        assert settings.rag.embedding_model == "text-embedding-3-small"

    def test_default_path_settings(self) -> None:
        """Should have correct default paths."""
        settings = Settings(openai_api_key="test-key")
        assert settings.paths.raw_docs_dir == Path("data/raw_docs")
        assert settings.paths.metadata_file == Path("data/metadata.json")
        assert settings.paths.index_dir == Path("data/indexes")

    def test_default_llm_settings(self) -> None:
        """Should have sensible LLM defaults."""
        settings = Settings(openai_api_key="test-key")
        assert settings.llm.model == "gpt-5.2"
        assert settings.llm.temperature == 0.3
        assert settings.llm.max_completion_tokens == 1000


class TestSettingsFromEnv:
    """Tests for loading settings from environment variables."""

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load API key from environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
        settings = Settings()
        assert settings.openai_api_key == "sk-test-key-123"

    def test_nested_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load nested LLM model from environment variable using __ delimiter."""
        monkeypatch.setenv("LLM__MODEL", "gpt-5.2-pro")
        settings = Settings()
        assert settings.llm.model == "gpt-5.2-pro"

    def test_nested_rag_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load nested RAG settings from environment variables."""
        monkeypatch.setenv("RAG__TOP_K", "10")
        monkeypatch.setenv("RAG__CHUNK_SIZE", "256")
        settings = Settings()
        assert settings.rag.top_k == 10
        assert settings.rag.chunk_size == 256

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

    def test_explicit_nested_values_override(self) -> None:
        """Explicit constructor values should work for nested settings."""
        custom_llm = LLMSettings(model="gpt-4o", temperature=0.7)
        settings = Settings(llm=custom_llm)
        assert settings.llm.model == "gpt-4o"
        assert settings.llm.temperature == 0.7

    def test_rag_validation_bounds(self) -> None:
        """RAG settings should validate bounds."""
        # Valid settings should work
        rag = RAGSettings(chunk_size=200, top_k=15)
        assert rag.chunk_size == 200
        assert rag.top_k == 15

        # Invalid settings should raise
        with pytest.raises(ValueError):
            RAGSettings(chunk_size=50)  # Below minimum of 100

        with pytest.raises(ValueError):
            RAGSettings(top_k=25)  # Above maximum of 20

    def test_llm_validation_bounds(self) -> None:
        """LLM settings should validate bounds."""
        # Valid settings should work
        llm = LLMSettings(temperature=1.5)
        assert llm.temperature == 1.5

        # Invalid settings should raise
        with pytest.raises(ValueError):
            LLMSettings(temperature=3.0)  # Above maximum of 2.0
