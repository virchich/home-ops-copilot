"""Tests for the maintenance planner workflow.

These tests validate that the maintenance planner:
1. Generates plans for all 4 seasons
2. Produces reasonable numbers of checklist items
3. Includes appropriate priorities
4. Cites source documents
5. Generates valid markdown output

Note: These tests call the actual LLM and RAG index, so they are
marked as integration tests and may be slow/costly to run frequently.
"""

import pytest
from langgraph.graph.state import CompiledStateGraph

from app.workflows.maintenance_planner import create_maintenance_planner
from app.workflows.models import ChecklistItem, HouseProfile, Season, load_house_profile


@pytest.fixture
def house_profile() -> HouseProfile:
    """Load the house profile for testing."""
    return load_house_profile()


@pytest.fixture
def planner() -> CompiledStateGraph:
    """Create a compiled maintenance planner workflow."""
    return create_maintenance_planner()


class TestMaintenancePlannerIntegration:
    """Integration tests for the maintenance planner workflow.

    These tests exercise the full workflow including RAG retrieval
    and LLM generation. They are marked as integration tests.
    """

    @pytest.mark.integration
    def test_winter_plan_generates_items(
        self, planner: CompiledStateGraph, house_profile: HouseProfile
    ) -> None:
        """Winter plan should generate maintenance items."""
        result = planner.invoke(
            {
                "house_profile": house_profile,
                "season": Season.WINTER,
            }
        )

        items = result.get("checklist_items", [])
        assert len(items) > 0, "Should generate at least some checklist items"
        assert len(items) >= 5, "Winter should have at least 5 maintenance tasks"

    @pytest.mark.integration
    def test_plan_includes_priorities(
        self, planner: CompiledStateGraph, house_profile: HouseProfile
    ) -> None:
        """Generated plan should include items of different priorities."""
        result = planner.invoke(
            {
                "house_profile": house_profile,
                "season": Season.FALL,
            }
        )

        items = result.get("checklist_items", [])
        priorities = {item.priority for item in items}

        # Should have at least high priority items (safety-critical)
        assert "high" in priorities, "Should include high priority items"

    @pytest.mark.integration
    def test_plan_cites_sources(
        self, planner: CompiledStateGraph, house_profile: HouseProfile
    ) -> None:
        """Generated items should cite source documents."""
        result = planner.invoke(
            {
                "house_profile": house_profile,
                "season": Season.SPRING,
            }
        )

        items = result.get("checklist_items", [])
        items_with_sources = [item for item in items if item.source_doc]

        # At least half should cite sources
        assert len(items_with_sources) >= len(items) // 2, (
            "At least half of items should cite source documents"
        )

    @pytest.mark.integration
    def test_plan_generates_markdown(
        self, planner: CompiledStateGraph, house_profile: HouseProfile
    ) -> None:
        """Workflow should produce markdown output."""
        result = planner.invoke(
            {
                "house_profile": house_profile,
                "season": Season.SUMMER,
            }
        )

        markdown = result.get("markdown_output", "")
        assert markdown, "Should generate markdown output"
        assert "# " in markdown, "Markdown should have headers"
        assert "- [ ]" in markdown or "No maintenance tasks" in markdown, (
            "Markdown should have checkboxes or indicate no tasks"
        )


class TestMaintenancePlannerUnit:
    """Unit tests for maintenance planner components.

    These tests don't require the LLM or RAG index.
    """

    def test_checklist_item_model(self) -> None:
        """ChecklistItem should accept all expected fields."""
        item = ChecklistItem(
            task="Replace furnace filter",
            device_type="furnace",
            priority="high",
            frequency="monthly",
            estimated_time="5 minutes",
            notes="Use MERV 11 filter",
            source_doc="Furnace-OM9GFRC-02.pdf",
        )

        assert item.task == "Replace furnace filter"
        assert item.priority == "high"
        assert item.source_doc == "Furnace-OM9GFRC-02.pdf"

    def test_checklist_item_defaults(self) -> None:
        """ChecklistItem should have sensible defaults."""
        item = ChecklistItem(task="Test task")

        assert item.task == "Test task"
        assert item.priority == "medium"  # Default priority
        assert item.device_type is None
        assert item.source_doc is None

    def test_season_enum_values(self) -> None:
        """Season enum should have all four seasons."""
        seasons = [s.value for s in Season]
        assert "spring" in seasons
        assert "summer" in seasons
        assert "fall" in seasons
        assert "winter" in seasons

    def test_house_profile_loads(self, house_profile: HouseProfile) -> None:
        """House profile should load from default path."""
        assert house_profile is not None
        assert house_profile.name == "Main Residence"
        assert len(house_profile.systems) > 0

    def test_planner_compiles(self, planner: CompiledStateGraph) -> None:
        """Maintenance planner should compile without errors."""
        assert planner is not None
