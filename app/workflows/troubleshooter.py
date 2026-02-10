"""Troubleshooting Tree Workflow with Safety Guardrails.

This module implements a two-invocation LangGraph workflow for guided
troubleshooting of home systems:

Invocation 1 (intake):
    START -> intake_parse -> retrieve_docs -> assess_risk -+-> generate_followups -> END
                                                           +-> safety_stop -> END

Invocation 2 (diagnosis, only if not safety-stopped):
    START -> generate_diagnosis -> render_output -> END

Session state is stored server-side between invocations using an in-memory
dict keyed by session ID.

Safety model:
    Layer 1: Deterministic keyword matching against SAFETY_STOP_PATTERNS
    Layer 2: LLM risk assessment via instructor (for nuanced cases)
    If either layer triggers HIGH + safety keywords -> workflow stops with
    professional recommendation. No DIY steps are generated.
"""

import logging

import instructor
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.rag.models import RiskLevel
from app.rag.retriever import retrieve
from app.workflows.models import RetrievedChunk
from app.workflows.troubleshooter_models import (
    DiagnosisResponse,
    FollowupGenerationResponse,
    TroubleshootingState,
    TroubleshootPhase,
)

logger = logging.getLogger(__name__)

# =============================================================================
# SAFETY STOP PATTERNS
# =============================================================================
# Deterministic keyword matching for high-risk scenarios that should
# ALWAYS stop the workflow and recommend a professional. These patterns
# bypass the LLM for immediate, reliable safety enforcement.

