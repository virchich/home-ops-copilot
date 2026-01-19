"""Tests for the query module."""

from unittest.mock import MagicMock, patch

from app.rag.query import get_llm_client


class TestLLMClientSingleton:
    """Tests for LLM client singleton behavior."""

    def test_get_llm_client_returns_client(self) -> None:
        """Should return an instructor client."""
        # Clear cache to ensure fresh state
        get_llm_client.cache_clear()

        with patch("app.rag.query.OpenAI") as mock_openai, \
             patch("app.rag.query.instructor.from_openai") as mock_instructor:
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client

            client = get_llm_client()

            assert client == mock_client
            mock_openai.assert_called_once()
            mock_instructor.assert_called_once()

    def test_get_llm_client_caches_result(self) -> None:
        """Should return the same cached client on subsequent calls."""
        get_llm_client.cache_clear()

        with patch("app.rag.query.OpenAI") as mock_openai, \
             patch("app.rag.query.instructor.from_openai") as mock_instructor:
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client

            client1 = get_llm_client()
            client2 = get_llm_client()

            # Should be the same object
            assert client1 is client2

            # Should only have created client once
            assert mock_openai.call_count == 1
            assert mock_instructor.call_count == 1

    def test_get_llm_client_uses_settings_api_key(self) -> None:
        """Should use API key from settings."""
        get_llm_client.cache_clear()

        with patch("app.rag.query.OpenAI") as mock_openai, \
             patch("app.rag.query.instructor.from_openai"), \
             patch("app.rag.query.settings") as mock_settings:
            mock_settings.openai_api_key = "test-api-key"

            get_llm_client()

            mock_openai.assert_called_once_with(api_key="test-api-key")
