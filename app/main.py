"""FastAPI application for Home Ops Copilot."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.rag.query import query

app = FastAPI(
    title="Home Ops Copilot",
    description="RAG-powered assistant for home maintenance, troubleshooting, and parts management",
    version="0.1.0",
)


class AskRequest(BaseModel):
    """Request body for /ask endpoint."""

    question: str


class CitationResponse(BaseModel):
    """Citation in the response."""

    source: str
    page: int | None = None
    section: str | None = None
    quote: str | None = None


class AskResponse(BaseModel):
    """Response from /ask endpoint."""

    answer: str
    citations: list[CitationResponse]
    risk_level: str
    contexts: list[str]


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
        citations=[
            CitationResponse(
                source=c.source,
                page=c.page,
                section=c.section,
                quote=c.quote,
            )
            for c in result.citations
        ],
        risk_level=result.risk_level.value,
        contexts=result.contexts,
    )