SAFETY_STOP_PATTERNS: dict[str, dict] = {
    "gas_leak": {
        "keywords": [
            "gas smell",
            "smell gas",
            "smells like gas",
            "rotten egg",
            "sulfur smell",
            "gas leak",
            "leaking gas",
            "hissing gas",
            "gas odor",
            "natural gas smell",
        ],
        "professional": "licensed gas technician or your gas utility company",
        "message": (
            "SAFETY ALERT: A gas smell or suspected gas leak is a serious emergency. "
            "Do NOT attempt any DIY troubleshooting. Leave the area immediately, "
            "do not operate any electrical switches, and call your gas utility's "
            "emergency line or 911 from outside your home."
        ),
    },
    "carbon_monoxide": {
        "keywords": [
            "co detector",
            "co alarm",
            "carbon monoxide alarm",
            "carbon monoxide detector",
            "co going off",
            "co beeping",
            "carbon monoxide beeping",
            "co poisoning",
        ],
        "professional": "licensed HVAC technician and your fire department",
        "message": (
            "SAFETY ALERT: A carbon monoxide alarm indicates a potentially "
            "life-threatening situation. Evacuate all people and pets immediately. "
            "Call 911 or your fire department from outside. Do NOT re-enter the "
            "home until emergency services have cleared it."
        ),
    },
    "electrical_hazard": {
        "keywords": [
            "sparking",
            "electrical spark",
            "burning smell electrical",
            "melting wire",
            "exposed wire",
            "wire sparking",
            "outlet sparking",
            "breaker keeps tripping",
            "electrical fire",
            "shock",
            "got shocked",
            "electrical shock",
            "buzzing outlet",
            "hot outlet",
            "scorched outlet",
            "burning outlet",
        ],
        "professional": "licensed electrician",
        "message": (
            "SAFETY ALERT: Electrical hazards can cause fires, injury, or death. "
            "Do NOT touch any sparking or damaged electrical components. Turn off "
            "the breaker for the affected circuit if you can safely do so. "
            "Call a licensed electrician immediately."
        ),
    },
    "structural": {
        "keywords": [
            "foundation crack",
            "load bearing wall",
            "sagging floor",
            "ceiling collapse",
            "structural crack",
            "beam damage",
            "joist cracking",
        ],
        "professional": "licensed structural engineer or general contractor",
        "message": (
            "SAFETY ALERT: Structural issues require professional assessment. "
            "Do NOT attempt any structural modifications or repairs yourself. "
            "Avoid the affected area if there are signs of active damage."
        ),
    },
    "water_gas_valve": {
        "keywords": [
            "gas valve stuck",
            "main gas valve",
            "gas shutoff",
            "water main break",
            "burst pipe flooding",
            "main water valve stuck",
        ],
        "professional": "licensed plumber or gas technician",
        "message": (
            "SAFETY ALERT: Main utility valve issues should be handled by "
            "a professional. If you're experiencing active flooding or can "
            "smell gas, call emergency services."
        ),
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def check_safety_patterns(symptom: str, device_type: str) -> dict | None:
    """Check symptom text against deterministic safety stop patterns.

    This is Layer 1 of the safety assessment: fast, deterministic keyword
    matching that doesn't require an LLM call.

    Args:
        symptom: The user-reported symptom text.
        device_type: The device type string.

    Returns:
        Dict with 'pattern_name', 'professional', 'message' if a pattern
        matches, or None if no safety stop is needed.
    """
    combined_text = f"{symptom} {device_type}".lower()

    for pattern_name, pattern in SAFETY_STOP_PATTERNS.items():
        for keyword in pattern["keywords"]:
            if keyword in combined_text:
                logger.warning(
                    f"Safety stop triggered: pattern={pattern_name}, keyword='{keyword}'"
                )
                return {
                    "pattern_name": pattern_name,
                    "professional": pattern["professional"],
                    "message": pattern["message"],
                }
    return None


def get_llm_client() -> instructor.Instructor:
    """Get an instructor-patched OpenAI client."""
    return instructor.from_openai(OpenAI(api_key=settings.openai_api_key))


# =============================================================================
# LLM PROMPTS
# =============================================================================

FOLLOWUP_SYSTEM_PROMPT = """You are a home maintenance diagnostic expert. Your job is to generate targeted follow-up questions that will help narrow down the root cause of a home system issue.

RULES:
1. Generate exactly 2-3 follow-up questions
2. Questions should be specific and diagnostic (not generic)
3. Use the retrieved documentation to inform what questions to ask
4. Consider the device type, reported symptom, and house profile
5. Each question should have a clear purpose (explain in the 'why' field)
6. Use appropriate question types:
   - yes_no: For binary diagnostic checks (e.g., "Is the pilot light visible?")
   - multiple_choice: For selecting from known options (e.g., "What color is the indicator light?")
   - free_text: For descriptions that vary widely (e.g., "What sound does it make?")
7. If you detect any safety concerns, note them even if they don't reach safety-stop level

IMPORTANT SAFETY RULES:
- If the symptom involves gas, electrical, CO, or structural concerns, set risk_level to HIGH
- Even for follow-up generation, flag any safety concerns you identify
"""

DIAGNOSIS_SYSTEM_PROMPT = """You are a home maintenance diagnostic expert. Based on the user's reported issue, their answers to follow-up questions, and relevant documentation, provide a structured diagnosis with actionable steps.

RULES:
1. Provide 3-6 diagnostic steps, ordered from simplest to most complex
2. Each step must include what to do, what to expect, and what to do if it doesn't work
3. The FINAL step should ALWAYS be: "If the issue persists, call a professional"
4. Cite source documents when your advice comes from the provided documentation
5. Be specific: include part numbers, settings, measurements when available from docs

CRITICAL SAFETY RULES - THESE ARE NON-NEGOTIABLE:
1. NEVER provide step-by-step instructions for gas line work
2. NEVER provide step-by-step instructions for electrical panel/wiring work
3. NEVER provide step-by-step instructions for structural modifications
4. For any step involving gas, high-voltage electrical, or structural work:
   - Set requires_professional=true
   - Set risk_level=HIGH
   - The instruction should be "Call a licensed [type] professional"
5. Steps like replacing filters, checking thermostat settings, or visual inspections are safe (LOW/MED)
6. Always include when_to_call_professional guidance
"""


# =============================================================================
# INTAKE GRAPH NODES
# =============================================================================


def intake_parse(state: TroubleshootingState) -> dict:
    """Parse and normalize intake inputs.

    Normalizes device_type to lowercase, validates it exists in the
    house profile (if provided), and sets initial state.

    Args:
        state: Current workflow state with intake inputs.

    Returns:
        Dict with normalized fields to merge into state.
    """
    if not state.symptom or not state.device_type:
        return {"error": "Missing symptom or device_type"}

    # Normalize device type to lowercase, replace spaces with underscores
    device_type = state.device_type.lower().strip().replace(" ", "_")
    logger.info(f"Intake: device_type={device_type}, symptom='{state.symptom[:80]}...'")

    # Check if device exists in house profile
    if state.house_profile:
        installed = list(state.house_profile.systems.keys())
        if device_type not in installed:
            logger.info(
                f"Device '{device_type}' not in house profile systems: {installed}. "
                "Proceeding anyway (user may know their systems better)."
            )

    return {
        "device_type": device_type,
        "phase": TroubleshootPhase.INTAKE,
    }


def retrieve_docs(state: TroubleshootingState) -> dict:
    """Retrieve relevant documents for the reported symptom.

    Queries the RAG index filtered by the device type, using the
    symptom text as the search query.

    Args:
        state: Current workflow state with device_type and symptom.

    Returns:
        Dict with 'retrieved_chunks' to merge into state.
    """
    if not state.symptom or not state.device_type:
        return {"retrieved_chunks": []}

    logger.info(f"Retrieving docs for device={state.device_type}, symptom='{state.symptom[:60]}'")

    try:
        nodes = retrieve(
            question=state.symptom,
            top_k=5,
            auto_filter=False,
            device_types=[state.device_type],
        )
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {"retrieved_chunks": [], "error": str(e)}

    retrieved_chunks = []
    for node in nodes:
        chunk = RetrievedChunk(
            text=node.node.get_content(),
            source=node.node.metadata.get("file_name", "Unknown"),
            device_type=node.node.metadata.get("device_type"),
            score=node.score if node.score is not None else 0.0,
        )
        retrieved_chunks.append(chunk)

    logger.info(f"Retrieved {len(retrieved_chunks)} chunks")
    return {"retrieved_chunks": retrieved_chunks}


def assess_risk(state: TroubleshootingState) -> dict:
    """Assess risk level using two-layer safety check.

    Layer 1: Deterministic keyword matching (fast, reliable)
    Layer 2: LLM risk assessment via instructor (nuanced)

    If Layer 1 triggers, we immediately safety-stop without an LLM call.
    If Layer 1 doesn't trigger, Layer 2 provides a nuanced assessment.

    Args:
        state: Current workflow state with symptom and device_type.

    Returns:
        Dict with risk assessment fields.
    """
    symptom = state.symptom or ""
    device_type = state.device_type or ""
    additional = state.additional_context or ""
    combined_text = f"{symptom} {additional}"

    # Layer 1: Deterministic keyword matching
    safety_match = check_safety_patterns(combined_text, device_type)
    if safety_match:
        logger.warning(f"Layer 1 safety stop: {safety_match['pattern_name']}")
        return {
            "risk_level": RiskLevel.HIGH,
            "is_safety_stop": True,
            "safety_message": safety_match["message"],
            "recommended_professional": safety_match["professional"],
        }

    # Layer 2: LLM risk assessment
    # Only runs if Layer 1 didn't trigger
    logger.info("Layer 1 passed, running Layer 2 LLM risk assessment")

    class RiskAssessment(BaseModel):
        """LLM risk assessment response."""

        risk_level: RiskLevel = Field(description="Risk level: LOW, MED, or HIGH")
        reasoning: str = Field(description="Why this risk level was assigned")
        safety_concern: bool = Field(
            default=False,
            description="Whether there's a safety concern requiring professional help",
        )
        recommended_professional: str | None = Field(
            default=None,
            description="Type of professional if safety concern is true",
        )

    try:
        client = get_llm_client()
        assessment = client.chat.completions.create(
            model=settings.llm.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a home safety assessor. Evaluate the risk level of "
                        "a reported home system issue. Consider: Is this something a "
                        "homeowner can safely investigate? Does it involve gas, "
                        "electrical, structural, or other hazards?"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Device: {device_type}\n"
                        f"Symptom: {symptom}\n"
                        f"Additional context: {additional}\n\n"
                        "Assess the risk level for DIY troubleshooting."
                    ),
                },
            ],
            response_model=RiskAssessment,
            temperature=0.1,
            max_completion_tokens=500,
        )

        is_safety_stop = assessment.safety_concern and assessment.risk_level == RiskLevel.HIGH
        result: dict = {
            "risk_level": assessment.risk_level,
            "is_safety_stop": is_safety_stop,
        }

        if is_safety_stop:
            result["safety_message"] = (
                f"SAFETY CONCERN: {assessment.reasoning}. "
                "This issue requires professional attention."
            )
            result["recommended_professional"] = assessment.recommended_professional

        logger.info(
            f"Layer 2 assessment: risk={assessment.risk_level}, safety_stop={is_safety_stop}"
        )
        return result

    except Exception as e:
        logger.error(f"LLM risk assessment failed: {e}")
        # Default to MED risk if LLM fails (conservative but not blocking)
        return {"risk_level": RiskLevel.MED, "is_safety_stop": False}


