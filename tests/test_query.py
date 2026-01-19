"""Tests for the query module.

Unit tests use mocked dependencies to test behavior without external calls.
Focus on:
- Output structure given inputs (behavior, not implementation)
- Error handling paths
- Edge cases
"""

from unittest.mock import MagicMock, patch

import pytest

from app.rag.models import Citation, QueryResponse, RiskLevel
from app.rag.query import get_llm_client, query


# =============================================================================
# TEST FIXTURES
# =============================================================================


def create_mock_node(
    text: str,
    score: float,
    file_name: str = "test.pdf",
    device_name: str = "TestDevice",
) -> MagicMock:
    """Create a mock NodeWithScore for testing."""
    mock_node = MagicMock()
    mock_node.node.text = text
    mock_node.node.metadata = {"file_name": file_name, "device_name": device_name}
    mock_node.score = score
    return mock_node


def create_mock_llm_response(
    answer: str = "Test answer",
    risk_level: str = "LOW",
    citations: list[Citation] | None = None,
) -> MagicMock:
    """Create a mock LLM response."""
    return MagicMock(
        answer=answer,
        risk_level=risk_level,
        reasoning="Test reasoning",
        citations=citations or [],
    )


@pytest.fixture
def mock_rag_pipeline():
    """Fixture that mocks the RAG pipeline components."""
    get_llm_client.cache_clear()

    with patch("app.rag.query.retrieve") as mock_retrieve, \
         patch("app.rag.query.format_contexts_for_llm") as mock_format, \
         patch("app.rag.query.get_llm_client") as mock_get_client:

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        yield {
            "retrieve": mock_retrieve,
            "format": mock_format,
            "client": mock_client,
        }


# =============================================================================
# UNIT TESTS - LLM Client Singleton
# =============================================================================


class TestLLMClientSingleton:
    """Tests for LLM client singleton behavior."""

    def test_get_llm_client_returns_client(self) -> None:
        """Should return an instructor client."""
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

            assert client1 is client2
            assert mock_openai.call_count == 1
            assert mock_instructor.call_count == 1


# =============================================================================
# UNIT TESTS - query() function: Happy Path
# =============================================================================


class TestQueryHappyPath:
    """Tests for query() function normal behavior."""

    def test_returns_query_response_type(self, mock_rag_pipeline) -> None:
        """Should return a QueryResponse object."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response()
        )

        result = query("test question")

        assert isinstance(result, QueryResponse)

    def test_returns_answer_from_llm(self, mock_rag_pipeline) -> None:
        """Should pass through answer from LLM response."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response(answer="Change filter every 3 months")
        )

        result = query("How often to change filter?")

        assert result.answer == "Change filter every 3 months"

    def test_returns_risk_level_from_llm(self, mock_rag_pipeline) -> None:
        """Should convert and return risk level from LLM response."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response(risk_level="HIGH")
        )

        result = query("How to replace gas valve?")

        assert result.risk_level == RiskLevel.HIGH

    def test_returns_citations_from_llm(self, mock_rag_pipeline) -> None:
        """Should pass through citations from LLM response."""
        citation = Citation(source="manual.pdf", page=5, quote="Replace annually")
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response(citations=[citation])
        )

        result = query("test")

        assert len(result.citations) == 1
        assert result.citations[0].source == "manual.pdf"
        assert result.citations[0].page == 5

    def test_returns_contexts_from_retrieved_nodes(self, mock_rag_pipeline) -> None:
        """Should populate contexts with text from retrieved nodes."""
        nodes = [
            create_mock_node("Chunk 1 text", 0.9),
            create_mock_node("Chunk 2 text", 0.8),
        ]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "formatted context"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response()
        )

        result = query("test")

        assert len(result.contexts) == 2
        assert "Chunk 1 text" in result.contexts
        assert "Chunk 2 text" in result.contexts

    def test_empty_retrieval_returns_empty_contexts(self, mock_rag_pipeline) -> None:
        """Should return empty contexts when retrieval finds nothing."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No relevant documents found."
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response()
        )

        result = query("obscure question")

        assert result.contexts == []


# =============================================================================
# UNIT TESTS - query() function: LLM Prompt Construction
# =============================================================================


class TestQueryPromptConstruction:
    """Tests verifying the LLM receives properly constructed prompts."""

    def test_question_included_in_prompt(self, mock_rag_pipeline) -> None:
        """User's question should be included in the LLM prompt."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response()
        )

        query("How do I clean my HRV?")

        call_args = mock_rag_pipeline["client"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[1]["content"]

        assert "How do I clean my HRV?" in user_content

    def test_formatted_context_included_in_prompt(self, mock_rag_pipeline) -> None:
        """Formatted retrieval context should be included in the LLM prompt."""
        mock_rag_pipeline["retrieve"].return_value = [create_mock_node("text", 0.9)]
        mock_rag_pipeline["format"].return_value = "[Source 1: manual.pdf]\nClean filters monthly"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response()
        )

        query("test")

        call_args = mock_rag_pipeline["client"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[1]["content"]

        assert "[Source 1: manual.pdf]" in user_content
        assert "Clean filters monthly" in user_content

    def test_system_prompt_is_first_message(self, mock_rag_pipeline) -> None:
        """System prompt should be the first message to LLM."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.return_value = (
            create_mock_llm_response()
        )

        query("test")

        call_args = mock_rag_pipeline["client"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0


# =============================================================================
# UNIT TESTS - query() function: Error Handling
# =============================================================================


class TestQueryErrorHandling:
    """Tests for query() error handling behavior."""

    def test_retriever_exception_propagates(self, mock_rag_pipeline) -> None:
        """Retriever exceptions should propagate to caller."""
        mock_rag_pipeline["retrieve"].side_effect = FileNotFoundError(
            "Index not found at ./index"
        )

        with pytest.raises(FileNotFoundError, match="Index not found"):
            query("test")

    def test_llm_api_exception_propagates(self, mock_rag_pipeline) -> None:
        """LLM API exceptions should propagate to caller."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline["client"].chat.completions.create.side_effect = (
            Exception("API rate limit exceeded")
        )

        with pytest.raises(Exception, match="rate limit"):
            query("test")
