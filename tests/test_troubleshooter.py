"""Tests for the troubleshooting workflow.

These tests validate that the troubleshooting workflow:
1. Models validate correctly
2. Graphs compile without errors
3. Safety patterns detect high-risk keywords
4. Router function routes correctly based on state
5. Intake parse normalizes device types
6. Render output produces valid markdown

Integration tests (marked with @pytest.mark.integration) exercise
the full workflow with real LLM + RAG calls.
"""

import pytest
from langgraph.graph.state import CompiledStateGraph

from app.rag.models import RiskLevel
from app.workflows.models import HouseProfile, load_house_profile
from app.workflows.troubleshooter import (
    SAFETY_STOP_PATTERNS,
    build_diagnosis_graph,
    build_intake_graph,
    check_safety_patterns,
    create_diagnosis_workflow,
    create_intake_workflow,
    intake_parse,
    render_output,
    risk_router,
    safety_stop,
)
from app.workflows.troubleshooter_models import (
    DiagnosisResponse,
    DiagnosticStep,
    FollowupAnswer,
    FollowupGenerationResponse,
    FollowupQuestion,
    QuestionType,
    TroubleshootDiagnoseRequest,
    TroubleshootDiagnoseResponse,
    TroubleshootingState,
    TroubleshootPhase,
    TroubleshootStartRequest,
    TroubleshootStartResponse,
)


@pytest.fixture
def house_profile() -> HouseProfile:
    """Load the house profile for testing."""
    return load_house_profile()


# =============================================================================
# MODEL VALIDATION TESTS
# =============================================================================


