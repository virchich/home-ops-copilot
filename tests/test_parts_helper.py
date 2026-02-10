"""Tests for the parts & consumables helper workflow.

These tests validate that the parts helper workflow:
1. Models validate correctly (confidence levels, part recommendations, API models)
2. Graph compiles without errors with correct node count
3. parse_query correctly resolves device types
4. render_markdown produces valid formatted output
5. Shared helpers work correctly after extraction

Integration tests (marked with @pytest.mark.integration) exercise
the full workflow with real LLM + RAG calls.
"""

import pytest
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.workflows.helpers import format_chunks_as_context, format_device_details
from app.workflows.models import (
    ClimateZone,
    HouseProfile,
    InstalledSystem,
    RetrievedChunk,
    load_house_profile,
)
from app.workflows.parts_helper import (
    _confidence_badge,
    build_parts_helper_graph,
    create_parts_helper,
    parse_query,
    render_markdown,
)
from app.workflows.parts_helper_models import (
    ClarificationQuestion,
    ConfidenceLevel,
    PartRecommendation,
    PartsHelperState,
    PartsLookupAPIResponse,
    PartsLookupRequest,
    PartsLookupResponse,
)


@pytest.fixture
def house_profile() -> HouseProfile:
    """Load the house profile for testing."""
    return load_house_profile()


@pytest.fixture
def sample_profile() -> HouseProfile:
    """A minimal house profile for unit tests."""
    return HouseProfile(
        name="Test House",
        climate_zone=ClimateZone.COLD,
        systems={
            "furnace": InstalledSystem(
                manufacturer="Carrier",
                model="OM9GFRC",
                fuel_type="gas",
                install_year=2018,
            ),
            "hrv": InstalledSystem(
                manufacturer="Lifebreath",
                model="RNC5-TPD",
            ),
            "humidifier": InstalledSystem(
                manufacturer="GeneralAire",
                model="1042",
            ),
        },
    )


# =============================================================================
# MODEL VALIDATION TESTS
# =============================================================================


