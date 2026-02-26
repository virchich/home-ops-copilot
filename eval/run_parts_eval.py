"""
Evaluation runner for Parts & Consumables Helper workflow.

This script:
1. Loads golden scenarios from parts_golden.json
2. Runs the parts helper workflow for each scenario
3. Evaluates results against expected criteria
4. Saves a report to eval/reports/

Usage:
    uv run python -m eval.run_parts_eval
    uv run python -m eval.run_parts_eval --scenario furnace_filter
"""

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.workflows.parts_helper_models import ConfidenceLevel


@dataclass
class ScenarioEvalResult:
    """Evaluation results for a single parts lookup scenario."""

    scenario_id: str
    query: str
    device_type: str | None = None

    # Results
    part_count: int = 0
    confirmed_count: int = 0
    likely_count: int = 0
    uncertain_count: int = 0
    clarification_count: int = 0
    device_types_found: list[str] = field(default_factory=list)
    parts_with_sources: int = 0
    parts_with_part_numbers: int = 0
    parts_with_intervals: int = 0
    summary_present: bool = False
    markdown_length: int = 0

    # Checks
    min_parts_ok: bool = False
    expected_devices_ok: bool = False
    min_confirmed_or_likely_ok: bool = False
    source_citation_ok: bool = False
    part_number_ok: bool = False
    replacement_interval_ok: bool = False
    clarification_count_ok: bool = False
    confirmed_have_sources: bool = False
    uncertain_no_part_numbers: bool = False
    min_device_types_ok: bool = False

    # Errors
    error: str | None = None
    checks_passed: int = 0
    checks_total: int = 0


def load_golden_scenarios() -> dict[str, Any]:
    """Load golden scenarios from parts_golden.json."""
    golden_path = Path(__file__).parent / "parts_golden.json"
    with open(golden_path) as f:
        result: dict[str, Any] = json.load(f)
        return result


def evaluate_scenario(
    result: dict,
    expected: dict,
    eval_result: ScenarioEvalResult,
) -> None:
    """Evaluate parts lookup results against expected criteria."""
    parts = result.get("parts", [])
    clarifications = result.get("clarification_questions", [])

    eval_result.part_count = len(parts)
    eval_result.clarification_count = len(clarifications)
    eval_result.summary_present = bool(result.get("summary"))
    eval_result.markdown_length = len(result.get("markdown_output", ""))

    # Count confidence levels
    for part in parts:
        if part.confidence == ConfidenceLevel.CONFIRMED:
            eval_result.confirmed_count += 1
        elif part.confidence == ConfidenceLevel.LIKELY:
            eval_result.likely_count += 1
        elif part.confidence == ConfidenceLevel.UNCERTAIN:
            eval_result.uncertain_count += 1

    # Collect device types
    eval_result.device_types_found = sorted({part.device_type for part in parts})

    # Count parts with sources, part numbers, intervals
    eval_result.parts_with_sources = sum(1 for p in parts if p.source_doc)
    eval_result.parts_with_part_numbers = sum(1 for p in parts if p.part_number)
    eval_result.parts_with_intervals = sum(1 for p in parts if p.replacement_interval)

    # === Run checks ===

    # Check: minimum parts count
    min_parts = expected.get("min_parts", 0)
    eval_result.min_parts_ok = eval_result.part_count >= min_parts

    # Check: expected device types present in results
    expected_devices = expected.get("expected_device_types", [])
    if expected_devices:
        eval_result.expected_devices_ok = all(
            d in eval_result.device_types_found for d in expected_devices
        )
    else:
        eval_result.expected_devices_ok = True

    # Check: minimum confirmed or likely parts
    min_conf_likely = expected.get("min_confirmed_or_likely", 0)
    eval_result.min_confirmed_or_likely_ok = (
        eval_result.confirmed_count + eval_result.likely_count >= min_conf_likely
    )

    # Check: source citations present
    if expected.get("should_cite_source", False):
        eval_result.source_citation_ok = eval_result.parts_with_sources > 0
    else:
        eval_result.source_citation_ok = True

    # Check: part number or size present
    if expected.get("should_have_part_number_or_size", False):
        eval_result.part_number_ok = eval_result.parts_with_part_numbers > 0
    else:
        eval_result.part_number_ok = True

    # Check: replacement interval present
    if expected.get("should_have_replacement_interval", False):
        eval_result.replacement_interval_ok = eval_result.parts_with_intervals > 0
    else:
        eval_result.replacement_interval_ok = True

    # Check: clarification question count
    max_cq = expected.get("max_clarification_questions", 10)
    min_cq = expected.get("min_clarification_questions", 0)
    eval_result.clarification_count_ok = min_cq <= eval_result.clarification_count <= max_cq

    # Check: CONFIRMED parts must have source_doc
    confirmed_parts = [p for p in parts if p.confidence == ConfidenceLevel.CONFIRMED]
    eval_result.confirmed_have_sources = (
        all(p.source_doc for p in confirmed_parts) if confirmed_parts else True
    )

    # Check: UNCERTAIN parts must NOT have part_number
    uncertain_parts = [p for p in parts if p.confidence == ConfidenceLevel.UNCERTAIN]
    eval_result.uncertain_no_part_numbers = (
        all(not p.part_number for p in uncertain_parts) if uncertain_parts else True
    )

    # Check: minimum device types in results (for multi-device queries)
    min_dt = expected.get("min_device_types_in_results", 0)
    eval_result.min_device_types_ok = (
        len(eval_result.device_types_found) >= min_dt if min_dt > 0 else True
    )


