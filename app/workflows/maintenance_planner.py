"""Seasonal Maintenance Planner Workflow.

This module implements a LangGraph workflow that generates seasonal
maintenance checklists based on a house profile and the current season.

Workflow structure:
    START → retrieve_docs → generate_checklist → render_markdown → END

Each node receives the full state and returns a partial update.
"""

import logging

import instructor
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.rag.retriever import retrieve
from app.workflows.models import ChecklistItem, MaintenancePlanState, RetrievedChunk, Season

logger = logging.getLogger(__name__)

# =============================================================================
# SEASON-SPECIFIC QUERY TEMPLATES
# =============================================================================
# These templates generate retrieval queries focused on seasonal tasks.
# Each device type gets a season-appropriate query.

SEASON_QUERY_TEMPLATES: dict[Season, str] = {
    Season.SPRING: "{device} spring maintenance checklist inspection cleaning",
    Season.SUMMER: "{device} summer maintenance cooling efficiency check",
    Season.FALL: "{device} fall winterization preparation maintenance checklist",
    Season.WINTER: "{device} winter maintenance heating efficiency check",
}

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

CHECKLIST_SYSTEM_PROMPT = """You are a home maintenance expert. Your job is to extract actionable maintenance tasks from equipment manuals and documentation.

Given documentation about home systems and a target season, generate a checklist of maintenance tasks.

RULES:
1. Only include tasks that are mentioned or implied in the provided documentation
2. Focus on tasks appropriate for the specified season
3. Be specific - include part numbers, filter sizes, settings when available
4. Prioritize safety-related tasks as "high" priority
5. Include the source document for each task
6. If a task involves gas, electrical, or structural work, note it requires a professional

OUTPUT FORMAT:
Return a list of maintenance tasks. Each task should include:
- task: Short, actionable description (e.g., "Replace furnace filter")
- device_type: Which system this relates to (e.g., "furnace", "hrv")
- priority: "high", "medium", or "low"
- frequency: How often to do this (e.g., "monthly", "annually")
- estimated_time: Rough time estimate (e.g., "5 minutes")
- notes: Specific details like part numbers, settings, warnings
- source_doc: The document this task came from
"""


class ChecklistResponse(BaseModel):
    """LLM response containing generated checklist items.

    This wrapper model is used with instructor to get structured output.
    """

    items: list[ChecklistItem] = Field(
        description="List of maintenance tasks extracted from the documentation"
    )


def get_llm_client() -> instructor.Instructor:
    """Get an instructor-patched OpenAI client."""
    return instructor.from_openai(OpenAI(api_key=settings.openai_api_key))

# =============================================================================
# NODE FUNCTIONS
# =============================================================================
# Each node receives the full state and returns a dict with fields to update.
# These are stub implementations - we'll add real logic in Phase 3.


def retrieve_docs(state: MaintenancePlanState) -> dict:
    """Retrieve relevant documents from the RAG index.

    This node queries the vector index filtered by:
    - Season (e.g., "winter maintenance", "fall preparation")
    - Device types from the house profile

    Strategy:
    1. Get device types from house profile
    2. Build metadata filters for those devices
    3. Generate a season-specific query
    4. Retrieve chunks with filtering
    5. Convert to RetrievedChunk format

    Args:
        state: Current workflow state with house_profile and season set.

    Returns:
        Dict with 'retrieved_chunks' to merge into state.
    """
    # Validate inputs
    if not state.house_profile or not state.season:
        logger.warning("Missing house_profile or season in state")
        return {"retrieved_chunks": [], "error": "Missing house_profile or season"}

    # Get device types from house profile
    device_types = list(state.house_profile.systems.keys())
    logger.info(f"Retrieving docs for season={state.season.value}, devices={device_types}")

    # Build season-specific query
    # We create a general query that covers maintenance for the season
    query_template = SEASON_QUERY_TEMPLATES.get(
        state.season,
        "{device} maintenance checklist"
    )

    # Create a combined query mentioning key devices
    # This helps retrieve relevant docs across all installed systems
    device_terms = " ".join(device_types[:3])  # Use first 3 to avoid too long query
    query = query_template.format(device=device_terms)
    logger.info(f"Retrieval query: {query}")

    # Retrieve with metadata filtering by house profile devices
    # Use fewer chunks to keep context size manageable for LLM
    try:
        nodes = retrieve(
            question=query,
            top_k=5,  # Balance between coverage and context size
            auto_filter=False,  # Don't auto-detect from question
            device_types=device_types,  # Filter by house profile devices
        )
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {"retrieved_chunks": [], "error": str(e)}

    # Convert NodeWithScore to RetrievedChunk
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