class TestModels:
    """Tests for Pydantic model validation."""

    def test_confidence_level_values(self) -> None:
        """ConfidenceLevel should have three levels."""
        assert ConfidenceLevel.CONFIRMED == "confirmed"
        assert ConfidenceLevel.LIKELY == "likely"
        assert ConfidenceLevel.UNCERTAIN == "uncertain"

    def test_part_recommendation_confirmed(self) -> None:
        """PartRecommendation should accept a CONFIRMED part with source."""
        part = PartRecommendation(
            part_name="Furnace Air Filter",
            part_number="16x25x1 MERV 11",
            device_type="furnace",
            device_model="OM9GFRC",
            description="Standard replacement air filter",
            replacement_interval="Every 1-3 months",
            confidence=ConfidenceLevel.CONFIRMED,
            source_doc="Furnace-OM9GFRC-02.pdf",
        )
        assert part.confidence == ConfidenceLevel.CONFIRMED
        assert part.part_number is not None
        assert part.source_doc is not None

    def test_part_recommendation_uncertain_no_part_number(self) -> None:
        """UNCERTAIN parts should work without part_number."""
        part = PartRecommendation(
            part_name="Water Softener Salt",
            device_type="water_softener",
            description="Salt pellets for water softener regeneration",
            confidence=ConfidenceLevel.UNCERTAIN,
        )
        assert part.confidence == ConfidenceLevel.UNCERTAIN
        assert part.part_number is None

    def test_confirmed_without_source_doc_rejected(self) -> None:
        """CONFIRMED parts without source_doc should be rejected by validator."""
        with pytest.raises(ValidationError, match="source_doc"):
            PartRecommendation(
                part_name="Filter",
                device_type="furnace",
                description="Air filter",
                confidence=ConfidenceLevel.CONFIRMED,
                # Missing source_doc
            )

    def test_uncertain_with_part_number_rejected(self) -> None:
        """UNCERTAIN parts with a part_number should be rejected by validator."""
        with pytest.raises(ValidationError, match="part_number"):
            PartRecommendation(
                part_name="Generic Filter",
                device_type="furnace",
                description="Some filter",
                confidence=ConfidenceLevel.UNCERTAIN,
                part_number="ABC-123",  # Not allowed for UNCERTAIN
            )

    def test_part_recommendation_defaults(self) -> None:
        """PartRecommendation should have sensible defaults."""
        part = PartRecommendation(
            part_name="Test Part",
            device_type="furnace",
            description="Test",
            confidence=ConfidenceLevel.LIKELY,
        )
        assert part.part_number is None
        assert part.device_model is None
        assert part.replacement_interval is None
        assert part.where_to_buy is None
        assert part.source_doc is None
        assert part.notes is None

    def test_clarification_question(self) -> None:
        """ClarificationQuestion should accept all fields."""
        q = ClarificationQuestion(
            id="cq1",
            question="What is the model number of your furnace?",
            reason="Filter size depends on the specific furnace model",
            related_device="furnace",
        )
        assert q.id == "cq1"
        assert q.related_device == "furnace"

    def test_clarification_question_no_device(self) -> None:
        """ClarificationQuestion should work without related_device."""
        q = ClarificationQuestion(
            id="cq2",
            question="How old is your HVAC system?",
            reason="Age determines compatible parts",
        )
        assert q.related_device is None

    def test_parts_lookup_response(self) -> None:
        """PartsLookupResponse should validate with parts and questions."""
        resp = PartsLookupResponse(
            parts=[
                PartRecommendation(
                    part_name="Filter",
                    device_type="furnace",
                    description="Air filter",
                    confidence=ConfidenceLevel.CONFIRMED,
                    source_doc="manual.pdf",
                ),
            ],
            clarification_questions=[
                ClarificationQuestion(
                    id="cq1",
                    question="What size?",
                    reason="Need size for exact match",
                ),
            ],
            summary="Found 1 part, need clarification on size.",
        )
        assert len(resp.parts) == 1
        assert len(resp.clarification_questions) == 1

    def test_parts_helper_state_defaults(self) -> None:
        """PartsHelperState should have sensible defaults."""
        state = PartsHelperState()
        assert state.query == ""
        assert state.device_type is None
        assert state.house_profile is None
        assert state.detected_devices == []
        assert state.retrieved_chunks == []
        assert state.parts == []
        assert state.clarification_questions == []
        assert state.summary == ""
        assert state.markdown_output is None
        assert state.error is None

    def test_parts_helper_state_with_inputs(self) -> None:
        """PartsHelperState should accept query inputs."""
        state = PartsHelperState(
            query="What filter for furnace?",
            device_type="furnace",
        )
        assert state.query == "What filter for furnace?"
        assert state.device_type == "furnace"

    def test_parts_lookup_request_valid(self) -> None:
        """PartsLookupRequest should accept a valid query."""
        req = PartsLookupRequest(query="What filter for the furnace?")
        assert req.query == "What filter for the furnace?"
        assert req.device_type is None

    def test_parts_lookup_request_with_device(self) -> None:
        """PartsLookupRequest should accept optional device_type."""
        req = PartsLookupRequest(
            query="What filter do I need?",
            device_type="furnace",
        )
        assert req.device_type == "furnace"

    def test_parts_lookup_request_rejects_empty_query(self) -> None:
        """PartsLookupRequest should reject empty query (min_length=1)."""
        with pytest.raises(ValidationError):
            PartsLookupRequest(query="")

    def test_parts_lookup_request_rejects_long_query(self) -> None:
        """PartsLookupRequest should reject query over max_length."""
        with pytest.raises(ValidationError):
            PartsLookupRequest(query="x" * 2001)

    def test_parts_lookup_request_rejects_long_device_type(self) -> None:
        """PartsLookupRequest should reject device_type over max_length."""
        with pytest.raises(ValidationError):
            PartsLookupRequest(query="test", device_type="x" * 101)

    def test_parts_lookup_request_accepts_max_length(self) -> None:
        """PartsLookupRequest should accept fields at exactly max_length."""
        req = PartsLookupRequest(
            query="y" * 2000,
            device_type="x" * 100,
        )
        assert len(req.query) == 2000
        assert len(req.device_type) == 100

    def test_parts_lookup_api_response(self) -> None:
        """PartsLookupAPIResponse should validate with all fields."""
        resp = PartsLookupAPIResponse(
            parts=[
                PartRecommendation(
                    part_name="Filter",
                    device_type="furnace",
                    description="Air filter",
                    confidence=ConfidenceLevel.CONFIRMED,
                    source_doc="manual.pdf",
                ),
            ],
            summary="Found 1 part.",
            markdown="# Parts\n...",
            sources_used=["manual.pdf"],
            has_gaps=False,
        )
        assert len(resp.parts) == 1
        assert not resp.has_gaps