def count_checks(eval_result: ScenarioEvalResult) -> None:
    """Count total checks and passed checks."""
    checks = [
        ("min_parts_ok", eval_result.min_parts_ok),
        ("expected_devices_ok", eval_result.expected_devices_ok),
        ("min_confirmed_or_likely_ok", eval_result.min_confirmed_or_likely_ok),
        ("source_citation_ok", eval_result.source_citation_ok),
        ("part_number_ok", eval_result.part_number_ok),
        ("replacement_interval_ok", eval_result.replacement_interval_ok),
        ("clarification_count_ok", eval_result.clarification_count_ok),
        ("confirmed_have_sources", eval_result.confirmed_have_sources),
        ("uncertain_no_part_numbers", eval_result.uncertain_no_part_numbers),
        ("min_device_types_ok", eval_result.min_device_types_ok),
    ]

    eval_result.checks_total = len(checks)
    eval_result.checks_passed = sum(1 for _, passed in checks if passed)


def generate_report(results: list[ScenarioEvalResult]) -> str:
    """Generate a markdown report from evaluation results."""
    lines = [
        "# Parts Helper Evaluation Report",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        "| Scenario | Parts | Confirmed | Likely | Uncertain | CQ | Sources | Checks |",
        "|----------|-------|-----------|--------|-----------|-----|---------|--------|",
    ]

    total_passed = 0
    total_checks = 0
    for r in results:
        total_passed += r.checks_passed
        total_checks += r.checks_total
        checks_str = f"{r.checks_passed}/{r.checks_total}"
        lines.append(
            f"| {r.scenario_id} | {r.part_count} | {r.confirmed_count} | "
            f"{r.likely_count} | {r.uncertain_count} | {r.clarification_count} | "
            f"{r.parts_with_sources} | {checks_str} |"
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
                f"- **Query**: {r.query[:80]}",
                f"- **Device filter**: {r.device_type or 'none'}",
                f"- **Parts found**: {r.part_count} (confirmed={r.confirmed_count}, "
                f"likely={r.likely_count}, uncertain={r.uncertain_count})",
                f"- **Device types**: {', '.join(r.device_types_found) or 'none'}",
                f"- **Clarification questions**: {r.clarification_count}",
                f"- **Parts with sources**: {r.parts_with_sources}",
                f"- **Parts with part numbers**: {r.parts_with_part_numbers}",
                f"- **Parts with intervals**: {r.parts_with_intervals}",
                f"- **Summary present**: {r.summary_present}",
                "",
                "**Checks**:",
                f"  - min_parts: {r.min_parts_ok}",
                f"  - expected_devices: {r.expected_devices_ok}",
                f"  - min_confirmed_or_likely: {r.min_confirmed_or_likely_ok}",
                f"  - source_citations: {r.source_citation_ok}",
                f"  - part_numbers: {r.part_number_ok}",
                f"  - replacement_intervals: {r.replacement_interval_ok}",
                f"  - clarification_count: {r.clarification_count_ok}",
                f"  - confirmed_have_sources: {r.confirmed_have_sources}",
                f"  - uncertain_no_part_numbers: {r.uncertain_no_part_numbers}",
                f"  - min_device_types: {r.min_device_types_ok}",
            ]
        )

        if r.error:
            lines.append(f"  - **Error**: {r.error}")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Run parts helper evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate parts helper workflow")
    parser.add_argument(
        "--scenario",
        help="Evaluate only this scenario ID (default: all)",
    )
    args = parser.parse_args()

    # Import here to avoid loading models when just checking help
    from app.workflows.models import load_house_profile
    from app.workflows.parts_helper import create_parts_helper

    print("=" * 60)
    print("Parts Helper Evaluation")
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

    # Load house profile and create workflow
    profile = load_house_profile()
    workflow = create_parts_helper()
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
            query=scenario["query"],
            device_type=scenario.get("device_type"),
        )

        try:
            result = workflow.invoke(
                {
                    "query": scenario["query"],
                    "device_type": scenario.get("device_type"),
                    "house_profile": profile,
                }
            )

            evaluate_scenario(result, expected, eval_result)
            count_checks(eval_result)

        except Exception as e:
            eval_result.error = str(e)
            eval_result.checks_total = 1
            eval_result.checks_passed = 0

        results.append(eval_result)
        status = "PASS" if eval_result.checks_passed == eval_result.checks_total else "FAIL"
        print(
            f"  [{status}] parts={eval_result.part_count}, "
            f"confirmed={eval_result.confirmed_count}, "
            f"likely={eval_result.likely_count}, "
            f"cq={eval_result.clarification_count}, "
            f"checks={eval_result.checks_passed}/{eval_result.checks_total}"
        )

    print()

    # Generate report
    report = generate_report(results)

    # Save report
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"parts_eval_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved to: {report_path}")

    # Also save JSON results
    json_path = reports_dir / f"parts_eval_{timestamp}.json"
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
