"""Models for the parts & consumables helper workflow.

This module contains Pydantic models for the single-invocation parts lookup
workflow:

    START → parse_query → retrieve_docs → generate_parts_list → render_markdown → END

Models are organized into:
- Enums (ConfidenceLevel)
- Value objects (PartRecommendation, ClarificationQuestion)
- Instructor response model (PartsLookupResponse)
- Workflow state (PartsHelperState)
- API request/response models
"""

from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.workflows.models import HouseProfile, RetrievedChunk

# =============================================================================
# ENUMS
# =============================================================================


class ConfidenceLevel(str, Enum):
    """Confidence level for a part recommendation.

    CONFIRMED: Found in documentation with a part number or explicit reference.
    LIKELY: Inferred from documentation (e.g., device model matches, specs align).
    UNCERTAIN: General knowledge, not directly supported by indexed documents.
    """

    CONFIRMED = "confirmed"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"


# =============================================================================
# VALUE OBJECTS
# =============================================================================


class PartRecommendation(BaseModel):
    """A single part or consumable recommendation.

    Example:
        {
            "part_name": "Furnace Air Filter",
            "part_number": "16x25x1 MERV 11",
            "device_type": "furnace",
            "device_model": "OM9GFRC",
            "description": "Standard replacement air filter",
            "replacement_interval": "Every 1-3 months during heating season",
            "where_to_buy": "Home Depot, Amazon",
            "confidence": "confirmed",
            "source_doc": "Furnace-OM9GFRC-02.pdf",
            "notes": "Use MERV 8-11 for standard filtration"
        }
    """

    part_name: str = Field(description="Name of the part or consumable")
    part_number: str | None = Field(
        default=None,
        description="Part number, filter size, or specific identifier. "
        "Must be None if confidence is UNCERTAIN.",
    )
    device_type: str = Field(description="Which device/system this part is for")
    device_model: str | None = Field(
        default=None,
        description="Specific device model this part fits (from house profile or docs)",
    )
    description: str = Field(description="Brief description of the part and its purpose")
    replacement_interval: str | None = Field(
        default=None,
        description="How often this part should be replaced (e.g., 'Every 3 months')",
    )
    where_to_buy: str | None = Field(
        default=None,
        description="Suggested retailers or sources for purchasing",
    )
    confidence: ConfidenceLevel = Field(
        description="How confident this recommendation is based on available documentation",
    )
    source_doc: str | None = Field(
        default=None,
        description="Source document supporting this recommendation. "
        "Required when confidence is CONFIRMED.",
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes, warnings, or installation tips. "
        "Include safety notes for gas/electrical parts.",
    )

    @model_validator(mode="after")
    def check_confidence_constraints(self) -> Self:
        """Enforce cross-field constraints based on confidence level.

        - CONFIRMED parts must have a source_doc reference.
        - UNCERTAIN parts must not have a part_number (can't be verified).
        """
        if self.confidence == ConfidenceLevel.CONFIRMED and not self.source_doc:
            raise ValueError("CONFIRMED parts must have a source_doc reference")
        if self.confidence == ConfidenceLevel.UNCERTAIN and self.part_number is not None:
            raise ValueError("UNCERTAIN parts must not have a part_number")
        return self


class ClarificationQuestion(BaseModel):
    """A question to ask the user for more specific part identification.

    Generated when the query is too vague or the device model is unknown.

    Example:
        {
            "id": "cq1",
            "question": "What is the model number of your furnace?",
            "reason": "Filter size depends on the specific furnace model",
            "related_device": "furnace"
        }
    """

    id: str = Field(description="Unique identifier for this question (e.g., 'cq1')")
    question: str = Field(description="The clarification question to ask the user")
    reason: str = Field(description="Why this information would help identify the correct part")
    related_device: str | None = Field(
        default=None,
        description="Which device this question relates to",
    )


# =============================================================================
# INSTRUCTOR RESPONSE MODEL
# =============================================================================


class PartsLookupResponse(BaseModel):
    """Structured LLM response for parts lookup.

    Used with instructor to get reliable structured output from the LLM.
    The LLM populates this based on retrieved documentation and the
    user's query.
    """

    parts: list[PartRecommendation] = Field(
        description="List of identified parts and consumables",
    )
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions to ask if information is insufficient for definitive answers",
    )
    summary: str = Field(
        description="Brief summary of findings and any gaps in information",
    )


# =============================================================================
# WORKFLOW STATE
# =============================================================================


class PartsHelperState(BaseModel):
    """State that flows through the parts helper workflow.

    This model holds all data as it passes through the graph nodes:
    1. parse_query sets: detected_devices (from query or profile)
    2. retrieve_docs sets: retrieved_chunks
    3. generate_parts_list sets: parts, clarification_questions, summary
    4. render_markdown sets: markdown_output

    All fields have defaults so nodes can return partial updates.
    """

    # --- Input ---
    query: str = Field(
        default="",
        description="The user's parts lookup query",
    )
    device_type: str | None = Field(
        default=None,
        description="Optional explicit device type filter from the user",
    )
    house_profile: HouseProfile | None = Field(
        default=None,
        description="The house profile with installed systems",
    )

    # --- Intermediate ---
    detected_devices: list[str] = Field(
        default_factory=list,
        description="Device types detected from query or profile",
    )
    retrieved_chunks: list[RetrievedChunk] = Field(
        default_factory=list,
        description="Chunks retrieved from RAG index",
    )

    # --- Output ---
    parts: list[PartRecommendation] = Field(
        default_factory=list,
        description="Identified parts and consumables",
    )
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions for the user if info is incomplete",
    )
    summary: str = Field(
        default="",
        description="Summary of findings",
    )
    markdown_output: str | None = Field(
        default=None,
        description="Final markdown-formatted parts list",
    )

    # --- Error tracking ---
    error: str | None = Field(
        default=None,
        description="Error message if something failed",
    )


# =============================================================================
# API REQUEST/RESPONSE MODELS
# =============================================================================


class PartsLookupRequest(BaseModel):
    """API request for parts lookup.

    This is the input to the POST /parts/lookup endpoint.
    """

    query: str = Field(
        min_length=1,
        max_length=2000,
        description="What parts or consumables to look up (e.g., 'What filter for the furnace?')",
    )
    device_type: str | None = Field(
        default=None,
        max_length=100,
        description="Optional device type to narrow the search (e.g., 'furnace')",
    )


class PartsLookupAPIResponse(BaseModel):
    """API response from parts lookup.

    Contains the identified parts, any clarification questions,
    and a formatted markdown output.
    """

    parts: list[PartRecommendation] = Field(
        description="Identified parts and consumables",
    )
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions for the user if info is incomplete",
    )
    summary: str = Field(
        description="Brief summary of findings",
    )
    markdown: str = Field(
        description="Formatted markdown output for display/export",
    )
    sources_used: list[str] = Field(
        default_factory=list,
        description="Source documents that informed the recommendations",
    )
    has_gaps: bool = Field(
        default=False,
        description="Whether there are information gaps (clarification questions present)",
    )