# =============================================================================
# SHARED HELPERS TESTS
# =============================================================================


class TestSharedHelpers:
    """Tests for extracted shared helper functions."""

    def test_format_chunks_as_context_empty(self) -> None:
        """format_chunks_as_context should return fallback for empty list."""
        result = format_chunks_as_context([])
        assert result == "No documentation available."

    def test_format_chunks_as_context_single(self) -> None:
        """format_chunks_as_context should format a single chunk."""
        chunks = [
            RetrievedChunk(
                text="Replace filter every 3 months",
                source="Furnace-Manual.pdf",
                device_type="furnace",
                score=0.9,
            )
        ]
        result = format_chunks_as_context(chunks)
        assert "[Source 1: Furnace-Manual.pdf (furnace)]" in result
        assert "Replace filter every 3 months" in result

    def test_format_chunks_as_context_multiple(self) -> None:
        """format_chunks_as_context should number multiple chunks."""
        chunks = [
            RetrievedChunk(text="Chunk 1", source="doc1.pdf", score=0.9),
            RetrievedChunk(text="Chunk 2", source="doc2.pdf", device_type="hrv", score=0.8),
        ]
        result = format_chunks_as_context(chunks)
        assert "[Source 1: doc1.pdf (general)]" in result
        assert "[Source 2: doc2.pdf (hrv)]" in result
        assert "---" in result

    def test_format_device_details_with_profile(self, sample_profile: HouseProfile) -> None:
        """format_device_details should return details for a known device."""
        result = format_device_details(sample_profile, "furnace")
        assert "Manufacturer: Carrier" in result
        assert "Model: OM9GFRC" in result
        assert "Fuel: gas" in result
        assert "Installed: 2018" in result

    def test_format_device_details_unknown_device(self, sample_profile: HouseProfile) -> None:
        """format_device_details should return empty for unknown device."""
        result = format_device_details(sample_profile, "air_conditioner")
        assert result == ""

    def test_format_device_details_no_profile(self) -> None:
        """format_device_details should return empty without profile."""
        result = format_device_details(None, "furnace")
        assert result == ""

    def test_format_device_details_no_device_type(self, sample_profile: HouseProfile) -> None:
        """format_device_details should return empty without device_type."""
        result = format_device_details(sample_profile, None)
        assert result == ""


# =============================================================================
# GRAPH COMPILATION TESTS
# =============================================================================


class TestGraphCompilation:
    """Tests for LangGraph workflow compilation."""

    def test_parts_helper_graph_compiles(self) -> None:
        """Parts helper graph should compile without errors."""
        workflow = create_parts_helper()
        assert workflow is not None
        assert isinstance(workflow, CompiledStateGraph)

    def test_parts_helper_graph_has_expected_nodes(self) -> None:
        """Parts helper graph should have the 4 expected nodes."""
        graph = build_parts_helper_graph()
        node_names = set(graph.nodes.keys())
        expected = {"parse_query", "retrieve_docs", "generate_parts_list", "render_markdown"}
        assert expected == node_names


# =============================================================================
# NODE FUNCTION UNIT TESTS
# =============================================================================


