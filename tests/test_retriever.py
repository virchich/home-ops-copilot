"""Tests for the retriever module.

Unit tests use mocked nodes and don't require the vector index.
Integration tests require the index to be built (run `make ingest` first).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.rag.retriever import (
    _get_top_score,
    _should_fallback_to_unfiltered,
    build_metadata_filters,
    build_source_mapping,
    detect_device_types,
    format_contexts_for_llm,
    get_index,
    get_node_metadata,
    retrieve,
)

# =============================================================================
# TEST FIXTURES - Mock nodes for unit tests
# =============================================================================


def create_mock_node(
    text: str,
    score: float,
    file_name: str = "test.pdf",
    device_type: str = "furnace",
    device_name: str = "TestDevice",
    manufacturer: str = "TestMfg",
) -> MagicMock:
    """Create a mock NodeWithScore for testing."""
    mock_node = MagicMock()
    mock_node.node.get_content.return_value = text
    mock_node.node.metadata = {
        "file_name": file_name,
        "device_type": device_type,
        "device_name": device_name,
        "manufacturer": manufacturer,
    }
    mock_node.score = score
    return mock_node


# =============================================================================
# UNIT TESTS - format_contexts_for_llm
# =============================================================================


class TestFormatContextsForLLM:
    """Tests for format_contexts_for_llm helper function."""

    def test_empty_list_returns_no_docs_message(self) -> None:
        """Should return informative message for empty results."""
        result = format_contexts_for_llm([])
        assert result == "No relevant documents found."

    def test_single_node_formatting(self) -> None:
        """Should format a single node with source label."""
        node = create_mock_node(
            text="Filter should be changed every 3 months.",
            score=0.85,
            file_name="furnace-manual.pdf",
            device_name="OM9GFRC",
        )

        result = format_contexts_for_llm([node])

        assert "[Source 1: furnace-manual.pdf - OM9GFRC]" in result
        assert "Filter should be changed every 3 months." in result

    def test_multiple_nodes_formatting(self) -> None:
        """Should format multiple nodes with numbered sources."""
        nodes = [
            create_mock_node(
                text="First chunk text.",
                score=0.9,
                file_name="doc1.pdf",
                device_name="Device1",
            ),
            create_mock_node(
                text="Second chunk text.",
                score=0.8,
                file_name="doc2.pdf",
                device_name="Device2",
            ),
        ]

        result = format_contexts_for_llm(nodes)

        assert "[Source 1: doc1.pdf - Device1]" in result
        assert "[Source 2: doc2.pdf - Device2]" in result
        assert "First chunk text." in result
        assert "Second chunk text." in result
        # Should have separator between sources
        assert "---" in result

    def test_handles_missing_metadata_gracefully(self) -> None:
        """Should use 'Unknown' for missing metadata fields."""
        mock_node = MagicMock()
        mock_node.node.get_content.return_value = "Some text"
        mock_node.node.metadata = {}  # Empty metadata
        mock_node.score = 0.5

        result = format_contexts_for_llm([mock_node])

        assert "[Source 1: Unknown - Unknown device]" in result


# =============================================================================
# UNIT TESTS - get_node_metadata
# =============================================================================


class TestGetNodeMetadata:
    """Tests for get_node_metadata helper function."""

    def test_extracts_all_fields(self) -> None:
        """Should extract all metadata fields from node."""
        node = create_mock_node(
            text="Some text",
            score=0.87,
            file_name="test-manual.pdf",
            device_type="hrv",
            device_name="RNC5-HEX",
            manufacturer="Venmar",
        )

        result = get_node_metadata(node)

        assert result["file_name"] == "test-manual.pdf"
        assert result["device_type"] == "hrv"
        assert result["device_name"] == "RNC5-HEX"
        assert result["manufacturer"] == "Venmar"
        assert result["score"] == 0.87

    def test_handles_missing_fields(self) -> None:
        """Should return empty strings for missing metadata fields."""
        mock_node = MagicMock()
        mock_node.node.metadata = {"file_name": "only-filename.pdf"}
        mock_node.score = 0.5

        result = get_node_metadata(mock_node)

        assert result["file_name"] == "only-filename.pdf"
        assert result["device_type"] == ""
        assert result["device_name"] == ""
        assert result["manufacturer"] == ""


# =============================================================================
# UNIT TESTS - build_source_mapping
# =============================================================================


class TestBuildSourceMapping:
    """Tests for build_source_mapping function."""

    def test_builds_mapping_with_correct_indices(self) -> None:
        """Should create 1-based index mapping."""
        nodes = [
            create_mock_node("Text 1", 0.9, "doc1.pdf", "Furnace"),
            create_mock_node("Text 2", 0.8, "doc2.pdf", "HRV"),
        ]

        result = build_source_mapping(nodes)

        assert 1 in result
        assert 2 in result
        assert 0 not in result  # 1-based indexing

    def test_maps_metadata_correctly(self) -> None:
        """Should map node metadata to indices."""
        nodes = [
            create_mock_node(
                "Text",
                0.9,
                file_name="manual.pdf",
                device_type="furnace",
                device_name="OM9GFRC",
                manufacturer="Carrier",
            ),
        ]

        result = build_source_mapping(nodes)

        assert result[1]["file_name"] == "manual.pdf"
        assert result[1]["device_name"] == "OM9GFRC"
        assert result[1]["score"] == 0.9

    def test_empty_nodes_returns_empty_mapping(self) -> None:
        """Should return empty dict for empty nodes list."""
        result = build_source_mapping([])

        assert result == {}

    def test_preserves_node_order(self) -> None:
        """Source indices should correspond to node order."""
        nodes = [
            create_mock_node("First", 0.9, "first.pdf"),
            create_mock_node("Second", 0.8, "second.pdf"),
            create_mock_node("Third", 0.7, "third.pdf"),
        ]

        result = build_source_mapping(nodes)

        assert result[1]["file_name"] == "first.pdf"
        assert result[2]["file_name"] == "second.pdf"
        assert result[3]["file_name"] == "third.pdf"


# =============================================================================
# UNIT TESTS - retrieve() default behavior
# =============================================================================


class TestRetrieveDefaults:
    """Tests for retrieve() parameter handling."""

    def test_uses_settings_top_k_when_none(self) -> None:
        """Should use settings.rag.top_k when top_k is None."""
        with (
            patch("app.rag.retriever.get_index") as mock_get_index,
            patch("app.rag.retriever.VectorIndexRetriever") as mock_retriever_class,
            patch("app.rag.retriever.rerank_nodes") as mock_rerank,
            patch("app.rag.retriever.settings") as mock_settings,
        ):
            # Setup mocks
            mock_settings.rag.top_k = 7
            mock_settings.rag.rerank_enabled = False  # Disable reranking for this test
            mock_index = MagicMock()
            mock_get_index.return_value = mock_index
            mock_retriever = MagicMock()
            mock_retriever.retrieve.return_value = []
            mock_retriever_class.return_value = mock_retriever
            mock_rerank.return_value = []  # Pass through

            # Call without top_k
            retrieve("test question")

            # Verify retriever was created with settings value
            # filters=None because "test question" doesn't match any device keywords
            # When rerank is disabled, similarity_top_k equals top_k (no over-fetch)
            mock_retriever_class.assert_called_once_with(
                index=mock_index,
                similarity_top_k=7,
                filters=None,
            )

    def test_uses_explicit_top_k_when_provided(self) -> None:
        """Should use explicit top_k when provided."""
        with (
            patch("app.rag.retriever.get_index") as mock_get_index,
            patch("app.rag.retriever.VectorIndexRetriever") as mock_retriever_class,
            patch("app.rag.retriever.rerank_nodes") as mock_rerank,
            patch("app.rag.retriever.settings") as mock_settings,
        ):
            # Setup mocks
            mock_settings.rag.top_k = 5  # Default
            mock_settings.rag.rerank_enabled = False  # Disable reranking for this test
            mock_index = MagicMock()
            mock_get_index.return_value = mock_index
            mock_retriever = MagicMock()
            mock_retriever.retrieve.return_value = []
            mock_retriever_class.return_value = mock_retriever
            mock_rerank.return_value = []  # Pass through

            # Call with explicit top_k
            retrieve("test question", top_k=10)

            # Verify retriever was created with explicit value
            # filters=None because "test question" doesn't match any device keywords
            # When rerank is disabled, similarity_top_k equals top_k (no over-fetch)
            mock_retriever_class.assert_called_once_with(
                index=mock_index,
                similarity_top_k=10,
                filters=None,
            )


# =============================================================================
# DEVICE TYPE DETECTION TESTS
# =============================================================================


class TestDetectDeviceTypes:
    """Tests for detect_device_types() function."""

    def test_detects_furnace_keywords(self) -> None:
        """Should detect furnace from various keywords."""
        assert "furnace" in detect_device_types("How do I change my furnace filter?")
        assert "furnace" in detect_device_types("What MERV rating should I use?")
        assert "furnace" in detect_device_types("My heating system isn't working")

    def test_detects_hrv_keywords(self) -> None:
        """Should detect HRV from various keywords."""
        assert "hrv" in detect_device_types("How do I use my HRV?")
        assert "hrv" in detect_device_types("Ventilation settings in winter")
        assert "hrv" in detect_device_types("Heat recovery ventilator maintenance")

    def test_detects_humidifier_keywords(self) -> None:
        """Should detect humidifier from various keywords."""
        assert "humidifier" in detect_device_types("What humidity level should I set?")
        assert "humidifier" in detect_device_types("My humidifier is not working")
        assert "humidifier" in detect_device_types("Dry air in winter")

    def test_detects_water_heater_keywords(self) -> None:
        """Should detect water heater from various keywords."""
        assert "water_heater" in detect_device_types("Hot water tank temperature")
        assert "water_heater" in detect_device_types("My water heater is making noise")

    def test_detects_water_softener_keywords(self) -> None:
        """Should detect water softener from various keywords."""
        assert "water_softener" in detect_device_types("How much salt for softener?")
        assert "water_softener" in detect_device_types("Hard water problems")

    def test_detects_multiple_devices(self) -> None:
        """Should detect multiple device types when question is ambiguous."""
        # Humidity relates to both humidifier and HRV
        result = detect_device_types("What humidity level for HRV?")
        assert "hrv" in result
        assert "humidifier" in result

    def test_returns_empty_for_generic_question(self) -> None:
        """Should return empty list when no device keywords match."""
        assert detect_device_types("How do I save money?") == []
        assert detect_device_types("General home maintenance tips") == []

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        assert "furnace" in detect_device_types("FURNACE filter")
        assert "hrv" in detect_device_types("HRV settings")


class TestBuildMetadataFilters:
    """Tests for build_metadata_filters() function."""

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when no device types provided."""
        assert build_metadata_filters([]) is None

    def test_creates_single_filter(self) -> None:
        """Should create a filter for a single device type."""
        from llama_index.core.vector_stores import MetadataFilter

        filters = build_metadata_filters(["furnace"])

        assert filters is not None
        assert len(filters.filters) == 1
        # Type narrowing for mypy
        first_filter = filters.filters[0]
        assert isinstance(first_filter, MetadataFilter)
        assert first_filter.key == "device_type"
        assert first_filter.value == "furnace"

    def test_creates_or_filter_for_multiple_devices(self) -> None:
        """Should create OR filter for multiple device types."""
        from llama_index.core.vector_stores import FilterCondition

        filters = build_metadata_filters(["furnace", "humidifier"])

        assert filters is not None
        assert len(filters.filters) == 2
        assert filters.condition == FilterCondition.OR


