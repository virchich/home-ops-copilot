"""Tests for the centralized LLM client (app.llm.client).

Tests cover:
- Default behavior (observability disabled): uses plain OpenAI client
- Observability enabled with valid keys: uses Langfuse OpenAI client
- Observability enabled with missing keys: falls back to plain client
- Caching behavior (lru_cache)
"""

from unittest.mock import MagicMock, patch

from app.llm.client import get_llm_client


class TestGetLLMClientDisabled:
    """Tests when observability is disabled (default)."""

    def test_uses_plain_openai_when_disabled(self) -> None:
        """Should use plain openai.OpenAI when observability is disabled."""
        get_llm_client.cache_clear()

        with (
            patch("app.llm.client.settings") as mock_settings,
            patch("app.llm.client.instructor") as mock_instructor,
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_settings.observability.enabled = False
            mock_settings.openai_api_key = "sk-test"
            mock_instructor.from_openai.return_value = MagicMock()

            get_llm_client()

            mock_openai.assert_called_once_with(api_key="sk-test")
            mock_instructor.from_openai.assert_called_once()


class TestGetLLMClientEnabled:
    """Tests when observability is enabled."""

    def test_uses_langfuse_openai_when_enabled_with_keys(self) -> None:
        """Should use langfuse.openai.OpenAI when enabled with valid keys."""
        get_llm_client.cache_clear()

        with (
            patch("app.llm.client.settings") as mock_settings,
            patch("app.llm.client.instructor") as mock_instructor,
            patch("langfuse.openai.OpenAI") as mock_langfuse_openai,
        ):
            mock_settings.observability.enabled = True
            mock_settings.observability.langfuse_public_key = "pk-test"
            mock_settings.observability.langfuse_secret_key = "sk-test"
            mock_settings.openai_api_key = "sk-openai"
            mock_instructor.from_openai.return_value = MagicMock()

            get_llm_client()

            mock_langfuse_openai.assert_called_once_with(api_key="sk-openai")
            mock_instructor.from_openai.assert_called_once()

    def test_falls_back_when_keys_missing(self) -> None:
        """Should fall back to plain client when Langfuse keys are empty."""
        get_llm_client.cache_clear()

        with (
            patch("app.llm.client.settings") as mock_settings,
            patch("app.llm.client.instructor") as mock_instructor,
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_settings.observability.enabled = True
            mock_settings.observability.langfuse_public_key = ""
            mock_settings.observability.langfuse_secret_key = ""
            mock_settings.openai_api_key = "sk-openai"
            mock_instructor.from_openai.return_value = MagicMock()

            get_llm_client()

            # Should fall back to plain OpenAI
            mock_openai.assert_called_once_with(api_key="sk-openai")

    def test_falls_back_when_langfuse_import_fails(self) -> None:
        """Should fall back to plain client when langfuse is not installed."""
        get_llm_client.cache_clear()

        with (
            patch("app.llm.client.settings") as mock_settings,
            patch("app.llm.client.instructor") as mock_instructor,
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_settings.observability.enabled = True
            mock_settings.observability.langfuse_public_key = "pk-test"
            mock_settings.observability.langfuse_secret_key = "sk-test"
            mock_settings.openai_api_key = "sk-openai"
            mock_instructor.from_openai.return_value = MagicMock()

            # Simulate langfuse not installed by patching the import target
            import builtins

            original_import = builtins.__import__

            def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
                if name == "langfuse.openai":
                    raise ImportError("No module named 'langfuse'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                get_llm_client()

            # Should fall back to plain OpenAI
            mock_openai.assert_called_once_with(api_key="sk-openai")


class TestGetLLMClientCaching:
    """Tests for lru_cache behavior."""

    def test_caches_result(self) -> None:
        """Should return the same client on subsequent calls."""
        get_llm_client.cache_clear()

        with (
            patch("app.llm.client.settings") as mock_settings,
            patch("app.llm.client.instructor") as mock_instructor,
            patch("openai.OpenAI"),
        ):
            mock_settings.observability.enabled = False
            mock_settings.openai_api_key = "sk-test"
            mock_client = MagicMock()
            mock_instructor.from_openai.return_value = mock_client

            client1 = get_llm_client()
            client2 = get_llm_client()

            assert client1 is client2
            # instructor.from_openai should only be called once
            assert mock_instructor.from_openai.call_count == 1
