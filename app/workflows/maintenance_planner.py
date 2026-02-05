"""Seasonal Maintenance Planner Workflow.

This module implements a LangGraph workflow that generates seasonal
maintenance checklists based on a house profile and the current season.

Workflow structure:
    START → retrieve_docs → generate_checklist → render_markdown → END

Each node receives the full state and returns a partial update.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.workflows.models import MaintenancePlanState

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

    Args:
        state: Current workflow state with house_profile and season set.

    Returns:
        Dict with 'retrieved_chunks' to merge into state.

    TODO (Phase 3):
        - Build season-specific queries
        - Filter by device types in house profile
        - Call the actual retriever
    """
    # Stub: Return empty list for now
    # In Phase 3, we'll query the actual RAG index
    print(f"[retrieve_docs] Season: {state.season}, Systems: {len(state.house_profile.systems) if state.house_profile else 0}")

    return {"retrieved_chunks": []}


def generate_checklist(state: MaintenancePlanState) -> dict:
    """Generate checklist items from retrieved documents.

    This node calls the LLM with:
    - Retrieved document chunks as context
    - House profile (to know what systems exist)
    - Season (to focus on relevant tasks)

    The LLM returns structured ChecklistItem objects.

    Args:
        state: Current workflow state with retrieved_chunks populated.

    Returns:
        Dict with 'checklist_items' to merge into state.

    TODO (Phase 3):
        - Build prompt with context and instructions
        - Use instructor for structured output
        - Validate items against house profile
    """
    # Stub: Return empty list for now
    # In Phase 3, we'll call the LLM with instructor
    print(f"[generate_checklist] Retrieved chunks: {len(state.retrieved_chunks)}")

    return {"checklist_items": []}


def render_markdown(state: MaintenancePlanState) -> dict:
    """Render checklist items as Apple Notes-friendly markdown.

    This node converts the structured checklist into a formatted
    markdown document that can be copy-pasted into Apple Notes.

    Args:
        state: Current workflow state with checklist_items populated.

    Returns:
        Dict with 'markdown_output' to merge into state.

    TODO (Phase 3):
        - Group items by device type or priority
        - Add checkboxes (- [ ])
        - Include source citations
    """
    # Stub: Return placeholder markdown
    # In Phase 3, we'll implement proper formatting
    season_name = state.season.value.title() if state.season else "Unknown"
    house_name = state.house_profile.name if state.house_profile else "Unknown House"

    markdown = f"""# {season_name} Maintenance Plan
## {house_name}

*Generated maintenance checklist*

### Tasks

- [ ] (No tasks generated yet - placeholder)

---
*Sources: None*
"""

    print(f"[render_markdown] Generated markdown ({len(markdown)} chars)")

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