# =============================================================================
# HYBRID FALLBACK TESTS
# =============================================================================


class TestGetTopScore:
    """Tests for _get_top_score() helper function."""

    def test_returns_zero_for_empty_list(self) -> None:
        """Should return 0.0 for empty results."""
        assert _get_top_score([]) == 0.0

    def test_returns_first_score(self) -> None:
        """Should return the score of the first result."""
        node = create_mock_node("test", score=0.85)
        assert _get_top_score([node]) == 0.85

    def test_handles_none_score(self) -> None:
        """Should return 0.0 if score is None."""
        node = create_mock_node("test", score=0.0)
        node.score = None
        assert _get_top_score([node]) == 0.0


class TestShouldFallbackToUnfiltered:
    """Tests for _should_fallback_to_unfiltered() helper function."""

    def test_returns_true_for_empty_results(self) -> None:
        """Should fall back when no results."""
        assert _should_fallback_to_unfiltered([]) is True

    def test_returns_true_for_low_score(self) -> None:
        """Should fall back when top score is below threshold."""
        # min_relevance_score default is 0.3
        node = create_mock_node("test", score=0.2)
        with patch("app.rag.retriever.settings") as mock_settings:
            mock_settings.rag.min_relevance_score = 0.3
            assert _should_fallback_to_unfiltered([node]) is True

    def test_returns_false_for_good_score(self) -> None:
        """Should not fall back when top score is above threshold."""
        node = create_mock_node("test", score=0.5)
        with patch("app.rag.retriever.settings") as mock_settings:
            mock_settings.rag.min_relevance_score = 0.3
            assert _should_fallback_to_unfiltered([node]) is False


