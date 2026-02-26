"""FastAPI application for Home Ops Copilot."""

import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.core.ssl_setup import configure_ssl
from app.llm.tracing import init_tracing, observe
from app.rag.models import Citation
from app.rag.query import query
from app.workflows.maintenance_planner import create_maintenance_planner
from app.workflows.models import (
    HouseProfile,
    MaintenancePlanRequest,
    MaintenancePlanResponse,
    load_house_profile,
    save_house_profile,
)
from app.workflows.parts_helper import create_parts_helper
from app.workflows.parts_helper_models import (
    PartsLookupAPIResponse,
    PartsLookupRequest,
)
from app.workflows.troubleshooter import create_diagnosis_workflow, create_intake_workflow
from app.workflows.troubleshooter_models import (
    TroubleshootDiagnoseRequest,
    TroubleshootDiagnoseResponse,
    TroubleshootingState,
    TroubleshootPhase,
    TroubleshootStartRequest,
    TroubleshootStartResponse,
)

# Must run before any HTTP client is created (fixes SSL on corporate proxies)
configure_ssl()

# Initialize Langfuse tracing (no-op when OBSERVABILITY__ENABLED=false)
init_tracing()

app = FastAPI(
    title="Home Ops Copilot",
    description="RAG-powered assistant for home maintenance, troubleshooting, and parts management",
    version="0.1.0",
)

# =============================================================================
# PRE-COMPILED WORKFLOWS
# =============================================================================
# LangGraph compilation is deterministic and stateless — the compiled graph is
# reusable across requests. Compiling once at module level avoids redundant work.

_maintenance_planner = create_maintenance_planner()
_parts_helper = create_parts_helper()
_intake_workflow = create_intake_workflow()
_diagnosis_workflow = create_diagnosis_workflow()

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
@observe(name="api_ask")
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
@observe(name="api_maintenance_plan")
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

    # Run the workflow
    result = _maintenance_planner.invoke(
        {
            "house_profile": profile,
            "season": request.season,
        }
    )

    # Check for errors
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Extract unique source documents from checklist items
    sources_used = list(
        {item.source_doc for item in result.get("checklist_items", []) if item.source_doc}
    )

    return MaintenancePlanResponse(
        season=request.season,
        house_name=profile.name,
        checklist_items=result.get("checklist_items", []),
        markdown=result.get("markdown_output", ""),
        sources_used=sources_used,
    )


@app.get("/house-profile", response_model=HouseProfile)
def get_house_profile() -> HouseProfile:
    """
    Get the current house profile.

    Returns the house profile from data/house_profile.json.
    """
    try:
        return load_house_profile()
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=404,
            detail="House profile not found. Create data/house_profile.json first.",
        ) from err


@app.put("/house-profile", response_model=HouseProfile)
def update_house_profile(profile: HouseProfile) -> HouseProfile:
    """
    Update the house profile.

    Saves the provided house profile to data/house_profile.json.
    Returns the saved profile.
    """
    save_house_profile(profile)
    return profile


# =============================================================================
# PARTS LOOKUP ENDPOINT
# =============================================================================


