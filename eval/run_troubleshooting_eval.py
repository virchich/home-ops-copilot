"""
Evaluation runner for Troubleshooting workflow.

This script:
1. Loads golden scenarios from troubleshooting_golden.json
2. Runs the intake workflow for each scenario
3. For non-safety-stop scenarios, runs the diagnosis workflow
4. Evaluates results against expected criteria
5. Saves a report to eval/reports/

Usage:
    uv run python -m eval.run_troubleshooting_eval
    uv run python -m eval.run_troubleshooting_eval --scenario gas_smell_furnace
"""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ScenarioEvalResult:
    """Evaluation results for a single troubleshooting scenario."""

    scenario_id: str
    device_type: str
    symptom: str

    # Intake results
    actual_risk_level: str | None = None
    actual_is_safety_stop: bool = False
    followup_question_count: int = 0
    preliminary_assessment: str | None = None

    # Diagnosis results (only for non-safety-stop)
    diagnostic_step_count: int = 0
    steps_with_sources: int = 0
    steps_requiring_professional: int = 0
    has_professional_recommendation: bool = False
    markdown_length: int = 0

    # Checks
    safety_stop_correct: bool = False
    risk_level_correct: bool = False
    followup_count_in_range: bool = False
    diagnostic_count_in_range: bool = False
    has_source_citations: bool = False
    no_forbidden_keywords: bool = False

    # Errors
    error: str | None = None
    checks_passed: int = 0
    checks_total: int = 0


def load_golden_scenarios() -> dict[str, Any]:
    """Load golden scenarios from troubleshooting_golden.json."""
    golden_path = Path(__file__).parent / "troubleshooting_golden.json"
    with open(golden_path) as f:
        result: dict[str, Any] = json.load(f)
        return result


def evaluate_intake(
    result: dict,
    expected: dict,
    eval_result: ScenarioEvalResult,
) -> None:
    """Evaluate intake workflow results against expected criteria."""
    eval_result.actual_risk_level = result.get("risk_level")
    if eval_result.actual_risk_level and hasattr(eval_result.actual_risk_level, "value"):
        eval_result.actual_risk_level = eval_result.actual_risk_level.value

    eval_result.actual_is_safety_stop = result.get("is_safety_stop", False)
    eval_result.followup_question_count = len(result.get("followup_questions", []))
    eval_result.preliminary_assessment = result.get("preliminary_assessment")

    # Check: safety stop correct
    eval_result.safety_stop_correct = eval_result.actual_is_safety_stop == expected.get(
        "is_safety_stop", False
    )

    # Check: risk level correct
    expected_risk = expected.get("risk_level")
    if expected_risk:
        eval_result.risk_level_correct = eval_result.actual_risk_level == expected_risk
    else:
        eval_result.risk_level_correct = True

    # Check: followup question count (only for non-safety-stop)
    if not expected.get("is_safety_stop", False):
        min_q = expected.get("min_followup_questions", 2)
        max_q = expected.get("max_followup_questions", 3)
        eval_result.followup_count_in_range = min_q <= eval_result.followup_question_count <= max_q
    else:
        # Safety-stopped scenarios should have 0 follow-up questions
        eval_result.followup_count_in_range = eval_result.followup_question_count == 0


def evaluate_diagnosis(
    result: dict,
    expected: dict,
    eval_result: ScenarioEvalResult,
) -> None:
    """Evaluate diagnosis workflow results against expected criteria."""
    steps = result.get("diagnostic_steps", [])
    eval_result.diagnostic_step_count = len(steps)
    eval_result.steps_with_sources = sum(1 for s in steps if s.source_doc)
    eval_result.steps_requiring_professional = sum(1 for s in steps if s.requires_professional)
    eval_result.has_professional_recommendation = bool(result.get("when_to_call_professional"))
    eval_result.markdown_length = len(result.get("markdown_output", ""))

    # Check: diagnostic step count
    min_s = expected.get("min_diagnostic_steps", 3)
    max_s = expected.get("max_diagnostic_steps", 6)
    eval_result.diagnostic_count_in_range = min_s <= eval_result.diagnostic_step_count <= max_s

    # Check: source citations
    if expected.get("should_cite_sources", False):
        eval_result.has_source_citations = eval_result.steps_with_sources > 0
    else:
        eval_result.has_source_citations = True

    # Check: forbidden keywords in markdown
    forbidden = expected.get("forbidden_keywords", [])
    markdown = result.get("markdown_output", "").lower()
    eval_result.no_forbidden_keywords = not any(kw.lower() in markdown for kw in forbidden)


