"""Query engine for RAG-based question answering.

Week 1: Stub implementation that calls LLM directly without retrieval.
Week 2+: Will add actual document retrieval.

Uses the `instructor` library for structured, Pydantic-validated LLM outputs.
This is more reliable than manual parsing and leverages OpenAI's function calling.
"""

from enum import Enum
from typing import Literal

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

# =============================================================================
# RESPONSE MODELS (Pydantic)
# =============================================================================
# These models define the structure of LLM outputs.
# Instructor uses these to generate a JSON schema and validate responses.


class RiskLevel(str, Enum):
    """Risk level for home maintenance advice."""

    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class Citation(BaseModel):
    """A citation to a source document."""

    source: str = Field(description="The source document name or path")
    page: int | None = Field(default=None, description="Page number if applicable")
    section: str | None = Field(default=None, description="Section name if applicable")
    quote: str | None = Field(default=None, description="Relevant quote from the source")


class LLMResponse(BaseModel):
    """
    Structured response from the LLM.

    Instructor will enforce this schema via OpenAI function calling.
    The LLM MUST return data matching this structure.
    """

    answer: str = Field(
        description="A concise, actionable answer to the user's question. "
        "If risk is HIGH, MUST recommend calling a licensed professional."
    )
    risk_level: Literal["LOW", "MED", "HIGH"] = Field(
        description="Risk assessment for the task. "
        "LOW = safe DIY, MED = some caution needed, HIGH = professional required"
    )
    reasoning: str = Field(description="Brief explanation of why this risk level was assigned")


class QueryResponse(BaseModel):
    """Final response from the query engine (includes retrieval context)."""

    answer: str
    citations: list[Citation]
    risk_level: RiskLevel
    contexts: list[str]  # Retrieved context chunks (for eval)


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
# Note: We no longer need format instructions because instructor handles that.
# The prompt focuses on behavior and domain knowledge.

SYSTEM_PROMPT = """You are a home maintenance assistant. Answer questions about home maintenance, troubleshooting, and repairs.

IMPORTANT RULES:
1. Assess risk level for every question:
   - LOW: Safe for any homeowner to do themselves
   - MED: Requires some caution or basic skills
   - HIGH: Involves gas, electrical, structural, or safety-critical work

2. If risk is HIGH, you MUST recommend calling a licensed professional (electrician, plumber, HVAC tech, etc.)

3. Be concise and actionable - homeowners want clear steps, not essays

4. If you don't have enough information to answer safely, say so - never guess on safety-critical topics

5. For now, you don't have access to specific documents about the user's home. When the RAG system is connected, you will receive relevant document excerpts to cite.
"""


# =============================================================================
# QUERY FUNCTION
# =============================================================================


def query(question: str) -> QueryResponse:
    """
    Query the system with a question and get a structured response.

    Uses instructor to get Pydantic-validated outputs from the LLM.
    This is more reliable than manual parsing.

    Args:
        question: The user's question about home maintenance.

    Returns:
        QueryResponse with answer, citations, risk level, and contexts.

    Note:
        Week 1 stub: No retrieval, just LLM call.
        Week 2+: Will retrieve relevant documents first.
    """
    # Patch OpenAI client with instructor for structured outputs
    client = instructor.from_openai(OpenAI(api_key=settings.openai_api_key))

    # Week 1: No retrieval, just call LLM directly
    # TODO: Week 2+ - Add retrieval step here
    contexts: list[str] = []

    # Call LLM with structured output
    # instructor automatically:
    # 1. Converts LLMResponse to a JSON schema
    # 2. Uses OpenAI function calling to enforce the schema
    # 3. Validates the response against the Pydantic model
    # 4. Retries if validation fails (configurable)
    llm_response = client.chat.completions.create(
        model=settings.llm.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        response_model=LLMResponse,  # This is the magic - instructor enforces this
        temperature=settings.llm.temperature,
        max_completion_tokens=settings.llm.max_completion_tokens,
    )

    # Week 1: No citations since no retrieval
    # TODO: Week 2+ - Extract citations from retrieved docs
    citations: list[Citation] = []

    return QueryResponse(
        answer=llm_response.answer,
        citations=citations,
        risk_level=RiskLevel(llm_response.risk_level),
        contexts=contexts,
    )
