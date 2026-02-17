"""Tests for the query module.

Unit tests use mocked dependencies to test behavior without external calls.
Focus on:
- Output structure given inputs (behavior, not implementation)
- Error handling paths
- Edge cases
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.rag.models import Citation, QueryResponse, RiskLevel
from app.rag.query import (
    _has_sufficient_evidence,
    _match_citation_to_source,
    enrich_citations,
    query,
)

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
    mock_node.node.get_content.return_value = text
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
def mock_rag_pipeline() -> Generator[dict[str, Any]]:
    """Fixture that mocks the RAG pipeline components."""
    with (
        patch("app.rag.query.retrieve") as mock_retrieve,
        patch("app.rag.query.format_contexts_for_llm") as mock_format,
        patch("app.rag.query.get_llm_client") as mock_get_client,
    ):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        yield {
            "retrieve": mock_retrieve,
            "format": mock_format,
            "client": mock_client,
        }


# =============================================================================
# UNIT TESTS - query() function: Happy Path
# =============================================================================


class TestQueryHappyPath:
    """Tests for query() function normal behavior."""

    def test_returns_query_response_type(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should return a QueryResponse object."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No docs"
        mock_rag_pipeline[
            "client"
        ].chat.completions.create.return_value = create_mock_llm_response()

        result = query("test question")

        assert isinstance(result, QueryResponse)

    def test_returns_answer_from_llm(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should pass through answer from LLM response."""
        # Provide nodes that pass relevance threshold
        nodes = [create_mock_node("Some relevant text", 0.8)]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1]\nSome text"
        mock_rag_pipeline["client"].chat.completions.create.return_value = create_mock_llm_response(
            answer="Change filter every 3 months"
        )

        result = query("How often to change filter?")

        assert result.answer == "Change filter every 3 months"

    def test_returns_risk_level_from_llm(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should convert and return risk level from LLM response."""
        # Provide nodes that pass relevance threshold
        nodes = [create_mock_node("Gas valve info", 0.8)]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1]\nGas valve info"
        mock_rag_pipeline["client"].chat.completions.create.return_value = create_mock_llm_response(
            risk_level="HIGH"
        )

        result = query("How to replace gas valve?")

        assert result.risk_level == RiskLevel.HIGH

    def test_returns_enriched_citations_from_llm(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should return enriched citations that match retrieved sources."""
        # Mock a retrieved node with metadata
        nodes = [create_mock_node("Some text", 0.9, file_name="manual.pdf", device_name="Furnace")]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1: manual.pdf - Furnace]\nSome text"

        # LLM cites the retrieved source
        citation = Citation(source="manual.pdf - Furnace", page=5, quote="Replace annually")
        mock_rag_pipeline["client"].chat.completions.create.return_value = create_mock_llm_response(
            citations=[citation]
        )

        result = query("test")

        assert len(result.citations) == 1
        assert "manual.pdf" in result.citations[0].source
        assert result.citations[0].page == 5

    def test_filters_out_unmatched_citations(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should filter out citations that don't match any retrieved source."""
        # Mock retrieved nodes
        nodes = [create_mock_node("Some text", 0.9, file_name="real-doc.pdf")]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1]\nSome text"

        # LLM cites a non-existent source (hallucination)
        hallucinated_citation = Citation(source="fake-doc.pdf", page=1)
        mock_rag_pipeline["client"].chat.completions.create.return_value = create_mock_llm_response(
            citations=[hallucinated_citation]
        )

        result = query("test")

        # Hallucinated citation should be filtered out
        assert len(result.citations) == 0

    def test_returns_contexts_from_retrieved_nodes(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should populate contexts with text from retrieved nodes."""
        nodes = [
            create_mock_node("Chunk 1 text", 0.9),
            create_mock_node("Chunk 2 text", 0.8),
        ]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "formatted context"
        mock_rag_pipeline[
            "client"
        ].chat.completions.create.return_value = create_mock_llm_response()

        result = query("test")

        assert len(result.contexts) == 2
        assert "Chunk 1 text" in result.contexts
        assert "Chunk 2 text" in result.contexts

    def test_empty_retrieval_returns_empty_contexts(
        self, mock_rag_pipeline: dict[str, Any]
    ) -> None:
        """Should return empty contexts when retrieval finds nothing."""
        mock_rag_pipeline["retrieve"].return_value = []
        mock_rag_pipeline["format"].return_value = "No relevant documents found."
        mock_rag_pipeline[
            "client"
        ].chat.completions.create.return_value = create_mock_llm_response()

        result = query("obscure question")

        assert result.contexts == []


# =============================================================================
# UNIT TESTS - query() function: LLM Prompt Construction
# =============================================================================


class TestQueryPromptConstruction:
    """Tests verifying the LLM receives properly constructed prompts."""

    def test_question_included_in_prompt(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """User's question should be included in the LLM prompt."""
        # Provide nodes that pass relevance threshold
        nodes = [create_mock_node("HRV cleaning info", 0.8)]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1]\nHRV info"
        mock_rag_pipeline[
            "client"
        ].chat.completions.create.return_value = create_mock_llm_response()

        query("How do I clean my HRV?")

        call_args = mock_rag_pipeline["client"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[1]["content"]

        assert "How do I clean my HRV?" in user_content

    def test_formatted_context_included_in_prompt(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Formatted retrieval context should be included in the LLM prompt."""
        mock_rag_pipeline["retrieve"].return_value = [create_mock_node("text", 0.9)]
        mock_rag_pipeline["format"].return_value = "[Source 1: manual.pdf]\nClean filters monthly"
        mock_rag_pipeline[
            "client"
        ].chat.completions.create.return_value = create_mock_llm_response()

        query("test")

        call_args = mock_rag_pipeline["client"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_content = messages[1]["content"]

        assert "[Source 1: manual.pdf]" in user_content
        assert "Clean filters monthly" in user_content

    def test_system_prompt_is_first_message(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """System prompt should be the first message to LLM."""
        # Provide nodes that pass relevance threshold
        nodes = [create_mock_node("Some text", 0.8)]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1]\nSome text"
        mock_rag_pipeline[
            "client"
        ].chat.completions.create.return_value = create_mock_llm_response()

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

    def test_retriever_exception_propagates(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Retriever exceptions should propagate to caller."""
        mock_rag_pipeline["retrieve"].side_effect = FileNotFoundError("Index not found at ./index")

        with pytest.raises(FileNotFoundError, match="Index not found"):
            query("test")

    def test_llm_api_exception_propagates(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """LLM API exceptions should propagate to caller."""
        # Provide nodes that pass relevance threshold so LLM is called
        nodes = [create_mock_node("Some text", 0.8)]
        mock_rag_pipeline["retrieve"].return_value = nodes
        mock_rag_pipeline["format"].return_value = "[Source 1]\nSome text"
        mock_rag_pipeline["client"].chat.completions.create.side_effect = Exception(
            "API rate limit exceeded"
        )

        with pytest.raises(Exception, match="rate limit"):
            query("test")


# =============================================================================
# UNIT TESTS - Insufficient Evidence Fallback
# =============================================================================


class TestHasSufficientEvidence:
    """Tests for _has_sufficient_evidence function."""

    def test_returns_false_for_empty_nodes(self) -> None:
        """Should return False when no nodes retrieved."""
        assert _has_sufficient_evidence([]) is False

    def test_returns_false_for_low_score_bi_encoder(self) -> None:
        """Should return False when top score is below threshold (bi-encoder)."""
        nodes = [create_mock_node("text", 0.1)]  # Very low score

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = False
            mock_settings.rag.min_relevance_score = 0.3
            assert _has_sufficient_evidence(nodes) is False

    def test_returns_true_for_high_score_bi_encoder(self) -> None:
        """Should return True when top score meets threshold (bi-encoder)."""
        nodes = [create_mock_node("text", 0.8)]  # High score

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = False
            mock_settings.rag.min_relevance_score = 0.3
            assert _has_sufficient_evidence(nodes) is True

    def test_returns_true_for_exact_threshold_bi_encoder(self) -> None:
        """Should return True when top score equals threshold (bi-encoder)."""
        nodes = [create_mock_node("text", 0.5)]

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = False
            mock_settings.rag.min_relevance_score = 0.5
            assert _has_sufficient_evidence(nodes) is True

    def test_uses_first_node_score_bi_encoder(self) -> None:
        """Should check the first (highest) node's score (bi-encoder)."""
        nodes = [
            create_mock_node("best match", 0.9),
            create_mock_node("second best", 0.5),
            create_mock_node("third", 0.2),
        ]

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = False
            mock_settings.rag.min_relevance_score = 0.7
            # Should pass because first node (0.9) exceeds threshold
            assert _has_sufficient_evidence(nodes) is True

    def test_returns_false_for_negative_score_cross_encoder(self) -> None:
        """Should return False when top score is negative (cross-encoder logits)."""
        nodes = [create_mock_node("text", -2.5)]  # Negative = not relevant

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = True
            assert _has_sufficient_evidence(nodes) is False

    def test_returns_true_for_positive_score_cross_encoder(self) -> None:
        """Should return True when top score is positive (cross-encoder logits)."""
        nodes = [create_mock_node("text", 3.5)]  # Positive = relevant

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = True
            assert _has_sufficient_evidence(nodes) is True


class TestQueryInsufficientEvidence:
    """Tests for query() insufficient evidence fallback."""

    def test_returns_fallback_for_empty_retrieval(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should return fallback response when no nodes retrieved."""
        mock_rag_pipeline["retrieve"].return_value = []

        result = query("What is the meaning of life?")

        assert "don't have enough information" in result.answer
        assert result.citations == []
        assert result.risk_level == RiskLevel.LOW
        assert result.contexts == []

    def test_returns_fallback_for_low_relevance(self, mock_rag_pipeline: dict[str, Any]) -> None:
        """Should return fallback when top score is below threshold (bi-encoder)."""
        # Mock low-scoring nodes
        low_score_nodes = [create_mock_node("irrelevant text", 0.1)]
        mock_rag_pipeline["retrieve"].return_value = low_score_nodes

        with patch("app.rag.query.settings") as mock_settings:
            mock_settings.rag.rerank_enabled = False
            mock_settings.rag.min_relevance_score = 0.3

            result = query("Random unrelated question")

            assert "don't have enough information" in result.answer
            assert result.citations == []
            assert result.contexts == []

    def test_does_not_call_llm_for_insufficient_evidence(
        self, mock_rag_pipeline: dict[str, Any]
    ) -> None:
        """Should skip LLM call when evidence is insufficient."""
        mock_rag_pipeline["retrieve"].return_value = []

        query("Unknown topic question")

        # LLM should not be called
        mock_rag_pipeline["client"].chat.completions.create.assert_not_called()


# =============================================================================
# UNIT TESTS - Citation Enrichment Functions
# =============================================================================


class TestCitationMatching:
    """Tests for _match_citation_to_source function."""

    def test_matches_by_source_index(self) -> None:
        """Should match 'Source N' pattern to source mapping."""
        source_mapping = {
            1: {"file_name": "manual.pdf", "device_name": "Furnace"},
            2: {"file_name": "guide.pdf", "device_name": "HRV"},
        }
        citation = Citation(source="Source 1")

        result = _match_citation_to_source(citation, source_mapping)

        assert result is not None
        assert result["file_name"] == "manual.pdf"

    def test_matches_by_bracketed_source_index(self) -> None:
        """Should match '[Source N]' pattern."""
        source_mapping = {1: {"file_name": "manual.pdf", "device_name": "Furnace"}}
        citation = Citation(source="[Source 1]")

        result = _match_citation_to_source(citation, source_mapping)

        assert result is not None
        assert result["file_name"] == "manual.pdf"

    def test_matches_by_file_name(self) -> None:
        """Should match by file name substring."""
        source_mapping = {1: {"file_name": "furnace-manual.pdf", "device_name": "Furnace"}}
        citation = Citation(source="furnace-manual.pdf - Furnace")

        result = _match_citation_to_source(citation, source_mapping)

        assert result is not None
        assert result["file_name"] == "furnace-manual.pdf"

    def test_matches_partial_file_name(self) -> None:
        """Should match when file name is contained in citation source."""
        source_mapping = {1: {"file_name": "manual.pdf", "device_name": ""}}
        citation = Citation(source="From manual.pdf page 5")

        result = _match_citation_to_source(citation, source_mapping)

        assert result is not None
        assert result["file_name"] == "manual.pdf"

    def test_returns_none_for_no_match(self) -> None:
        """Should return None when citation doesn't match any source."""
        source_mapping = {1: {"file_name": "real-doc.pdf", "device_name": "Device"}}
        citation = Citation(source="fake-doc.pdf")

        result = _match_citation_to_source(citation, source_mapping)

        assert result is None

    def test_returns_none_for_invalid_source_index(self) -> None:
        """Should return None for source index that doesn't exist."""
        source_mapping = {1: {"file_name": "manual.pdf", "device_name": "Furnace"}}
        citation = Citation(source="Source 99")

        result = _match_citation_to_source(citation, source_mapping)

        assert result is None


class TestEnrichCitations:
    """Tests for enrich_citations function."""

    def test_enriches_valid_citations(self) -> None:
        """Should enrich citations with source metadata."""
        source_mapping = {
            1: {"file_name": "manual.pdf", "device_name": "Furnace"},
        }
        citations = [Citation(source="Source 1", page=5, quote="test quote")]

        result = enrich_citations(citations, source_mapping)

        assert len(result) == 1
        assert result[0].source == "manual.pdf - Furnace"
        assert result[0].page == 5
        assert result[0].quote == "test quote"

    def test_filters_unmatched_citations(self) -> None:
        """Should filter out citations that don't match any source."""
        source_mapping = {1: {"file_name": "real.pdf", "device_name": "Device"}}
        citations = [
            Citation(source="real.pdf"),  # Valid
            Citation(source="fake.pdf"),  # Invalid - should be filtered
        ]

        result = enrich_citations(citations, source_mapping)

        assert len(result) == 1
        assert "real.pdf" in result[0].source

    def test_returns_empty_for_empty_mapping(self) -> None:
        """Should return empty list when source mapping is empty."""
        citations = [Citation(source="any.pdf")]

        result = enrich_citations(citations, {})

        assert result == []

    def test_returns_empty_for_empty_citations(self) -> None:
        """Should return empty list when no citations provided."""
        source_mapping = {1: {"file_name": "manual.pdf", "device_name": "Device"}}

        result = enrich_citations([], source_mapping)

        assert result == []

    def test_preserves_llm_provided_fields(self) -> None:
        """Should preserve page, section, and quote from LLM."""
        source_mapping = {1: {"file_name": "manual.pdf", "device_name": "Device"}}
        citations = [
            Citation(
                source="Source 1",
                page=10,
                section="Maintenance",
                quote="Check filter monthly",
            )
        ]

        result = enrich_citations(citations, source_mapping)

        assert len(result) == 1
        assert result[0].page == 10
        assert result[0].section == "Maintenance"
        assert result[0].quote == "Check filter monthly"

    def test_handles_source_without_device_name(self) -> None:
        """Should handle sources without device name gracefully."""
        source_mapping = {1: {"file_name": "notes.pdf", "device_name": ""}}
        citations = [Citation(source="notes.pdf")]

        result = enrich_citations(citations, source_mapping)

        assert len(result) == 1
        assert result[0].source == "notes.pdf"  # No " - " suffix
