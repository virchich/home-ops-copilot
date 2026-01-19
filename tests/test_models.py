"""Tests for shared RAG models."""

import pytest

from app.rag.models import Citation, LLMResponse, QueryResponse, RiskLevel


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_level_values(self) -> None:
        """Should have expected risk level values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MED.value == "MED"
        assert RiskLevel.HIGH.value == "HIGH"

    def test_risk_level_from_string(self) -> None:
        """Should be able to create from string value."""
        assert RiskLevel("LOW") == RiskLevel.LOW
        assert RiskLevel("MED") == RiskLevel.MED
        assert RiskLevel("HIGH") == RiskLevel.HIGH

    def test_risk_level_invalid_raises(self) -> None:
        """Should raise for invalid risk level."""
        with pytest.raises(ValueError):
            RiskLevel("INVALID")


class TestCitation:
    """Tests for Citation model."""

    def test_citation_required_fields(self) -> None:
        """Should require source field."""
        citation = Citation(source="manual.pdf")
        assert citation.source == "manual.pdf"
        assert citation.page is None
        assert citation.section is None
        assert citation.quote is None

    def test_citation_all_fields(self) -> None:
        """Should accept all optional fields."""
        citation = Citation(
            source="furnace-manual.pdf",
            page=12,
            section="Filter Replacement",
            quote="Change filter every 3 months",
        )
        assert citation.source == "furnace-manual.pdf"
        assert citation.page == 12
        assert citation.section == "Filter Replacement"
        assert citation.quote == "Change filter every 3 months"

    def test_citation_serialization(self) -> None:
        """Should serialize to dict correctly."""
        citation = Citation(source="test.pdf", page=5)
        data = citation.model_dump()
        assert data["source"] == "test.pdf"
        assert data["page"] == 5
        assert data["section"] is None


class TestLLMResponse:
    """Tests for LLMResponse model (internal LLM response)."""

    def test_llm_response_required_fields(self) -> None:
        """Should require answer, risk_level, and reasoning."""
        response = LLMResponse(
            answer="Change the filter.",
            risk_level="LOW",
            reasoning="Simple DIY task.",
        )
        assert response.answer == "Change the filter."
        assert response.risk_level == "LOW"
        assert response.reasoning == "Simple DIY task."
        assert response.citations == []

    def test_llm_response_with_citations(self) -> None:
        """Should accept citations list."""
        response = LLMResponse(
            answer="Set to 120°F.",
            risk_level="MED",
            reasoning="Hot water can scald.",
            citations=[Citation(source="water-heater.pdf", page=8)],
        )
        assert len(response.citations) == 1
        assert response.citations[0].source == "water-heater.pdf"

    def test_llm_response_validates_risk_level(self) -> None:
        """Should only accept valid risk level literals."""
        # Valid values work
        for level in ["LOW", "MED", "HIGH"]:
            response = LLMResponse(
                answer="Test",
                risk_level=level,
                reasoning="Test",
            )
            assert response.risk_level == level

        # Invalid value raises
        with pytest.raises(ValueError):
            LLMResponse(
                answer="Test",
                risk_level="INVALID",
                reasoning="Test",
            )


class TestQueryResponse:
    """Tests for QueryResponse model (API response)."""

    def test_query_response_minimal(self) -> None:
        """Should work with minimal fields."""
        response = QueryResponse(
            answer="Test answer",
            risk_level=RiskLevel.LOW,
        )
        assert response.answer == "Test answer"
        assert response.risk_level == RiskLevel.LOW
        assert response.citations == []
        assert response.contexts == []

    def test_query_response_full(self) -> None:
        """Should accept all fields."""
        response = QueryResponse(
            answer="Detailed answer",
            citations=[Citation(source="doc.pdf")],
            risk_level=RiskLevel.HIGH,
            contexts=["Context chunk 1", "Context chunk 2"],
        )
        assert response.answer == "Detailed answer"
        assert len(response.citations) == 1
        assert response.risk_level == RiskLevel.HIGH
        assert len(response.contexts) == 2

    def test_query_response_serialization(self) -> None:
        """Should serialize correctly for API responses."""
        response = QueryResponse(
            answer="Test",
            citations=[Citation(source="test.pdf", page=1)],
            risk_level=RiskLevel.MED,
            contexts=["chunk"],
        )
        data = response.model_dump()
        assert data["answer"] == "Test"
        assert data["risk_level"] == "MED"  # Enum serializes to value
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source"] == "test.pdf"