@app.post("/parts/lookup", response_model=PartsLookupAPIResponse)
@observe(name="api_parts_lookup")
def parts_lookup(request: PartsLookupRequest) -> PartsLookupAPIResponse:
    """
    Look up replacement parts and consumables.

    Takes a query (e.g., "What filter for the furnace?") and optionally
    a device type. Returns identified parts with confidence levels,
    plus clarification questions if information is incomplete.

    No session storage needed — users refine by re-querying with more detail.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
        )

    # Load house profile
    try:
        profile = load_house_profile()
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=404,
            detail="House profile not found. Create data/house_profile.json first.",
        ) from err

    # Run parts helper workflow
    result = _parts_helper.invoke(
        {
            "query": request.query,
            "device_type": request.device_type,
            "house_profile": profile,
        }
    )

    # Check for errors
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Extract unique source documents
    sources_used = sorted({part.source_doc for part in result.get("parts", []) if part.source_doc})

    return PartsLookupAPIResponse(
        parts=result.get("parts", []),
        clarification_questions=result.get("clarification_questions", []),
        summary=result.get("summary", ""),
        markdown=result.get("markdown_output", ""),
        sources_used=sources_used,
        has_gaps=bool(result.get("clarification_questions")),
    )


# =============================================================================
# TROUBLESHOOTING ENDPOINTS
# =============================================================================
# In-memory session storage for troubleshooting state between invocations.
# Adequate for a local-first single-user app.
# Sessions expire after 1 hour and are capped at 100 to prevent memory leaks.

_SESSION_TTL_SECONDS = 3600  # 1 hour
_SESSION_MAX_COUNT = 100

_troubleshoot_sessions: dict[str, tuple[float, TroubleshootingState]] = {}


def _evict_expired_sessions() -> None:
    """Remove sessions older than _SESSION_TTL_SECONDS."""
    now = time.monotonic()
    expired = [
        sid
        for sid, (created_at, _) in _troubleshoot_sessions.items()
        if now - created_at > _SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _troubleshoot_sessions.pop(sid, None)


@app.post("/troubleshoot/start", response_model=TroubleshootStartResponse)
@observe(name="api_troubleshoot_start")
def troubleshoot_start(request: TroubleshootStartRequest) -> TroubleshootStartResponse:
    """
    Start a troubleshooting session.

    Takes device type and symptom, runs the intake workflow (retrieval +
    risk assessment + follow-up generation), and returns either follow-up
    questions or a safety stop.

    Session state is stored server-side for the diagnosis step.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
        )

    # Load house profile
    try:
        profile = load_house_profile()
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=404,
            detail="House profile not found. Create data/house_profile.json first.",
        ) from err

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Run intake workflow
    result = _intake_workflow.invoke(
        {
            "device_type": request.device_type,
            "symptom": request.symptom,
            "urgency": request.urgency,
            "additional_context": request.additional_context,
            "house_profile": profile,
            "session_id": session_id,
        }
    )

    # Check for errors
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Evict expired sessions and enforce cap before storing
    _evict_expired_sessions()
    if len(_troubleshoot_sessions) >= _SESSION_MAX_COUNT:
        oldest_sid = min(_troubleshoot_sessions, key=lambda s: _troubleshoot_sessions[s][0])
        _troubleshoot_sessions.pop(oldest_sid, None)

    # Store session state for diagnosis step
    session_state = TroubleshootingState(
        **{k: v for k, v in result.items() if k in TroubleshootingState.model_fields}
    )
    _troubleshoot_sessions[session_id] = (time.monotonic(), session_state)

    return TroubleshootStartResponse(
        session_id=session_id,
        phase=result.get("phase", TroubleshootPhase.FOLLOWUP),
        risk_level=result["risk_level"],
        followup_questions=result.get("followup_questions", []),
        preliminary_assessment=result.get("preliminary_assessment"),
        is_safety_stop=result.get("is_safety_stop", False),
        safety_message=result.get("safety_message"),
        recommended_professional=result.get("recommended_professional"),
    )


@app.post("/troubleshoot/diagnose", response_model=TroubleshootDiagnoseResponse)
@observe(name="api_troubleshoot_diagnose")
def troubleshoot_diagnose(request: TroubleshootDiagnoseRequest) -> TroubleshootDiagnoseResponse:
    """
    Submit follow-up answers and get a diagnosis.

    Loads the session state from the start step, injects the user's
    follow-up answers, runs the diagnosis workflow, and returns
    diagnostic steps with safety guidance.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
        )

    # Load session state
    _evict_expired_sessions()
    session_entry = _troubleshoot_sessions.get(request.session_id)
    if not session_entry:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Start a new troubleshooting session.",
        )

    _, session_state = session_entry

    # Safety check: don't allow diagnosis on safety-stopped sessions
    if session_state.is_safety_stop:
        raise HTTPException(
            status_code=400,
            detail="This session was safety-stopped. No diagnosis will be generated. "
            "Please follow the safety guidance provided.",
        )

    # Build state dict with follow-up answers injected
    state_dict = session_state.model_dump()
    state_dict["followup_answers"] = [a.model_dump() for a in request.answers]

    # Run diagnosis workflow
    result = _diagnosis_workflow.invoke(state_dict)

    # Check for errors
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Extract sources from diagnostic steps
    sources_used = sorted(
        {step.source_doc for step in result.get("diagnostic_steps", []) if step.source_doc}
    )

    # Clean up session (one-time use)
    _troubleshoot_sessions.pop(request.session_id, None)

    return TroubleshootDiagnoseResponse(
        session_id=request.session_id,
        diagnosis_summary=result.get("diagnosis_summary", ""),
        diagnostic_steps=result.get("diagnostic_steps", []),
        overall_risk_level=result["overall_risk_level"],
        when_to_call_professional=result.get("when_to_call_professional", ""),
        markdown=result.get("markdown_output", ""),
        sources_used=sources_used,
    )
