"""FastAPI application for Home Ops Copilot."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.rag.models import Citation
from app.rag.query import query
from app.workflows.maintenance_planner import create_maintenance_planner
from app.workflows.models import (
    MaintenancePlanRequest,
    MaintenancePlanResponse,
    load_house_profile,
)

app = FastAPI(
    title="Home Ops Copilot",
    description="RAG-powered assistant for home maintenance, troubleshooting, and parts management",
    version="0.1.0",
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/maintenance-plan", response_model=MaintenancePlanResponse)
def generate_maintenance_plan(request: MaintenancePlanRequest) -> MaintenancePlanResponse:
    """
    Generate a seasonal maintenance plan for a house.

    Takes a season and optionally a house profile path. Returns a structured
    checklist with Apple Notes-friendly markdown output.

    This endpoint invokes a LangGraph workflow that:
    1. Retrieves relevant documents from the RAG index
    2. Generates checklist items using the LLM
    3. Renders the checklist as markdown
    """
    # Load house profile
    try:
        profile = load_house_profile()
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=404,
            detail="House profile not found. Create data/house_profile.json first.",
        ) from err

    # Create and run the workflow
    planner = create_maintenance_planner()
    result = planner.invoke({
        "house_profile": profile,
        "season": request.season,
    })

    # Check for errors
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Extract unique source documents from checklist items
    sources_used = list({
        item.source_doc
        for item in result.get("checklist_items", [])
        if item.source_doc
    })

    return MaintenancePlanResponse(
        season=request.season,
        house_name=profile.name,
        checklist_items=result.get("checklist_items", []),
        markdown=result.get("markdown_output", ""),
        sources_used=sources_used,
    )
