"""FastAPI application for Home Ops Copilot."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.rag.models import Citation
from app.rag.query import query

app = FastAPI(
    title="Home Ops Copilot",
    description="RAG-powered assistant for home maintenance, troubleshooting, and parts management",
    version="0.1.0",
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================
# These are API-specific models. Internal models live in app/rag/models.py


class AskRequest(BaseModel):
    """Request body for /ask endpoint."""

    question: str


class AskResponse(BaseModel):
    """Response from /ask endpoint."""

    answer: str
    citations: list[Citation]  # Reuse shared Citation model
    risk_level: str
    contexts: list[str]


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """
    Ask a question about home maintenance.

    Returns an answer with citations and risk level.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
        )

    result = query(request.question)

    return AskResponse(
        answer=result.answer,
        citations=result.citations,  # No conversion needed - same model
        risk_level=result.risk_level.value,
        contexts=result.contexts,
    )