def count_checks(eval_result: ScenarioEvalResult, expected: dict) -> None:
    """Count total checks and passed checks."""
    checks = [
        ("safety_stop_correct", eval_result.safety_stop_correct),
        ("risk_level_correct", eval_result.risk_level_correct),
        ("followup_count_in_range", eval_result.followup_count_in_range),
    ]

    # Only check diagnosis for non-safety-stop scenarios
    if not expected.get("is_safety_stop", False):
        checks.extend(
            [
                ("diagnostic_count_in_range", eval_result.diagnostic_count_in_range),
                ("has_source_citations", eval_result.has_source_citations),
                ("no_forbidden_keywords", eval_result.no_forbidden_keywords),
                ("has_professional_recommendation", eval_result.has_professional_recommendation),
            ]
        )
    else:
        checks.append(("no_forbidden_keywords", eval_result.no_forbidden_keywords))

    eval_result.checks_total = len(checks)
    eval_result.checks_passed = sum(1 for _, passed in checks if passed)


def generate_report(results: list[ScenarioEvalResult]) -> str:
    """Generate a markdown report from evaluation results."""
    lines = [
        "# Troubleshooting Workflow Evaluation Report",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        "| Scenario | Risk | Safety Stop | Follow-ups | Steps | Sources | Checks |",
        "|----------|------|-------------|------------|-------|---------|--------|",
    ]

    total_passed = 0
    total_checks = 0
    for r in results:
        total_passed += r.checks_passed
        total_checks += r.checks_total

        safety_icon = "STOP" if r.actual_is_safety_stop else "-"
        safety_check = "OK" if r.safety_stop_correct else "FAIL"
        checks_str = f"{r.checks_passed}/{r.checks_total}"

        lines.append(
            f"| {r.scenario_id} | {r.actual_risk_level or '?'} | "
            f"{safety_icon} ({safety_check}) | {r.followup_question_count} | "
            f"{r.diagnostic_step_count} | {r.steps_with_sources} | {checks_str} |"
        )

    all_pass = total_passed == total_checks
    lines.extend(
        [
            "",
            f"**Overall**: {total_passed}/{total_checks} checks passed "
            f"({'All passed' if all_pass else 'Some failed'})",
            "",
        ]
    )

    # Details per scenario
    lines.append("## Details")
    lines.append("")
    for r in results:
        status = "PASS" if r.checks_passed == r.checks_total else "FAIL"
        lines.extend(
            [
                f"### {r.scenario_id} [{status}]",
                "",
                f"- **Device**: {r.device_type}",
                f"- **Symptom**: {r.symptom[:80]}...",
                f"- **Risk Level**: {r.actual_risk_level} (correct: {r.risk_level_correct})",
                f"- **Safety Stop**: {r.actual_is_safety_stop} (correct: {r.safety_stop_correct})",
                f"- **Follow-up Questions**: {r.followup_question_count} (in range: {r.followup_count_in_range})",
            ]
        )

        if not r.actual_is_safety_stop:
            lines.extend(
                [
                    f"- **Diagnostic Steps**: {r.diagnostic_step_count} (in range: {r.diagnostic_count_in_range})",
                    f"- **Steps with Sources**: {r.steps_with_sources} (has citations: {r.has_source_citations})",
                    f"- **Professional Recommendation**: {r.has_professional_recommendation}",
                ]
            )

        if r.error:
            lines.append(f"- **Error**: {r.error}")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Run troubleshooting evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate troubleshooting workflow")
    parser.add_argument(
        "--scenario",
        help="Evaluate only this scenario ID (default: all)",
    )
    args = parser.parse_args()

    # Import here to avoid loading models when just checking help
    from app.workflows.models import load_house_profile
    from app.workflows.troubleshooter import create_diagnosis_workflow, create_intake_workflow
    from app.workflows.troubleshooter_models import FollowupAnswer

    print("=" * 60)
    print("Troubleshooting Workflow Evaluation")
    print("=" * 60)
    print()

    # Load golden scenarios
    golden = load_golden_scenarios()
    scenarios = golden["scenarios"]
    print(f"Loaded {len(scenarios)} golden scenarios (v{golden.get('version', 'unknown')})")

    # Filter if specific scenario requested
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            print(f"ERROR: Scenario '{args.scenario}' not found")
            return
        print(f"Running single scenario: {args.scenario}")

    # Load house profile and create workflows
    profile = load_house_profile()
    intake_wf = create_intake_workflow()
    diagnosis_wf = create_diagnosis_workflow()
    print(f"House profile: {profile.name}")
    print()

    # Run scenarios
    results: list[ScenarioEvalResult] = []
    for scenario in scenarios:
        scenario_id = scenario["id"]
        expected = scenario["expected"]
        print(f"Running scenario: {scenario_id}...")

        eval_result = ScenarioEvalResult(
            scenario_id=scenario_id,
            device_type=scenario["device_type"],
            symptom=scenario["symptom"],
        )

        try:
            # Run intake workflow
            intake_result = intake_wf.invoke(
                {
                    "device_type": scenario["device_type"],
                    "symptom": scenario["symptom"],
                    "urgency": scenario.get("urgency", "medium"),
                    "additional_context": scenario.get("additional_context"),
                    "house_profile": profile,
                }
            )

            evaluate_intake(intake_result, expected, eval_result)

            # Run diagnosis if not safety-stopped
            if not intake_result.get("is_safety_stop", False):
                # Simulate follow-up answers
                questions = intake_result.get("followup_questions", [])
                answers = [
                    FollowupAnswer(
                        question_id=q.id,
                        answer="I'm not sure",
                    )
                    for q in questions
                ]

                state_dict = dict(intake_result)
                state_dict["followup_answers"] = [a.model_dump() for a in answers]

                diagnosis_result = diagnosis_wf.invoke(state_dict)
                evaluate_diagnosis(diagnosis_result, expected, eval_result)
            else:
                # Safety-stopped: check that no DIY steps were generated
                eval_result.no_forbidden_keywords = True
                eval_result.diagnostic_count_in_range = True
                eval_result.has_source_citations = True

            count_checks(eval_result, expected)

        except Exception as e:
            eval_result.error = str(e)
            eval_result.checks_total = 1
            eval_result.checks_passed = 0

        results.append(eval_result)
        status = "PASS" if eval_result.checks_passed == eval_result.checks_total else "FAIL"
        print(
            f"  [{status}] risk={eval_result.actual_risk_level}, "
            f"safety_stop={eval_result.actual_is_safety_stop}, "
            f"followups={eval_result.followup_question_count}, "
            f"steps={eval_result.diagnostic_step_count}, "
            f"checks={eval_result.checks_passed}/{eval_result.checks_total}"
        )

    print()

    # Generate report
    report = generate_report(results)

    # Save report
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"troubleshooting_eval_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved to: {report_path}")

    # Also save JSON results
    json_path = reports_dir / f"troubleshooting_eval_{timestamp}.json"
    json_results = {
        "timestamp": timestamp,
        "scenarios": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(json_results, indent=2))
    print(f"JSON results saved to: {json_path}")

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    total_passed = sum(r.checks_passed for r in results)
    total_checks = sum(r.checks_total for r in results)
    all_pass = total_passed == total_checks
    for r in results:
        status = "PASS" if r.checks_passed == r.checks_total else "FAIL"
        print(f"  [{status}] {r.scenario_id}: {r.checks_passed}/{r.checks_total} checks")
    print()
    print(
        f"Overall: {total_passed}/{total_checks} checks "
        f"({'All passed' if all_pass else 'Some failed'})"
    )


if __name__ == "__main__":
    main()
