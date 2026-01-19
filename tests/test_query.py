"""Tests for the query module."""

from unittest.mock import MagicMock, patch

from app.rag.models import Citation, RiskLevel
from app.rag.query import get_llm_client, query


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


# =============================================================================
# UNIT TESTS - query() function
# =============================================================================


def create_mock_node(text: str, score: float, file_name: str = "test.pdf") -> MagicMock:
    """Create a mock NodeWithScore for testing."""
    mock_node = MagicMock()
    mock_node.node.text = text
    mock_node.node.metadata = {"file_name": file_name, "device_name": "TestDevice"}
    mock_node.score = score
    return mock_node


class TestQueryFunction:
    """Tests for the query() function."""

    def test_query_calls_retrieve_with_question(self) -> None:
        """Should call retrieve() with the user's question."""
        get_llm_client.cache_clear()

        with patch("app.rag.query.retrieve") as mock_retrieve, \
             patch("app.rag.query.format_contexts_for_llm") as mock_format, \
             patch("app.rag.query.get_llm_client") as mock_get_client:

            # Setup mocks
            mock_retrieve.return_value = []
            mock_format.return_value = "No relevant documents found."
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                answer="Test answer",
                risk_level="LOW",
                reasoning="Test reasoning",
                citations=[],
            )
            mock_get_client.return_value = mock_client

            query("How do I change my furnace filter?")

            mock_retrieve.assert_called_once_with("How do I change my furnace filter?")

    def test_query_returns_contexts_from_retrieved_nodes(self) -> None:
        """Should populate contexts field with text from retrieved nodes."""
        get_llm_client.cache_clear()

        mock_nodes = [
            create_mock_node("First chunk about filters.", 0.9),
            create_mock_node("Second chunk about maintenance.", 0.8),
        ]

        with patch("app.rag.query.retrieve") as mock_retrieve, \
             patch("app.rag.query.format_contexts_for_llm") as mock_format, \
             patch("app.rag.query.get_llm_client") as mock_get_client:

            mock_retrieve.return_value = mock_nodes
            mock_format.return_value = "[Source 1]...[Source 2]..."
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                answer="Test answer",
                risk_level="LOW",
                reasoning="Test reasoning",
                citations=[],
            )
            mock_get_client.return_value = mock_client

            result = query("test question")

            assert len(result.contexts) == 2
            assert "First chunk about filters." in result.contexts
            assert "Second chunk about maintenance." in result.contexts

    def test_query_includes_context_in_llm_prompt(self) -> None:
        """Should include formatted context in the user message to LLM."""
        get_llm_client.cache_clear()

        with patch("app.rag.query.retrieve") as mock_retrieve, \
             patch("app.rag.query.format_contexts_for_llm") as mock_format, \
             patch("app.rag.query.get_llm_client") as mock_get_client:

            mock_retrieve.return_value = [create_mock_node("Filter info", 0.9)]
            mock_format.return_value = "[Source 1: manual.pdf]\nFilter info"
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                answer="Test answer",
                risk_level="LOW",
                reasoning="Test reasoning",
                citations=[],
            )
            mock_get_client.return_value = mock_client

            query("How do I change my filter?")

            # Check that the LLM was called with context in the message
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            user_message = messages[1]["content"]

            assert "[Source 1: manual.pdf]" in user_message
            assert "Filter info" in user_message
            assert "How do I change my filter?" in user_message

    def test_query_returns_citations_from_llm(self) -> None:
        """Should return citations from LLM response."""
        get_llm_client.cache_clear()

        with patch("app.rag.query.retrieve") as mock_retrieve, \
             patch("app.rag.query.format_contexts_for_llm") as mock_format, \
             patch("app.rag.query.get_llm_client") as mock_get_client:

            mock_retrieve.return_value = []
            mock_format.return_value = "No relevant documents found."
            mock_client = MagicMock()
            mock_citation = Citation(source="furnace-manual.pdf", page=8, quote="Change filter monthly")
            mock_client.chat.completions.create.return_value = MagicMock(
                answer="Change the filter monthly.",
                risk_level="LOW",
                reasoning="Simple task",
                citations=[mock_citation],
            )
            mock_get_client.return_value = mock_client

            result = query("test question")

            assert len(result.citations) == 1
            assert result.citations[0].source == "furnace-manual.pdf"
            assert result.citations[0].page == 8

    def test_query_returns_risk_level(self) -> None:
        """Should return risk level from LLM response."""
        get_llm_client.cache_clear()

        with patch("app.rag.query.retrieve") as mock_retrieve, \
             patch("app.rag.query.format_contexts_for_llm") as mock_format, \
             patch("app.rag.query.get_llm_client") as mock_get_client:

            mock_retrieve.return_value = []
            mock_format.return_value = "No relevant documents found."
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                answer="Call an electrician.",
                risk_level="HIGH",
                reasoning="Electrical work is dangerous",
                citations=[],
            )
            mock_get_client.return_value = mock_client

            result = query("How do I rewire my outlet?")

            assert result.risk_level == RiskLevel.HIGH