# =============================================================================
# INTEGRATION TESTS - Require actual index
# =============================================================================
# These tests require the vector index to be built.
# Run `make ingest` before running these tests.
# Skip with: pytest -m "not integration"


@pytest.mark.integration
class TestRetrieverIntegration:
    """Integration tests that require the actual vector index."""

    def test_get_index_loads_successfully(self) -> None:
        """Should load the vector index from disk."""
        # Clear cache to ensure fresh load
        get_index.cache_clear()

        index = get_index()

        assert index is not None
        # Index should have documents
        assert len(index.docstore.docs) > 0

    def test_get_index_caching_returns_same_instance(self) -> None:
        """Should return the same cached index instance."""
        get_index.cache_clear()

        index1 = get_index()
        index2 = get_index()

        # Should be the exact same object (cached)
        assert index1 is index2

    def test_retrieve_returns_results(self) -> None:
        """Should return results for a valid question."""
        get_index.cache_clear()

        results = retrieve("How do I change the furnace filter?")

        assert len(results) > 0
        # Each result should have expected attributes
        for result in results:
            assert hasattr(result, "score")
            assert hasattr(result, "node")
            assert hasattr(result.node, "text")
            assert hasattr(result.node, "metadata")

    def test_retrieve_respects_top_k(self) -> None:
        """Should return at most the configured number of results.

        Note: When reranking is enabled, returns rerank_top_n results.
        When disabled, returns exactly top_k results.
        """
        from app.core.config import settings

        get_index.cache_clear()

        results = retrieve("furnace maintenance", top_k=3)

        # When reranking is enabled, we return rerank_top_n (default: 5)
        # When disabled, we return top_k (3)
        if settings.rag.rerank_enabled:
            assert len(results) == settings.rag.rerank_top_n
        else:
            assert len(results) == 3

    def test_retrieve_results_have_scores(self) -> None:
        """Results should have valid relevance scores.

        Note: Score range depends on whether reranking is enabled:
        - Bi-encoder: scores are 0-1 (cosine similarity)
        - Cross-encoder: scores are logits (typically -10 to +10)
        """
        import numpy as np

        get_index.cache_clear()

        results = retrieve("water heater temperature")

        for result in results:
            assert result.score is not None, "Score should not be None"
            # Just verify scores are numeric (may be numpy types)
            assert isinstance(result.score, (int, float, np.floating))

    def test_retrieve_results_sorted_by_relevance(self) -> None:
        """Results should be sorted by score (highest first)."""
        get_index.cache_clear()

        results = retrieve("HRV cleaning")

        scores = [r.score for r in results if r.score is not None]
        assert len(scores) == len(results), "All scores should be present"
        assert scores == sorted(scores, reverse=True)

    def test_retrieve_results_have_metadata(self) -> None:
        """Results should include document metadata."""
        get_index.cache_clear()

        results = retrieve("thermostat settings")

        for result in results:
            metadata = result.node.metadata
            # Should have key metadata fields
            assert "file_name" in metadata
            assert "device_type" in metadata