def generate_checklist(state: MaintenancePlanState) -> dict:
    """Generate checklist items from retrieved documents.

    This node calls the LLM with:
    - Retrieved document chunks as context
    - House profile (to know what systems exist)
    - Season (to focus on relevant tasks)

    The LLM returns structured ChecklistItem objects via instructor.

    Args:
        state: Current workflow state with retrieved_chunks populated.

    Returns:
        Dict with 'checklist_items' to merge into state.
    """
    # Check prerequisites
    if not state.retrieved_chunks:
        logger.warning("No retrieved chunks to generate checklist from")
        return {"checklist_items": []}

    if not state.season or not state.house_profile:
        logger.warning("Missing season or house_profile")
        return {"checklist_items": [], "error": "Missing season or house_profile"}

    logger.info(f"Generating checklist from {len(state.retrieved_chunks)} chunks")

    # Format retrieved chunks as context for the LLM
    context_parts = []
    for i, chunk in enumerate(state.retrieved_chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk.source} ({chunk.device_type or 'general'})]\n{chunk.text}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Build list of installed systems for context
    systems_list = ", ".join(state.house_profile.systems.keys())

    # Build the user message
    user_message = f"""Season: {state.season.value.upper()}

Installed systems in this house: {systems_list}

Documentation excerpts:
{context}

Based on the documentation above, generate a {state.season.value} maintenance checklist for this house.
Focus on tasks that are relevant for {state.season.value} and the installed systems."""

    # Call LLM with structured output
    # Use higher max_completion_tokens since checklist generation needs more space
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.llm.model,
            messages=[
                {"role": "system", "content": CHECKLIST_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_model=ChecklistResponse,
            temperature=0.3,  # Lower temperature for more consistent output
            max_completion_tokens=4000,  # Higher limit for detailed checklist
        )

        checklist_items = response.items
        logger.info(f"Generated {len(checklist_items)} checklist items")

        return {"checklist_items": checklist_items}

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {"checklist_items": [], "error": str(e)}


def render_markdown(state: MaintenancePlanState) -> dict:
    """Render checklist items as Apple Notes-friendly markdown.

    This node converts the structured checklist into a formatted
    markdown document that can be copy-pasted into Apple Notes.

    Formatting:
    - Groups tasks by priority (High → Medium → Low)
    - Uses checkboxes (- [ ]) for each task
    - Includes notes and frequency inline
    - Lists all source documents at the end

    Args:
        state: Current workflow state with checklist_items populated.

    Returns:
        Dict with 'markdown_output' to merge into state.
    """
    season_name = state.season.value.title() if state.season else "Unknown"
    house_name = state.house_profile.name if state.house_profile else "Unknown House"

    # Start building markdown
    lines = [
        f"# {season_name} Maintenance Plan",
        f"**{house_name}**",
        "",
    ]

    # Handle empty checklist
    if not state.checklist_items:
        lines.extend([
            "No maintenance tasks generated.",
            "",
            "---",
            "*No sources used*",
        ])
        markdown = "\n".join(lines)
        logger.info(f"Generated markdown ({len(markdown)} chars) - empty checklist")
        return {"markdown_output": markdown}

    # Group items by priority
    high_priority = [item for item in state.checklist_items if item.priority == "high"]
    medium_priority = [item for item in state.checklist_items if item.priority == "medium"]
    low_priority = [item for item in state.checklist_items if item.priority == "low"]

    # Render each priority group
    def render_task(item: ChecklistItem) -> list[str]:
        """Render a single task as markdown lines."""
        task_lines = [f"- [ ] **{item.task}**"]

        # Add details on the same checkbox item
        details = []
        if item.device_type:
            details.append(f"*{item.device_type}*")
        if item.frequency:
            details.append(f"({item.frequency})")

        if details:
            task_lines[0] += " — " + " ".join(details)

        # Add notes as sub-item if present
        if item.notes:
            # Truncate long notes
            notes = item.notes if len(item.notes) <= 150 else item.notes[:147] + "..."
            task_lines.append(f"  - {notes}")

        return task_lines

    # High priority tasks
    if high_priority:
        lines.append("## High Priority")
        lines.append("")
        for item in high_priority:
            lines.extend(render_task(item))
        lines.append("")

    # Medium priority tasks
    if medium_priority:
        lines.append("## Medium Priority")
        lines.append("")
        for item in medium_priority:
            lines.extend(render_task(item))
        lines.append("")

    # Low priority tasks
    if low_priority:
        lines.append("## Low Priority")
        lines.append("")
        for item in low_priority:
            lines.extend(render_task(item))
        lines.append("")

    # Collect unique sources
    sources = sorted({
        item.source_doc
        for item in state.checklist_items
        if item.source_doc
    })

    # Add sources section
    lines.append("---")
    if sources:
        lines.append(f"*Sources: {', '.join(sources)}*")
    else:
        lines.append("*No sources cited*")

    markdown = "\n".join(lines)
    logger.info(f"Generated markdown ({len(markdown)} chars)")

    return {"markdown_output": markdown}


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================


def build_maintenance_planner_graph() -> StateGraph:
    """Build the maintenance planner workflow graph.

    This function constructs the LangGraph StateGraph with:
    - Three nodes: retrieve_docs, generate_checklist, render_markdown
    - Linear flow: START → retrieve → generate → render → END

    Returns:
        Configured StateGraph (not yet compiled).

    Example:
        >>> graph = build_maintenance_planner_graph()
        >>> workflow = graph.compile()
        >>> result = workflow.invoke(initial_state)
    """
    # Create the graph with our state schema
    graph = StateGraph(MaintenancePlanState)

    # Add nodes
    # Each node is a function that takes state and returns partial updates
    graph.add_node("retrieve_docs", retrieve_docs)
    graph.add_node("generate_checklist", generate_checklist)
    graph.add_node("render_markdown", render_markdown)

    # Add edges (define the flow)
    # START is a special node that marks the entry point
    graph.add_edge(START, "retrieve_docs")
    graph.add_edge("retrieve_docs", "generate_checklist")
    graph.add_edge("generate_checklist", "render_markdown")
    graph.add_edge("render_markdown", END)

    return graph


def create_maintenance_planner() -> CompiledStateGraph:
    """Create a compiled maintenance planner workflow.

    This is a convenience function that builds and compiles the graph
    in one step. The compiled workflow can be invoked with initial state.

    Returns:
        Compiled workflow ready for invocation.

    Example:
        >>> planner = create_maintenance_planner()
        >>> result = planner.invoke({
        ...     "house_profile": profile,
        ...     "season": Season.WINTER
        ... })
        >>> print(result["markdown_output"])
    """
    graph = build_maintenance_planner_graph()
    return graph.compile()
