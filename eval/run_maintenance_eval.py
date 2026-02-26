"""
Evaluation runner for Maintenance Plan workflow.

This script:
1. Loads golden criteria from maintenance_golden.json
2. Generates maintenance plans for all 4 seasons
3. Evaluates plans against quality criteria
4. Saves a report to eval/reports/

Usage:
    uv run python -m eval.run_maintenance_eval
    uv run python -m eval.run_maintenance_eval --season winter  # Single season
    uv run python -m eval.run_maintenance_eval --threshold-check  # Fail on regression
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

# =============================================================================
# THRESHOLDS — Fixed floors to prevent quality regression
# =============================================================================

THRESHOLDS: dict[str, float] = {
    # Overall pass rate across all season checks
    "overall_pass_rate": 0.80,
    # Minimum source coverage percentage (per season)
    "source_coverage_pct": 50.0,
}


MAX_ITEMS_PER_SEASON = 30  # Upper bound — plans with more items are likely noisy


@dataclass
class SeasonEvalResult:
    """Evaluation results for a single season's maintenance plan."""

    season: str
    total_items: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    items_with_sources: int
    unique_sources: list[str]
    devices_covered: list[str]
    has_markdown: bool
    markdown_has_checkboxes: bool
    # Quality checks
    meets_min_items: bool
    meets_min_high_priority: bool
    source_coverage_pct: float
    within_max_items: bool = True
    meets_device_coverage: bool = True
    no_duplicate_tasks: bool = True
    duplicate_count: int = 0
    missing_devices: list[str] | None = None
    # Errors
    error: str | None = None


def load_golden_criteria() -> dict[str, object]:
    """Load golden criteria from maintenance_golden.json."""
    golden_path = Path(__file__).parent / "maintenance_golden.json"
    with open(golden_path) as f:
        data: dict[str, object] = json.load(f)
        return data


def evaluate_season(
    season_name: str,
    result: dict,
    criteria: dict,
) -> SeasonEvalResult:
    """Evaluate a single season's maintenance plan against criteria."""
    items = result.get("checklist_items", [])
    markdown = result.get("markdown_output", "")

    # Count priorities
    high = [i for i in items if i.priority == "high"]
    medium = [i for i in items if i.priority == "medium"]
    low = [i for i in items if i.priority == "low"]

    # Count sources
    items_with_sources = [i for i in items if i.source_doc]
    unique_sources = sorted(set(i.source_doc for i in items if i.source_doc))

    # Get devices covered
    devices_covered = sorted(set(i.device_type for i in items if i.device_type))

    # Source coverage percentage
    source_pct = len(items_with_sources) / len(items) * 100 if items else 0

    # Get season-specific criteria
    season_criteria = criteria.get("seasons", {}).get(season_name, {})
    min_items = season_criteria.get("min_items", 5)
    min_high = season_criteria.get("min_high_priority", 2)
    expected_devices = season_criteria.get("expected_device_coverage", [])

    # Check device coverage: all expected devices should appear in results
    missing = [d for d in expected_devices if d not in devices_covered]

    # Detect duplicate tasks by normalizing task descriptions
    seen_tasks: set[str] = set()
    duplicate_count = 0
    for item in items:
        # Normalize: lowercase, strip whitespace
        key = item.task.lower().strip()
        if key in seen_tasks:
            duplicate_count += 1
        else:
            seen_tasks.add(key)

    return SeasonEvalResult(
        season=season_name,
        total_items=len(items),
        high_priority_count=len(high),
        medium_priority_count=len(medium),
        low_priority_count=len(low),
        items_with_sources=len(items_with_sources),
        unique_sources=unique_sources,
        devices_covered=devices_covered,
        has_markdown=bool(markdown),
        markdown_has_checkboxes="- [ ]" in markdown,
        meets_min_items=len(items) >= min_items,
        meets_min_high_priority=len(high) >= min_high,
        source_coverage_pct=source_pct,
        within_max_items=len(items) <= MAX_ITEMS_PER_SEASON,
        meets_device_coverage=len(missing) == 0,
        no_duplicate_tasks=duplicate_count == 0,
        duplicate_count=duplicate_count,
        missing_devices=missing if missing else None,
    )