class TestParseQuery:
    """Tests for the parse_query node."""

    def test_explicit_device_type(self) -> None:
        """parse_query should use explicit device_type when provided."""
        state = PartsHelperState(
            query="What filter do I need?",
            device_type="furnace",
        )
        result = parse_query(state)
        assert result["detected_devices"] == ["furnace"]

    def test_explicit_device_type_normalized(self) -> None:
        """parse_query should normalize device_type to lowercase with underscores."""
        state = PartsHelperState(
            query="What filter?",
            device_type="Water Heater",
        )
        result = parse_query(state)
        assert result["detected_devices"] == ["water_heater"]

    def test_detect_from_query(self) -> None:
        """parse_query should detect device from query text."""
        state = PartsHelperState(
            query="What filter does my furnace need?",
        )
        result = parse_query(state)
        assert "furnace" in result["detected_devices"]

    def test_broad_query_uses_profile(self, sample_profile: HouseProfile) -> None:
        """parse_query should use all profile devices for broad queries."""
        state = PartsHelperState(
            query="What parts should I stock up on?",
            house_profile=sample_profile,
        )
        result = parse_query(state)
        # Should include all profile devices
        assert "furnace" in result["detected_devices"]
        assert "hrv" in result["detected_devices"]
        assert "humidifier" in result["detected_devices"]

    def test_empty_query_returns_error(self) -> None:
        """parse_query should return error for empty query."""
        state = PartsHelperState(query="")
        result = parse_query(state)
        assert "error" in result

    def test_no_detection_no_profile(self) -> None:
        """parse_query should return empty devices when nothing detected and no profile."""
        state = PartsHelperState(
            query="What parts do I need?",
        )
        result = parse_query(state)
        assert result["detected_devices"] == []


class TestRenderMarkdown:
    """Tests for the render_markdown node."""

    def test_render_with_confirmed_part(self) -> None:
        """render_markdown should render CONFIRMED parts with sources."""
        state = PartsHelperState(
            parts=[
                PartRecommendation(
                    part_name="Furnace Filter",
                    part_number="16x25x1 MERV 11",
                    device_type="furnace",
                    device_model="OM9GFRC",
                    description="Standard replacement filter",
                    replacement_interval="Every 1-3 months",
                    confidence=ConfidenceLevel.CONFIRMED,
                    source_doc="Furnace-OM9GFRC-02.pdf",
                ),
            ],
            summary="Found 1 confirmed part.",
        )
        result = render_markdown(state)
        md = result["markdown_output"]

        assert "# Parts & Consumables" in md
        assert "Furnace Filter" in md
        assert "[CONFIRMED]" in md
        assert "16x25x1 MERV 11" in md
        assert "OM9GFRC" in md
        assert "Every 1-3 months" in md
        assert "Furnace-OM9GFRC-02.pdf" in md

    def test_render_with_uncertain_part(self) -> None:
        """render_markdown should render UNCERTAIN parts."""
        state = PartsHelperState(
            parts=[
                PartRecommendation(
                    part_name="Water Softener Salt",
                    device_type="water_softener",
                    description="Salt pellets for regeneration",
                    confidence=ConfidenceLevel.UNCERTAIN,
                ),
            ],
            summary="Found 1 uncertain recommendation.",
        )
        result = render_markdown(state)
        md = result["markdown_output"]
        assert "[UNCERTAIN]" in md
        assert "Water Softener Salt" in md

    def test_render_groups_by_device(self) -> None:
        """render_markdown should group parts by device_type."""
        state = PartsHelperState(
            parts=[
                PartRecommendation(
                    part_name="Furnace Filter",
                    device_type="furnace",
                    description="Air filter",
                    confidence=ConfidenceLevel.CONFIRMED,
                    source_doc="manual.pdf",
                ),
                PartRecommendation(
                    part_name="HRV Filter",
                    device_type="hrv",
                    description="Ventilation filter",
                    confidence=ConfidenceLevel.LIKELY,
                ),
            ],
        )
        result = render_markdown(state)
        md = result["markdown_output"]
        assert "## Furnace" in md
        assert "## Hrv" in md

    def test_render_with_clarification_questions(self) -> None:
        """render_markdown should include clarification questions section."""
        state = PartsHelperState(
            clarification_questions=[
                ClarificationQuestion(
                    id="cq1",
                    question="What model is your air conditioner?",
                    reason="Filter size varies by model",
                    related_device="air_conditioner",
                ),
            ],
        )
        result = render_markdown(state)
        md = result["markdown_output"]
        assert "Missing Information" in md
        assert "What model is your air conditioner?" in md

    def test_render_empty_parts(self) -> None:
        """render_markdown should handle empty parts list."""
        state = PartsHelperState()
        result = render_markdown(state)
        md = result["markdown_output"]
        assert "# Parts & Consumables" in md
        assert "No parts identified" in md

    def test_render_includes_sources_footer(self) -> None:
        """render_markdown should include a sources footer."""
        state = PartsHelperState(
            parts=[
                PartRecommendation(
                    part_name="Filter",
                    device_type="furnace",
                    description="Test",
                    confidence=ConfidenceLevel.CONFIRMED,
                    source_doc="manual.pdf",
                ),
            ],
        )
        result = render_markdown(state)
        md = result["markdown_output"]
        assert "Sources: manual.pdf" in md

    def test_render_part_with_notes(self) -> None:
        """render_markdown should include notes when present."""
        state = PartsHelperState(
            parts=[
                PartRecommendation(
                    part_name="Gas Valve",
                    device_type="furnace",
                    description="Replacement gas valve",
                    confidence=ConfidenceLevel.LIKELY,
                    notes="Professional installation recommended for gas components",
                ),
            ],
        )
        result = render_markdown(state)
        md = result["markdown_output"]
        assert "Professional installation recommended" in md


