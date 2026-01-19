"""Tests for FastAPI endpoints.

Unit tests verify request validation without external dependencies.
Integration tests require the vector index and OpenAI API.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag.retriever import get_index


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


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
    """Integration tests for /ask endpoint with real RAG pipeline."""

    def test_ask_returns_populated_contexts(self, client: TestClient) -> None:
        """Should return contexts from retrieved documents."""
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I change my furnace filter?"},
        )

        assert response.status_code == 200
        data = response.json()

        # Contexts should be populated with retrieved chunks
        assert "contexts" in data
        assert len(data["contexts"]) > 0
        # Each context should be a non-empty string
        for ctx in data["contexts"]:
            assert isinstance(ctx, str)
            assert len(ctx) > 0

    def test_ask_returns_citations_for_relevant_question(self, client: TestClient) -> None:
        """Should return citations when context is relevant."""
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I change my furnace filter?"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have citations
        assert "citations" in data
        assert len(data["citations"]) > 0

        # Each citation should have a source
        for citation in data["citations"]:
            assert "source" in citation
            assert len(citation["source"]) > 0

    def test_ask_answer_references_sources(self, client: TestClient) -> None:
        """Answer should reference sources using [Source N] format."""
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I change my furnace filter?"},
        )

        assert response.status_code == 200
        data = response.json()

        # Answer should contain source references
        answer = data["answer"]
        assert "[Source" in answer, "Answer should contain [Source N] references"

    def test_ask_returns_risk_level(self, client: TestClient) -> None:
        """Should return a valid risk level."""
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I change my furnace filter?"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "risk_level" in data
        assert data["risk_level"] in ["LOW", "MED", "HIGH"]

    def test_ask_high_risk_recommends_professional(self, client: TestClient) -> None:
        """HIGH risk answers should recommend a professional."""
        get_index.cache_clear()

        response = client.post(
            "/ask",
            json={"question": "How do I replace my gas furnace igniter?"},
        )

        assert response.status_code == 200
        data = response.json()

        # If risk is HIGH, answer should mention professional
        if data["risk_level"] == "HIGH":
            answer_lower = data["answer"].lower()
            assert any(
                term in answer_lower
                for term in ["professional", "technician", "licensed", "hvac", "call"]
            ), "HIGH risk answer should recommend a professional"