def generate_report(results: list[SeasonEvalResult], criteria: dict) -> str:
    """Generate a markdown report from evaluation results."""
    lines = [
        "# Maintenance Plan Evaluation Report",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        "| Season | Items | High | Med | Low | Sources | Devices | Min Items | Min High |",
        "|--------|-------|------|-----|-----|---------|---------|-----------|----------|",
    ]

    all_pass = True
    for r in results:
        items_check = "✅" if r.meets_min_items else "❌"
        high_check = "✅" if r.meets_min_high_priority else "❌"
        if not r.meets_min_items or not r.meets_min_high_priority:
            all_pass = False

        lines.append(
            f"| {r.season} | {r.total_items} | {r.high_priority_count} | "
            f"{r.medium_priority_count} | {r.low_priority_count} | "
            f"{len(r.unique_sources)} | {len(r.devices_covered)} | "
            f"{items_check} | {high_check} |"
        )

    lines.extend(
        [
            "",
            f"**Overall**: {'✅ All checks passed' if all_pass else '❌ Some checks failed'}",
            "",
            "## Quality Metrics",
            "",
        ]
    )

    for r in results:
        lines.extend(
            [
                f"### {r.season.title()}",
                "",
                f"- **Total items**: {r.total_items}",
                f"- **Priority breakdown**: High={r.high_priority_count}, "
                f"Med={r.medium_priority_count}, Low={r.low_priority_count}",
                f"- **Source coverage**: {r.source_coverage_pct:.1f}% of items cite sources",
                f"- **Devices covered**: {', '.join(r.devices_covered) or 'None'}",
                f"- **Device coverage met**: {'✅' if r.meets_device_coverage else '❌ Missing: ' + ', '.join(r.missing_devices or [])}",
                f"- **Sources used**: {', '.join(r.unique_sources) or 'None'}",
                f"- **Markdown**: {'✅ Valid' if r.has_markdown else '❌ Missing'}, "
                f"Checkboxes: {'✅' if r.markdown_has_checkboxes else '❌'}",
                f"- **Within max items ({MAX_ITEMS_PER_SEASON})**: {'✅' if r.within_max_items else '❌'}",
                f"- **Duplicate tasks**: {r.duplicate_count} found {'✅' if r.no_duplicate_tasks else '❌'}",
                "",
            ]
        )

    # Add criteria reference
    lines.extend(
        [
            "## Golden Criteria Reference",
            "",
        ]
    )
    for season_name, season_criteria in criteria.get("seasons", {}).items():
        lines.extend(
            [
                f"### {season_name.title()}",
                f"- Min items: {season_criteria.get('min_items', 'N/A')}",
                f"- Min high priority: {season_criteria.get('min_high_priority', 'N/A')}",
                f"- Expected themes: {', '.join(season_criteria.get('expected_themes', []))}",
                "",
            ]
        )

    return "\n".join(lines)