class TestModels:
    """Tests for Pydantic model validation."""

    def test_followup_question_yes_no(self) -> None:
        """FollowupQuestion should accept yes_no type."""
        q = FollowupQuestion(
            id="q1",
            question="Is the pilot light visible?",
            question_type=QuestionType.YES_NO,
            why="Determines if ignition system is the issue",
        )
        assert q.id == "q1"
        assert q.question_type == QuestionType.YES_NO
        assert q.options is None

    def test_followup_question_multiple_choice(self) -> None:
        """FollowupQuestion should accept multiple_choice with options."""
        q = FollowupQuestion(
            id="q2",
            question="What color is the indicator light?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            options=["Green", "Red", "Blinking", "Off"],
            why="Indicator color maps to specific error codes",
        )
        assert q.question_type == QuestionType.MULTIPLE_CHOICE
        assert q.options is not None
        assert len(q.options) == 4

    def test_followup_question_free_text(self) -> None:
        """FollowupQuestion should accept free_text type."""
        q = FollowupQuestion(
            id="q3",
            question="Describe the sound the furnace makes",
            question_type=QuestionType.FREE_TEXT,
            why="Sound type helps identify mechanical vs electrical issue",
        )
        assert q.question_type == QuestionType.FREE_TEXT

    def test_followup_answer(self) -> None:
        """FollowupAnswer should accept question_id and answer."""
        a = FollowupAnswer(question_id="q1", answer="No, the pilot light is not visible")
        assert a.question_id == "q1"
        assert "pilot light" in a.answer

    def test_diagnostic_step_full(self) -> None:
        """DiagnosticStep should accept all fields."""
        step = DiagnosticStep(
            step_number=1,
            instruction="Check thermostat is set to HEAT mode",
            expected_outcome="Display shows HEAT and set temperature",
            if_not_resolved="Move to step 2",
            risk_level=RiskLevel.LOW,
            source_doc="Furnace-OM9GFRC-02.pdf",
            requires_professional=False,
        )
        assert step.step_number == 1
        assert step.risk_level == RiskLevel.LOW
        assert not step.requires_professional

    def test_diagnostic_step_high_risk(self) -> None:
        """DiagnosticStep should flag professional-required steps."""
        step = DiagnosticStep(
            step_number=5,
            instruction="Call a licensed HVAC technician to inspect the gas valve",
            expected_outcome="Professional diagnoses and repairs gas valve",
            if_not_resolved="The technician will advise next steps",
            risk_level=RiskLevel.HIGH,
            source_doc=None,
            requires_professional=True,
        )
        assert step.risk_level == RiskLevel.HIGH
        assert step.requires_professional

    def test_diagnostic_step_defaults(self) -> None:
        """DiagnosticStep should have sensible defaults."""
        step = DiagnosticStep(
            step_number=1,
            instruction="Check filter",
            expected_outcome="Filter is clean",
            if_not_resolved="Replace filter",
            risk_level=RiskLevel.LOW,
        )
        assert step.source_doc is None
        assert not step.requires_professional

    def test_troubleshooting_state_defaults(self) -> None:
        """TroubleshootingState should have sensible defaults for all fields."""
        state = TroubleshootingState()
        assert state.device_type is None
        assert state.symptom is None
        assert state.phase == TroubleshootPhase.INTAKE
        assert state.is_safety_stop is False
        assert state.retrieved_chunks == []
        assert state.followup_questions == []
        assert state.followup_answers == []
        assert state.diagnostic_steps == []
        assert state.error is None

    def test_troubleshooting_state_with_inputs(self) -> None:
        """TroubleshootingState should accept intake inputs."""
        state = TroubleshootingState(
            device_type="furnace",
            symptom="No heat coming from vents",
            urgency="high",
            additional_context="Started yesterday after a power outage",
        )
        assert state.device_type == "furnace"
        assert state.symptom == "No heat coming from vents"
        assert state.urgency == "high"

    def test_followup_generation_response(self) -> None:
        """FollowupGenerationResponse should validate with questions."""
        resp = FollowupGenerationResponse(
            risk_level=RiskLevel.MED,
            followup_questions=[
                FollowupQuestion(
                    id="q1",
                    question="Is the thermostat set to heat?",
                    question_type=QuestionType.YES_NO,
                    why="Basic check",
                ),
            ],
            preliminary_assessment="Likely a thermostat or ignition issue",
        )
        assert resp.risk_level == RiskLevel.MED
        assert len(resp.followup_questions) == 1

    def test_diagnosis_response(self) -> None:
        """DiagnosisResponse should validate with diagnostic steps."""
        resp = DiagnosisResponse(
            diagnosis_summary="Furnace ignition failure",
            diagnostic_steps=[
                DiagnosticStep(
                    step_number=1,
                    instruction="Check thermostat",
                    expected_outcome="Set to heat mode",
                    if_not_resolved="Continue to step 2",
                    risk_level=RiskLevel.LOW,
                ),
            ],
            overall_risk_level=RiskLevel.MED,
            when_to_call_professional="If furnace doesn't ignite after steps 1-3",
        )
        assert resp.diagnosis_summary == "Furnace ignition failure"
        assert len(resp.diagnostic_steps) == 1

    def test_start_request(self) -> None:
        """TroubleshootStartRequest should validate required fields."""
        req = TroubleshootStartRequest(
            device_type="furnace",
            symptom="No heat",
        )
        assert req.device_type == "furnace"
        assert req.urgency == "medium"  # Default

    def test_start_request_rejects_invalid_urgency(self) -> None:
        """TroubleshootStartRequest should reject invalid urgency values."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TroubleshootStartRequest(
                device_type="furnace",
                symptom="No heat",
                urgency="super_urgent",  # type: ignore[arg-type]
            )

    def test_start_request_rejects_long_symptom(self) -> None:
        """TroubleshootStartRequest should reject symptom over max_length."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TroubleshootStartRequest(
                device_type="furnace",
                symptom="x" * 2001,
            )

    def test_start_request_rejects_long_device_type(self) -> None:
        """TroubleshootStartRequest should reject device_type over max_length."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TroubleshootStartRequest(
                device_type="x" * 101,
                symptom="No heat",
            )

    def test_start_request_accepts_max_length(self) -> None:
        """TroubleshootStartRequest should accept fields at exactly max_length."""
        req = TroubleshootStartRequest(
            device_type="x" * 100,
            symptom="y" * 2000,
            additional_context="z" * 2000,
        )
        assert len(req.device_type) == 100
        assert len(req.symptom) == 2000

    def test_start_response_followup(self) -> None:
        """TroubleshootStartResponse should work for follow-up path."""
        resp = TroubleshootStartResponse(
            session_id="test-123",
            phase=TroubleshootPhase.FOLLOWUP,
            risk_level=RiskLevel.MED,
            followup_questions=[
                FollowupQuestion(
                    id="q1",
                    question="Test?",
                    question_type=QuestionType.YES_NO,
                    why="test",
                ),
            ],
            preliminary_assessment="Test assessment",
        )
        assert not resp.is_safety_stop
        assert len(resp.followup_questions) == 1

    def test_start_response_safety_stop(self) -> None:
        """TroubleshootStartResponse should work for safety stop path."""
        resp = TroubleshootStartResponse(
            session_id="test-456",
            phase=TroubleshootPhase.SAFETY_STOP,
            risk_level=RiskLevel.HIGH,
            is_safety_stop=True,
            safety_message="Gas leak detected",
            recommended_professional="gas technician",
        )
        assert resp.is_safety_stop
        assert resp.followup_questions == []

    def test_diagnose_request(self) -> None:
        """TroubleshootDiagnoseRequest should validate."""
        req = TroubleshootDiagnoseRequest(
            session_id="test-123",
            answers=[
                FollowupAnswer(question_id="q1", answer="Yes"),
            ],
        )
        assert req.session_id == "test-123"
        assert len(req.answers) == 1

    def test_diagnose_response(self) -> None:
        """TroubleshootDiagnoseResponse should validate."""
        resp = TroubleshootDiagnoseResponse(
            session_id="test-123",
            diagnosis_summary="Test diagnosis",
            diagnostic_steps=[
                DiagnosticStep(
                    step_number=1,
                    instruction="Test step",
                    expected_outcome="Test outcome",
                    if_not_resolved="Call pro",
                    risk_level=RiskLevel.LOW,
                ),
            ],
            overall_risk_level=RiskLevel.MED,
            when_to_call_professional="If unresolved",
            markdown="# Test",
            sources_used=["doc.pdf"],
        )
        assert resp.session_id == "test-123"
        assert len(resp.sources_used) == 1


# =============================================================================
# SAFETY PATTERN TESTS
# =============================================================================


class TestSafetyPatterns:
    """Tests for deterministic safety pattern matching."""

    def test_gas_smell_triggers_safety_stop(self) -> None:
        """Gas smell keywords should trigger safety stop."""
        result = check_safety_patterns("I smell gas near my furnace", "furnace")
        assert result is not None
        assert result["pattern_name"] == "gas_leak"
        assert "gas" in result["professional"].lower()

    def test_rotten_egg_triggers_gas_leak(self) -> None:
        """Rotten egg smell should map to gas leak."""
        result = check_safety_patterns("There's a rotten egg smell in the basement", "furnace")
        assert result is not None
        assert result["pattern_name"] == "gas_leak"

    def test_co_alarm_triggers_safety_stop(self) -> None:
        """CO alarm keywords should trigger safety stop."""
        result = check_safety_patterns("My carbon monoxide alarm is going off", "furnace")
        assert result is not None
        assert result["pattern_name"] == "carbon_monoxide"
        assert "fire department" in result["professional"].lower()

    def test_co_detector_triggers_safety_stop(self) -> None:
        """CO detector keywords should trigger safety stop."""
        result = check_safety_patterns("The co detector is beeping", "furnace")
        assert result is not None
        assert result["pattern_name"] == "carbon_monoxide"

    def test_electrical_sparking_triggers_safety_stop(self) -> None:
        """Electrical sparking should trigger safety stop."""
        result = check_safety_patterns("My outlet is sparking when I plug things in", "other")
        assert result is not None
        assert result["pattern_name"] == "electrical_hazard"
        assert "electrician" in result["professional"].lower()

    def test_got_shocked_triggers_safety_stop(self) -> None:
        """Getting shocked should trigger safety stop."""
        result = check_safety_patterns("I got shocked touching the light switch", "other")
        assert result is not None
        assert result["pattern_name"] == "electrical_hazard"

    def test_structural_crack_triggers_safety_stop(self) -> None:
        """Structural concerns should trigger safety stop."""
        result = check_safety_patterns("I found a foundation crack in the basement", "other")
        assert result is not None
        assert result["pattern_name"] == "structural"

    def test_normal_symptom_does_not_trigger(self) -> None:
        """Normal symptoms should not trigger safety stop."""
        result = check_safety_patterns("My furnace is making a clicking sound", "furnace")
        assert result is None

    def test_filter_replacement_does_not_trigger(self) -> None:
        """Common maintenance tasks should not trigger."""
        result = check_safety_patterns("How do I replace the furnace filter", "furnace")
        assert result is None

    def test_no_heat_does_not_trigger(self) -> None:
        """'No heat' symptom should not trigger safety stop."""
        result = check_safety_patterns("No heat coming from the vents", "furnace")
        assert result is None

    def test_water_heater_no_hot_water_does_not_trigger(self) -> None:
        """Normal water heater issue should not trigger."""
        result = check_safety_patterns("No hot water from the tap", "water_heater")
        assert result is None

    def test_hrv_noise_does_not_trigger(self) -> None:
        """HRV noise should not trigger safety stop."""
        result = check_safety_patterns("HRV is making a loud humming noise", "hrv")
        assert result is None

    def test_all_patterns_have_required_keys(self) -> None:
        """All safety patterns should have required keys."""
        for name, pattern in SAFETY_STOP_PATTERNS.items():
            assert "keywords" in pattern, f"Pattern '{name}' missing 'keywords'"
            assert "professional" in pattern, f"Pattern '{name}' missing 'professional'"
            assert "message" in pattern, f"Pattern '{name}' missing 'message'"
            assert len(pattern["keywords"]) > 0, f"Pattern '{name}' has no keywords"

    def test_safety_messages_are_actionable(self) -> None:
        """Safety messages should contain actionable guidance."""
        for name, pattern in SAFETY_STOP_PATTERNS.items():
            msg = pattern["message"].lower()
            assert "safety" in msg or "alert" in msg or "emergency" in msg, (
                f"Pattern '{name}' message should mention safety/alert/emergency"
            )

    def test_keyword_matching_is_case_insensitive(self) -> None:
        """Safety pattern matching should be case-insensitive."""
        result = check_safety_patterns("I SMELL GAS in my kitchen", "furnace")
        assert result is not None
        assert result["pattern_name"] == "gas_leak"

    def test_keyword_in_additional_context(self) -> None:
        """Safety keywords in device_type field should also trigger."""
        # 'gas leak' in device_type context
        result = check_safety_patterns("something weird", "gas leak detector")
        assert result is not None

    def test_bare_shock_does_not_trigger(self) -> None:
        """The word 'shock' alone should not trigger (too broad)."""
        result = check_safety_patterns("I was shocked to find the filter dirty", "furnace")
        assert result is None

    def test_electrical_shock_still_triggers(self) -> None:
        """'electrical shock' should still trigger even without bare 'shock'."""
        result = check_safety_patterns("I felt an electrical shock from the panel", "other")
        assert result is not None
        assert result["pattern_name"] == "electrical_hazard"


# =============================================================================
# GRAPH COMPILATION TESTS
# =============================================================================


class TestGraphCompilation:
    """Tests for LangGraph workflow compilation."""

    def test_intake_graph_compiles(self) -> None:
        """Intake graph should compile without errors."""
        workflow = create_intake_workflow()
        assert workflow is not None
        assert isinstance(workflow, CompiledStateGraph)

    def test_diagnosis_graph_compiles(self) -> None:
        """Diagnosis graph should compile without errors."""
        workflow = create_diagnosis_workflow()
        assert workflow is not None
        assert isinstance(workflow, CompiledStateGraph)

    def test_intake_graph_has_expected_nodes(self) -> None:
        """Intake graph should have the 5 expected nodes."""
        graph = build_intake_graph()
        node_names = set(graph.nodes.keys())
        expected = {
            "intake_parse",
            "retrieve_docs",
            "assess_risk",
            "safety_stop",
            "generate_followups",
        }
        assert expected == node_names

    def test_diagnosis_graph_has_expected_nodes(self) -> None:
        """Diagnosis graph should have the 2 expected nodes."""
        graph = build_diagnosis_graph()
        node_names = set(graph.nodes.keys())
        expected = {"generate_diagnosis", "render_output"}
        assert expected == node_names


# =============================================================================
# NODE FUNCTION UNIT TESTS
# =============================================================================


class TestNodeFunctions:
    """Unit tests for individual node functions (no LLM/RAG calls)."""

    def test_intake_parse_normalizes_device_type(self) -> None:
        """intake_parse should normalize device_type to lowercase."""
        state = TroubleshootingState(
            device_type="Furnace",
            symptom="No heat",
        )
        result = intake_parse(state)
        assert result["device_type"] == "furnace"

    def test_intake_parse_replaces_spaces(self) -> None:
        """intake_parse should replace spaces with underscores."""
        state = TroubleshootingState(
            device_type="water heater",
            symptom="No hot water",
        )
        result = intake_parse(state)
        assert result["device_type"] == "water_heater"

    def test_intake_parse_missing_fields(self) -> None:
        """intake_parse should return error if fields are missing."""
        state = TroubleshootingState()
        result = intake_parse(state)
        assert "error" in result

    def test_risk_router_safety_stop(self) -> None:
        """risk_router should route to safety_stop when is_safety_stop is True."""
        state = TroubleshootingState(is_safety_stop=True)
        assert risk_router(state) == "safety_stop"

    def test_risk_router_followups(self) -> None:
        """risk_router should route to generate_followups when not safety_stop."""
        state = TroubleshootingState(is_safety_stop=False)
        assert risk_router(state) == "generate_followups"

    def test_safety_stop_sets_phase(self) -> None:
        """safety_stop node should set phase to SAFETY_STOP."""
        state = TroubleshootingState(
            device_type="furnace",
            is_safety_stop=True,
            safety_message="Gas leak",
            recommended_professional="gas technician",
        )
        result = safety_stop(state)
        assert result["phase"] == TroubleshootPhase.SAFETY_STOP
        assert result["followup_questions"] == []
        assert result["diagnostic_steps"] == []

    def test_render_output_basic(self) -> None:
        """render_output should produce markdown with steps."""
        state = TroubleshootingState(
            device_type="furnace",
            symptom="No heat",
            overall_risk_level=RiskLevel.MED,
            diagnosis_summary="Likely a thermostat or ignition issue",
            diagnostic_steps=[
                DiagnosticStep(
                    step_number=1,
                    instruction="Check thermostat",
                    expected_outcome="Set to HEAT",
                    if_not_resolved="Move to step 2",
                    risk_level=RiskLevel.LOW,
                    source_doc="Furnace-OM9GFRC-02.pdf",
                ),
                DiagnosticStep(
                    step_number=2,
                    instruction="Replace filter",
                    expected_outcome="Clean filter installed",
                    if_not_resolved="Call professional",
                    risk_level=RiskLevel.LOW,
                ),
            ],
            when_to_call_professional="If furnace still doesn't ignite",
        )
        result = render_output(state)
        md = result["markdown_output"]

        assert "# Troubleshooting Diagnosis" in md
        assert "furnace" in md
        assert "No heat" in md
        assert "Step 1" in md
        assert "Step 2" in md
        assert "Check thermostat" in md
        assert "Furnace-OM9GFRC-02.pdf" in md
        assert "When to Call a Professional" in md
        assert result["phase"] == TroubleshootPhase.COMPLETE

    def test_render_output_high_risk_step(self) -> None:
        """render_output should flag HIGH risk steps."""
        state = TroubleshootingState(
            device_type="furnace",
            symptom="Strange smell",
            diagnostic_steps=[
                DiagnosticStep(
                    step_number=1,
                    instruction="Call a licensed HVAC tech",
                    expected_outcome="Professional diagnosis",
                    if_not_resolved="Follow tech's advice",
                    risk_level=RiskLevel.HIGH,
                    requires_professional=True,
                ),
            ],
        )
        result = render_output(state)
        md = result["markdown_output"]
        assert "HIGH RISK" in md
        assert "Professional Required" in md
        assert "licensed professional" in md

    def test_render_output_empty_steps(self) -> None:
        """render_output should handle empty diagnostic steps."""
        state = TroubleshootingState(
            device_type="furnace",
            symptom="No heat",
        )
        result = render_output(state)
        md = result["markdown_output"]
        assert "# Troubleshooting Diagnosis" in md
        assert "Diagnostic Steps" not in md  # No steps section


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestTroubleshooterIntegration:
    """Integration tests for the full troubleshooting workflow.

    These tests call the actual LLM and RAG index.
    """

    @pytest.mark.integration
    def test_intake_generates_followups(
        self,
        house_profile: HouseProfile,
    ) -> None:
        """Intake workflow should generate follow-up questions for normal symptom."""
        workflow = create_intake_workflow()
        result = workflow.invoke(
            {
                "device_type": "furnace",
                "symptom": "Furnace is not producing heat, vents blow cold air",
                "urgency": "high",
                "house_profile": house_profile,
            }
        )

        assert result["phase"] == TroubleshootPhase.FOLLOWUP
        assert not result["is_safety_stop"]
        assert len(result["followup_questions"]) >= 2
        assert result["preliminary_assessment"] is not None

    @pytest.mark.integration
    def test_intake_safety_stops_for_gas_smell(
        self,
        house_profile: HouseProfile,
    ) -> None:
        """Intake workflow should safety-stop for gas smell."""
        workflow = create_intake_workflow()
        result = workflow.invoke(
            {
                "device_type": "furnace",
                "symptom": "I smell gas near my furnace",
                "urgency": "emergency",
                "house_profile": house_profile,
            }
        )

        assert result["phase"] == TroubleshootPhase.SAFETY_STOP
        assert result["is_safety_stop"]
        assert result["risk_level"] == RiskLevel.HIGH
        assert result["safety_message"] is not None
        assert result["recommended_professional"] is not None
        # Should NOT generate follow-up questions
        assert result["followup_questions"] == []

    @pytest.mark.integration
    def test_full_diagnosis_flow(
        self,
        house_profile: HouseProfile,
    ) -> None:
        """Full flow: intake -> followup answers -> diagnosis."""
        # Invocation 1: Intake
        intake_wf = create_intake_workflow()
        intake_result = intake_wf.invoke(
            {
                "device_type": "furnace",
                "symptom": "Furnace making loud banging noise when it starts",
                "urgency": "medium",
                "house_profile": house_profile,
            }
        )

        assert intake_result["phase"] == TroubleshootPhase.FOLLOWUP
        questions = intake_result["followup_questions"]
        assert len(questions) >= 2

        # Simulate user answering follow-up questions
        answers = [{"question_id": q.id, "answer": "I'm not sure"} for q in questions]

        # Invocation 2: Diagnosis
        # Build state from intake result + answers
        diagnosis_state = dict(intake_result)
        diagnosis_state["followup_answers"] = answers

        diagnosis_wf = create_diagnosis_workflow()
        result = diagnosis_wf.invoke(diagnosis_state)

        assert result["phase"] == TroubleshootPhase.COMPLETE
        assert result["diagnosis_summary"] is not None
        assert len(result["diagnostic_steps"]) >= 3
        assert result["when_to_call_professional"] is not None
        assert result["markdown_output"] is not None
        assert "Step 1" in result["markdown_output"]
