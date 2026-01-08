"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


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
