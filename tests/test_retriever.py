"""Tests for the retriever module.

Unit tests use mocked nodes and don't require the vector index.
Integration tests require the index to be built (run `make ingest` first).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.rag.retriever import (
    build_source_mapping,
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
            patch("app.rag.retriever.settings") as mock_settings,
        ):
            # Setup mocks
            mock_settings.rag.top_k = 7
            mock_index = MagicMock()
            mock_get_index.return_value = mock_index
            mock_retriever = MagicMock()
            mock_retriever.retrieve.return_value = []
            mock_retriever_class.return_value = mock_retriever

            # Call without top_k
            retrieve("test question")

            # Verify retriever was created with settings value
            mock_retriever_class.assert_called_once_with(
                index=mock_index,
                similarity_top_k=7,
            )

    def test_uses_explicit_top_k_when_provided(self) -> None:
        """Should use explicit top_k when provided."""
        with (
            patch("app.rag.retriever.get_index") as mock_get_index,
            patch("app.rag.retriever.VectorIndexRetriever") as mock_retriever_class,
            patch("app.rag.retriever.settings") as mock_settings,
        ):
            # Setup mocks
            mock_settings.rag.top_k = 5  # Default
            mock_index = MagicMock()
            mock_get_index.return_value = mock_index
            mock_retriever = MagicMock()
            mock_retriever.retrieve.return_value = []
            mock_retriever_class.return_value = mock_retriever

            # Call with explicit top_k
            retrieve("test question", top_k=10)

            # Verify retriever was created with explicit value
            mock_retriever_class.assert_called_once_with(
                index=mock_index,
                similarity_top_k=10,
            )


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
        """Should return exactly top_k results."""
        get_index.cache_clear()

        results = retrieve("furnace maintenance", top_k=3)

        assert len(results) == 3

    def test_retrieve_results_have_scores(self) -> None:
        """Results should have similarity scores between 0 and 1."""
        get_index.cache_clear()

        results = retrieve("water heater temperature")

        for result in results:
            assert result.score is not None, "Score should not be None"
            assert 0 <= result.score <= 1

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
