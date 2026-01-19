"""Query engine for RAG-based question answering.

This module orchestrates the RAG pipeline:
1. Retrieve relevant documents (Phase 2+)
2. Generate answer using LLM with retrieved context
3. Return structured response with citations

Uses the `instructor` library for structured, Pydantic-validated LLM outputs.
"""

from functools import lru_cache

import instructor
from openai import OpenAI

from app.core.config import settings
from app.rag.models import Citation, LLMResponse, QueryResponse, RiskLevel


# =============================================================================
# LLM CLIENT (SINGLETON)
# =============================================================================
# Create the client once and reuse it across requests.
# This avoids the overhead of creating a new client per request.


@lru_cache(maxsize=1)
def get_llm_client() -> instructor.Instructor:
    """
    Get a cached instructor-patched OpenAI client.

    The client is created once and reused for all subsequent calls.
    This is more efficient than creating a new client per request.

    Returns:
        instructor.Instructor: OpenAI client with instructor patching
    """
    return instructor.from_openai(OpenAI(api_key=settings.openai_api_key))


# =============================================================================
# SYSTEM PROMPT
# =============================================================================


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

    This is the main entry point for the RAG pipeline. It:
    1. Retrieves relevant documents (TODO: Phase 2)
    2. Calls the LLM with context
    3. Returns a structured response with citations

    Args:
        question: The user's question about home maintenance.

    Returns:
        QueryResponse with answer, citations, risk level, and contexts.
    """
    # Get cached LLM client
    client = get_llm_client()

    # TODO: Phase 2 - Add retrieval step here
    # retrieved_nodes = retrieve(question)
    # context = format_contexts_for_llm(retrieved_nodes)
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
        response_model=LLMResponse,
        temperature=settings.llm.temperature,
        max_completion_tokens=settings.llm.max_completion_tokens,
    )

    # TODO: Phase 2 - Extract citations from retrieved docs
    # For now, LLM returns empty citations since no context provided
    citations: list[Citation] = llm_response.citations

    return QueryResponse(
        answer=llm_response.answer,
        citations=citations,
        risk_level=RiskLevel(llm_response.risk_level),
        contexts=contexts,
    )