def check_thresholds(results: list[SeasonEvalResult]) -> list[str]:
    """Check results against fixed thresholds.

    Returns a list of failure messages. Empty list means all thresholds passed.
    """
    failures: list[str] = []

    # Overall pass rate: each season contributes checks
    # (min_items, min_high_priority, device_coverage, within_max_items)
    total_checks = 0
    total_passed = 0
    for r in results:
        total_checks += 4
        if r.meets_min_items:
            total_passed += 1
        if r.meets_min_high_priority:
            total_passed += 1
        if r.meets_device_coverage:
            total_passed += 1
        if r.within_max_items:
            total_passed += 1

    if total_checks > 0:
        pass_rate = total_passed / total_checks
        threshold = THRESHOLDS["overall_pass_rate"]
        if pass_rate < threshold:
            failures.append(f"  FAIL overall_pass_rate: {pass_rate:.3f} < {threshold:.3f}")

    # Source coverage per season
    source_threshold = THRESHOLDS["source_coverage_pct"]
    for r in results:
        if r.source_coverage_pct < source_threshold:
            failures.append(
                f"  FAIL source_coverage ({r.season}): "
                f"{r.source_coverage_pct:.1f}% < {source_threshold:.1f}%"
            )

    # Markdown quality: every season should produce markdown with checkboxes
    for r in results:
        if not r.has_markdown:
            failures.append(f"  FAIL has_markdown ({r.season}): no markdown output")
        if not r.markdown_has_checkboxes:
            failures.append(
                f"  FAIL markdown_has_checkboxes ({r.season}): no checkboxes in markdown"
            )

    # Device coverage: warn about missing expected devices
    for r in results:
        if not r.meets_device_coverage:
            failures.append(
                f"  FAIL device_coverage ({r.season}): "
                f"missing devices: {', '.join(r.missing_devices or [])}"
            )

    # Duplicate detection: flag excessive duplicates
    for r in results:
        if r.duplicate_count > 0:
            failures.append(
                f"  FAIL duplicate_tasks ({r.season}): {r.duplicate_count} duplicate task(s) found"
            )

    return failures


def main() -> int:
    """Run maintenance plan evaluation."""
    from app.core.ssl_setup import configure_ssl

    configure_ssl()

    parser = argparse.ArgumentParser(description="Evaluate maintenance plans")
    parser.add_argument(
        "--season",
        choices=["spring", "summer", "fall", "winter"],
        help="Evaluate only this season (default: all)",
    )
    parser.add_argument(
        "--threshold-check",
        action="store_true",
        help="Exit with code 1 if any metric falls below its threshold",
    )
    args = parser.parse_args()

    # Import here to avoid loading models when just checking help
    from app.workflows.maintenance_planner import create_maintenance_planner
    from app.workflows.models import Season, load_house_profile

    print("=" * 60)
    print("Maintenance Plan Evaluation")
    print("=" * 60)
    print()

    # Load criteria
    criteria = load_golden_criteria()
    print(f"Loaded golden criteria (v{criteria.get('version', 'unknown')})")

    # Load house profile and create planner
    profile = load_house_profile()
    planner = create_maintenance_planner()
    print(f"House profile: {profile.name}")
    print()

    # Determine which seasons to evaluate
    if args.season:
        seasons = [Season(args.season)]
    else:
        seasons = [Season.SPRING, Season.SUMMER, Season.FALL, Season.WINTER]

    # Generate and evaluate plans
    results: list[SeasonEvalResult] = []
    for season in seasons:
        print(f"Generating {season.value} plan...")
        result = planner.invoke(
            {
                "house_profile": profile,
                "season": season,
            }
        )

        eval_result = evaluate_season(season.value, result, criteria)
        results.append(eval_result)
        print(
            f"  → {eval_result.total_items} items, "
            f"{eval_result.high_priority_count} high priority, "
            f"{len(eval_result.unique_sources)} sources"
        )

    print()

    # Generate report
    report = generate_report(results, criteria)

    # Save report
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"maintenance_eval_{timestamp}.md"
    report_path.write_text(report)
    print(f"Report saved to: {report_path}")

    # Also save JSON results
    json_path = reports_dir / f"maintenance_eval_{timestamp}.json"
    json_results = {
        "timestamp": timestamp,
        "seasons": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(json_results, indent=2))
    print(f"JSON results saved to: {json_path}")

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    all_pass = all(r.meets_min_items and r.meets_min_high_priority for r in results)
    for r in results:
        status = "✅" if r.meets_min_items and r.meets_min_high_priority else "❌"
        print(
            f"  {status} {r.season}: {r.total_items} items, {r.high_priority_count} high priority"
        )
    print()
    print(f"Overall: {'✅ All checks passed' if all_pass else '❌ Some checks failed'}")

    # Threshold check
    if args.threshold_check:
        failures = check_thresholds(results)
        if failures:
            print("\nTHRESHOLD CHECK FAILED:")
            for f in failures:
                print(f)
            return 1
        print("\nTHRESHOLD CHECK PASSED: All metrics within acceptable range.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