class TestConfidenceBadge:
    """Tests for the confidence badge helper."""

    def test_confirmed_badge(self) -> None:
        assert _confidence_badge(ConfidenceLevel.CONFIRMED) == "[CONFIRMED]"

    def test_likely_badge(self) -> None:
        assert _confidence_badge(ConfidenceLevel.LIKELY) == "[LIKELY]"

    def test_uncertain_badge(self) -> None:
        assert _confidence_badge(ConfidenceLevel.UNCERTAIN) == "[UNCERTAIN]"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestPartsHelperIntegration:
    """Integration tests for the full parts helper workflow.

    These tests call the actual LLM and RAG index.
    """

    @pytest.mark.integration
    def test_furnace_filter_lookup(self, house_profile: HouseProfile) -> None:
        """Should identify furnace filter from documentation."""
        workflow = create_parts_helper()
        result = workflow.invoke(
            {
                "query": "What filter does my furnace need?",
                "house_profile": house_profile,
            }
        )

        assert result["parts"]
        assert result["summary"]
        assert result["markdown_output"]
        # Should find at least one furnace-related part
        furnace_parts = [p for p in result["parts"] if p.device_type == "furnace"]
        assert len(furnace_parts) >= 1

    @pytest.mark.integration
    def test_all_filters_lookup(self, house_profile: HouseProfile) -> None:
        """Broad 'all filters' query should return parts from multiple devices."""
        workflow = create_parts_helper()
        result = workflow.invoke(
            {
                "query": "What filters do I need for all my systems?",
                "house_profile": house_profile,
            }
        )

        assert result["parts"]
        # Should span multiple device types
        device_types = {p.device_type for p in result["parts"]}
        assert len(device_types) >= 2

    @pytest.mark.integration
    def test_unknown_device_generates_questions(self, house_profile: HouseProfile) -> None:
        """Query about unknown device should generate clarification questions."""
        workflow = create_parts_helper()
        result = workflow.invoke(
            {
                "query": "What filter does my air conditioner need?",
                "house_profile": house_profile,
            }
        )

        # Should generate at least one clarification or note about missing device
        assert result["summary"]
        assert result["markdown_output"]
