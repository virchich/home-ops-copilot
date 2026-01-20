"""Shared models for the RAG system.

This module contains all Pydantic models used across the RAG pipeline.
Having models in one place:
1. Eliminates duplication between modules
2. Makes the data contracts clear
3. Enables reuse in tests
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# ENUMS
# =============================================================================


class RiskLevel(str, Enum):
    """Risk level for home maintenance advice.

    Used to classify the safety risk of following advice:
    - LOW: Safe for any homeowner to do themselves
    - MED: Requires some caution or basic skills
    - HIGH: Involves gas, electrical, structural, or safety-critical work
    """

    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


# =============================================================================
# CITATION MODELS
# =============================================================================


class Citation(BaseModel):
    """A citation to a source document.

    Used to track where information came from, enabling:
    - User verification of answers
    - Debugging retrieval quality
    - Trust through transparency
    """

    source: str = Field(description="The source document name or path")
    page: int | None = Field(default=None, description="Page number if applicable")
    section: str | None = Field(default=None, description="Section name if applicable")
    quote: str | None = Field(default=None, description="Relevant quote from the source")


# =============================================================================
# LLM RESPONSE MODELS
# =============================================================================


class LLMResponse(BaseModel):
    """Structured response from the LLM (internal model).

    This model is used with the `instructor` library to enforce
    structured outputs via OpenAI function calling. The LLM MUST
    return data matching this structure.

    Note: This is an internal model - external APIs use QueryResponse.
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
    citations: list[Citation] = Field(
        default_factory=list,
        description="Citations to source documents that support the answer. "
        "Each citation should reference a specific source from the provided context.",
    )


# =============================================================================
# API RESPONSE MODELS
# =============================================================================


class QueryResponse(BaseModel):
    """Response from the query engine.

    This is the primary response model returned by the RAG pipeline.
    It includes everything needed for:
    - User-facing answers (answer, citations, risk_level)
    - Evaluation (contexts for measuring retrieval quality)
    """

    answer: str = Field(description="The answer to the user's question")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Citations to source documents",
    )
    risk_level: RiskLevel = Field(description="Risk assessment for the task")
    contexts: list[str] = Field(
        default_factory=list,
        description="Retrieved context chunks (for evaluation)",
    )