def risk_router(state: TroubleshootingState) -> str:
    """Route after risk assessment: safety_stop or generate_followups.

    This is a conditional edge function for LangGraph.

    Args:
        state: Current workflow state with risk assessment complete.

    Returns:
        "safety_stop" if is_safety_stop is True, else "generate_followups".
    """
    if state.is_safety_stop:
        return "safety_stop"
    return "generate_followups"


def safety_stop(state: TroubleshootingState) -> dict:
    """Build safety stop response.

    Sets the phase to SAFETY_STOP and ensures a clear message
    with professional recommendation is present.

    Args:
        state: Current workflow state with safety assessment.

    Returns:
        Dict with safety stop fields.
    """
    logger.warning(
        f"Safety stop activated for device={state.device_type}, "
        f"professional={state.recommended_professional}"
    )
    return {
        "phase": TroubleshootPhase.SAFETY_STOP,
        "followup_questions": [],
        "diagnostic_steps": [],
    }


def generate_followups(state: TroubleshootingState) -> dict:
    """Generate 2-3 targeted follow-up questions using the LLM.

    Uses retrieved documentation as context to generate diagnostic
    questions specific to the device and symptom.

    Args:
        state: Current workflow state with retrieval and risk assessment done.

    Returns:
        Dict with followup_questions and preliminary_assessment.
    """
    # Format retrieved chunks as context
    context_parts = []
    for i, chunk in enumerate(state.retrieved_chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk.source} ({chunk.device_type or 'general'})]\n{chunk.text}"
        )
    context = "\n\n---\n\n".join(context_parts) if context_parts else "No documentation available."

    # Build house profile context
    systems_info = ""
    if state.house_profile:
        system_details = state.house_profile.systems.get(state.device_type or "")
        if system_details:
            parts = []
            if system_details.manufacturer:
                parts.append(f"Manufacturer: {system_details.manufacturer}")
            if system_details.model:
                parts.append(f"Model: {system_details.model}")
            if system_details.fuel_type:
                parts.append(f"Fuel: {system_details.fuel_type}")
            if system_details.install_year:
                parts.append(f"Installed: {system_details.install_year}")
            systems_info = "\n".join(parts)

    user_message = f"""Device type: {state.device_type}
Reported symptom: {state.symptom}
Urgency: {state.urgency or "medium"}
Additional context: {state.additional_context or "None provided"}
Risk level: {state.risk_level.value if state.risk_level else "Unknown"}

Device details from house profile:
{systems_info or "No details available"}

Relevant documentation:
{context}

Generate 2-3 targeted follow-up questions to help diagnose this issue."""

    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.llm.model,
            messages=[
                {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_model=FollowupGenerationResponse,
            temperature=0.3,
            max_completion_tokens=2000,
        )

        logger.info(f"Generated {len(response.followup_questions)} follow-up questions")

        return {
            "followup_questions": response.followup_questions,
            "preliminary_assessment": response.preliminary_assessment,
            "risk_level": response.risk_level,
            "phase": TroubleshootPhase.FOLLOWUP,
        }

    except Exception as e:
        logger.error(f"Follow-up generation failed: {e}")
        return {
            "error": str(e),
            "followup_questions": [],
            "phase": TroubleshootPhase.FOLLOWUP,
        }


# =============================================================================
# DIAGNOSIS GRAPH NODES
# =============================================================================


def generate_diagnosis(state: TroubleshootingState) -> dict:
    """Generate a full diagnosis with diagnostic steps.

    Uses the complete context: intake info, retrieved docs, follow-up
    answers, and house profile to produce actionable diagnostic steps.

    Args:
        state: Full workflow state with follow-up answers populated.

    Returns:
        Dict with diagnosis fields.
    """
    # Format retrieved chunks
    context_parts = []
    for i, chunk in enumerate(state.retrieved_chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk.source} ({chunk.device_type or 'general'})]\n{chunk.text}"
        )
    context = "\n\n---\n\n".join(context_parts) if context_parts else "No documentation available."

    # Format follow-up Q&A
    qa_parts = []
    question_map = {q.id: q.question for q in state.followup_questions}
    for answer in state.followup_answers:
        question_text = question_map.get(answer.question_id, f"Question {answer.question_id}")
        qa_parts.append(f"Q: {question_text}\nA: {answer.answer}")
    qa_context = "\n\n".join(qa_parts) if qa_parts else "No follow-up answers provided."

    # Device details from house profile
    systems_info = ""
    if state.house_profile and state.device_type:
        system_details = state.house_profile.systems.get(state.device_type)
        if system_details:
            parts = []
            if system_details.manufacturer:
                parts.append(f"Manufacturer: {system_details.manufacturer}")
            if system_details.model:
                parts.append(f"Model: {system_details.model}")
            if system_details.fuel_type:
                parts.append(f"Fuel: {system_details.fuel_type}")
            if system_details.install_year:
                parts.append(f"Installed: {system_details.install_year}")
            systems_info = "\n".join(parts)

    user_message = f"""Device type: {state.device_type}
Reported symptom: {state.symptom}
Urgency: {state.urgency or "medium"}
Additional context: {state.additional_context or "None provided"}
Preliminary assessment: {state.preliminary_assessment or "None"}

Device details:
{systems_info or "No details available"}

Follow-up Q&A:
{qa_context}

Relevant documentation:
{context}

Provide a diagnosis with 3-6 actionable steps to resolve this issue. Remember: the final step must always recommend calling a professional if unresolved."""

    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.llm.model,
            messages=[
                {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_model=DiagnosisResponse,
            temperature=0.3,
            max_completion_tokens=4000,
        )

        logger.info(
            f"Generated diagnosis: {len(response.diagnostic_steps)} steps, "
            f"risk={response.overall_risk_level}"
        )

        return {
            "diagnosis_summary": response.diagnosis_summary,
            "diagnostic_steps": response.diagnostic_steps,
            "overall_risk_level": response.overall_risk_level,
            "when_to_call_professional": response.when_to_call_professional,
            "phase": TroubleshootPhase.DIAGNOSIS,
        }

    except Exception as e:
        logger.error(f"Diagnosis generation failed: {e}")
        return {"error": str(e), "phase": TroubleshootPhase.DIAGNOSIS}


def render_output(state: TroubleshootingState) -> dict:
    """Render diagnostic output as formatted markdown.

    Produces a markdown document with:
    - Diagnosis summary
    - Numbered diagnostic steps with risk badges
    - Source citations
    - Professional recommendation

    Args:
        state: Workflow state with diagnosis complete.

    Returns:
        Dict with 'markdown_output' and phase update.
    """
    lines = [
        "# Troubleshooting Diagnosis",
        f"**Device**: {state.device_type or 'Unknown'}",
        f"**Symptom**: {state.symptom or 'Not specified'}",
        "",
    ]

    # Risk badge
    risk = state.overall_risk_level or state.risk_level
    if risk:
        risk_emoji = {"LOW": "LOW", "MED": "MED", "HIGH": "HIGH"}.get(risk.value, "")
        lines.append(f"**Risk Level**: {risk_emoji}")
        lines.append("")

    # Diagnosis summary
    if state.diagnosis_summary:
        lines.extend(
            [
                "## Summary",
                "",
                state.diagnosis_summary,
                "",
            ]
        )

    # Diagnostic steps
    if state.diagnostic_steps:
        lines.extend(["## Diagnostic Steps", ""])

        for step in state.diagnostic_steps:
            # Step header with risk indicator
            risk_tag = ""
            if step.risk_level == RiskLevel.HIGH:
                risk_tag = " [HIGH RISK - Professional Required]"
            elif step.risk_level == RiskLevel.MED:
                risk_tag = " [Medium Risk]"

            lines.append(f"### Step {step.step_number}{risk_tag}")
            lines.append("")
            lines.append(f"**Do**: {step.instruction}")
            lines.append(f"**Expected**: {step.expected_outcome}")
            lines.append(f"**If not resolved**: {step.if_not_resolved}")

            if step.source_doc:
                lines.append(f"*Source: {step.source_doc}*")

            if step.requires_professional:
                lines.append("**This step requires a licensed professional.**")

            lines.append("")

    # When to call professional
    if state.when_to_call_professional:
        lines.extend(
            [
                "---",
                "",
                "## When to Call a Professional",
                "",
                state.when_to_call_professional,
                "",
            ]
        )

    # Sources
    sources = sorted({step.source_doc for step in state.diagnostic_steps if step.source_doc})
    if sources:
        lines.extend(
            [
                "---",
                f"*Sources: {', '.join(sources)}*",
            ]
        )

    markdown = "\n".join(lines)
    logger.info(f"Rendered markdown ({len(markdown)} chars)")

    return {
        "markdown_output": markdown,
        "phase": TroubleshootPhase.COMPLETE,
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================


def build_intake_graph() -> StateGraph:
    """Build the intake workflow graph (Invocation 1).

    Flow:
        START -> intake_parse -> retrieve_docs -> assess_risk
            --(if safety_stop)--> safety_stop -> END
            --(else)-----------> generate_followups -> END

    Returns:
        Configured StateGraph (not yet compiled).
    """
    graph = StateGraph(TroubleshootingState)

    # Add nodes
    graph.add_node("intake_parse", intake_parse)
    graph.add_node("retrieve_docs", retrieve_docs)
    graph.add_node("assess_risk", assess_risk)
    graph.add_node("safety_stop", safety_stop)
    graph.add_node("generate_followups", generate_followups)

    # Add edges
    graph.add_edge(START, "intake_parse")
    graph.add_edge("intake_parse", "retrieve_docs")
    graph.add_edge("retrieve_docs", "assess_risk")

    # Conditional edge after risk assessment
    graph.add_conditional_edges(
        "assess_risk",
        risk_router,
        {
            "safety_stop": "safety_stop",
            "generate_followups": "generate_followups",
        },
    )

    graph.add_edge("safety_stop", END)
    graph.add_edge("generate_followups", END)

    return graph


def build_diagnosis_graph() -> StateGraph:
    """Build the diagnosis workflow graph (Invocation 2).

    Flow:
        START -> generate_diagnosis -> render_output -> END

    Returns:
        Configured StateGraph (not yet compiled).
    """
    graph = StateGraph(TroubleshootingState)

    # Add nodes
    graph.add_node("generate_diagnosis", generate_diagnosis)
    graph.add_node("render_output", render_output)

    # Add edges
    graph.add_edge(START, "generate_diagnosis")
    graph.add_edge("generate_diagnosis", "render_output")
    graph.add_edge("render_output", END)

    return graph


def create_intake_workflow() -> CompiledStateGraph:
    """Create a compiled intake workflow (Invocation 1).

    Returns:
        Compiled workflow ready for invocation.

    Example:
        >>> workflow = create_intake_workflow()
        >>> result = workflow.invoke({
        ...     "device_type": "furnace",
        ...     "symptom": "No heat coming from vents",
        ...     "house_profile": profile,
        ... })
    """
    return build_intake_graph().compile()


def create_diagnosis_workflow() -> CompiledStateGraph:
    """Create a compiled diagnosis workflow (Invocation 2).

    Returns:
        Compiled workflow ready for invocation.

    Example:
        >>> workflow = create_diagnosis_workflow()
        >>> result = workflow.invoke(session_state_dict)
    """
    return build_diagnosis_graph().compile()
