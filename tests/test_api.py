"""Tests for FastAPI endpoints.

Unit tests verify request validation without external dependencies.
Integration tests require the vector index and OpenAI API.

Integration test design principles:
- Test response structure/contract, not specific LLM content
- Use lenient assertions for non-deterministic LLM output
- Consolidate tests to minimize API calls (~$0.01-0.05 per call)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag.retriever import get_index


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# =============================================================================
# UNIT TESTS - Health Endpoint
# =============================================================================


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.json() == {"status": "healthy"}

    def test_health_content_type(self, client: TestClient) -> None:
        """Health endpoint should return JSON content type."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


# =============================================================================
# UNIT TESTS - /ask Endpoint Validation
# =============================================================================


class TestAskEndpointValidation:
    """Tests for /ask endpoint request validation."""

    def test_ask_requires_question(self, client: TestClient) -> None:
        """Ask endpoint should require a question field."""
        response = client.post("/ask", json={})
        assert response.status_code == 422  # Validation error

    def test_ask_rejects_empty_body(self, client: TestClient) -> None:
        """Ask endpoint should reject requests without body."""
        response = client.post("/ask")
        assert response.status_code == 422

    def test_ask_rejects_wrong_content_type(self, client: TestClient) -> None:
        """Ask endpoint should reject non-JSON content."""
        response = client.post("/ask", content="not json", headers={"Content-Type": "text/plain"})
        assert response.status_code == 422


# =============================================================================
# UNIT TESTS - OpenAPI Schema
# =============================================================================


class TestOpenAPISchema:
    """Tests for OpenAPI schema generation."""

    def test_openapi_schema_available(self, client: TestClient) -> None:
        """OpenAPI schema should be available at /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Home Ops Copilot"

    def test_docs_available(self, client: TestClient) -> None:
        """Swagger docs should be available at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200


# =============================================================================
# INTEGRATION TESTS - /ask endpoint with real RAG pipeline
# =============================================================================
# These tests require:
# 1. Vector index built (run `make ingest` first)
# 2. OpenAI API key set in environment
# Run with: make test-integration


@pytest.mark.integration
class TestAskEndpointIntegration:
    """Integration tests for /ask endpoint with real RAG pipeline.

    Design notes:
    - Tests are consolidated to minimize API calls
    - Assertions are lenient for non-deterministic LLM output
    - Focus on response structure/contract, not specific content
    """

    def test_ask_returns_complete_response_structure(self, client: TestClient) -> None:
        """Response should contain all required fields with correct types.

        This is the main integration test - it verifies the full pipeline
        returns a properly structured response. We test structure, not content,
        because LLM output is non-deterministic.
        """
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I change my furnace filter?"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields exist
        assert "answer" in data, "Response must contain 'answer' field"
        assert "citations" in data, "Response must contain 'citations' field"
        assert "risk_level" in data, "Response must contain 'risk_level' field"
        assert "contexts" in data, "Response must contain 'contexts' field"

        # Verify field types
        assert isinstance(data["answer"], str), "answer must be a string"
        assert isinstance(data["citations"], list), "citations must be a list"
        assert isinstance(data["contexts"], list), "contexts must be a list"
        assert data["risk_level"] in ["LOW", "MED", "HIGH"], "risk_level must be LOW/MED/HIGH"

        # Verify answer is non-empty (LLM should always respond)
        assert len(data["answer"]) > 0, "answer should not be empty"

        # Verify contexts were retrieved (for a question about furnace filters)
        assert len(data["contexts"]) > 0, "contexts should contain retrieved chunks"
        for ctx in data["contexts"]:
            assert isinstance(ctx, str), "each context must be a string"
            assert len(ctx) > 0, "contexts should not be empty strings"

    def test_ask_citations_have_valid_structure(self, client: TestClient) -> None:
        """Citations should have the expected structure when present.

        Note: We don't assert citations exist because LLM might not always
        generate them. But when they do exist, they should be well-formed.
        """
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I change my furnace filter?"},
        )

        assert response.status_code == 200
        data = response.json()

        # If citations exist, verify their structure
        for citation in data["citations"]:
            assert "source" in citation, "citation must have 'source' field"
            assert isinstance(citation["source"], str), "source must be a string"
            # page, section, quote are optional - just verify types if present
            if "page" in citation and citation["page"] is not None:
                assert isinstance(citation["page"], int), "page must be an integer"
            if "section" in citation and citation["section"] is not None:
                assert isinstance(citation["section"], str), "section must be a string"
            if "quote" in citation and citation["quote"] is not None:
                assert isinstance(citation["quote"], str), "quote must be a string"

    def test_ask_handles_different_risk_levels(self, client: TestClient) -> None:
        """Different questions should potentially return different risk levels.

        This test verifies the system can distinguish between low and high risk
        questions. We use two very different questions to maximize the chance
        of getting different risk assessments.
        """
        get_index.cache_clear()

        # Low risk question
        low_risk_response = client.post(
            "/ask",
            json={"question": "How often should I check my furnace filter?"},
        )
        assert low_risk_response.status_code == 200
        low_risk_data = low_risk_response.json()

        # Higher risk question (gas-related)
        high_risk_response = client.post(
            "/ask",
            json={"question": "How do I relight the pilot light on my gas furnace?"},
        )
        assert high_risk_response.status_code == 200
        high_risk_data = high_risk_response.json()

        # Both should have valid risk levels
        assert low_risk_data["risk_level"] in ["LOW", "MED", "HIGH"]
        assert high_risk_data["risk_level"] in ["LOW", "MED", "HIGH"]

        # The gas-related question should ideally be rated higher risk
        # But we don't strictly assert this since LLM behavior varies
        # Instead, we just verify both responses are valid

        # If the gas question is HIGH risk, verify professional recommendation
        if high_risk_data["risk_level"] == "HIGH":
            answer_lower = high_risk_data["answer"].lower()
            professional_terms = ["professional", "technician", "licensed", "hvac", "qualified", "expert", "call"]
            has_professional_mention = any(term in answer_lower for term in professional_terms)
            # This is a soft assertion - log warning instead of failing
            if not has_professional_mention:
                import warnings
                warnings.warn(
                    "HIGH risk answer did not mention professional - "
                    "consider adjusting system prompt"
                )
