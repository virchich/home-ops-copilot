"""Tests for ICS calendar generation.

Tests the ics_generator module which converts maintenance checklist items
into iCalendar (.ics) events for import into calendar applications.
"""

from datetime import date

from app.workflows.ics_generator import (
    SEASON_START_MONTH,
    _escape_ics,
    _fold_line,
    _next_date_for_season,
    generate_ics,
)
from app.workflows.models import ChecklistItem, Season

# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================


class TestEscapeIcs:
    """Tests for RFC 5545 text escaping."""

    def test_no_special_chars(self) -> None:
        assert _escape_ics("Hello world") == "Hello world"

    def test_escapes_semicolons(self) -> None:
        assert _escape_ics("Check filter; replace if dirty") == "Check filter\\; replace if dirty"

    def test_escapes_commas(self) -> None:
        assert _escape_ics("Furnace, HRV, humidifier") == "Furnace\\, HRV\\, humidifier"

    def test_escapes_backslashes(self) -> None:
        assert _escape_ics("path\\to\\file") == "path\\\\to\\\\file"

    def test_escapes_newlines(self) -> None:
        assert _escape_ics("Line 1\nLine 2") == "Line 1\\nLine 2"

    def test_escapes_multiple_special_chars(self) -> None:
        result = _escape_ics("A; B, C\nD")
        assert result == "A\\; B\\, C\\nD"


class TestFoldLine:
    """Tests for RFC 5545 line folding (max 75 octets)."""

    def test_short_line_unchanged(self) -> None:
        line = "SUMMARY:Replace furnace filter"
        assert _fold_line(line) == line

    def test_exactly_75_bytes_unchanged(self) -> None:
        line = "X" * 75
        assert _fold_line(line) == line

    def test_long_line_folded(self) -> None:
        line = "DESCRIPTION:" + "A" * 100
        result = _fold_line(line)
        # Folded lines use CRLF + space as continuation
        assert "\r\n " in result
        # First line should be <= 75 bytes
        first_line = result.split("\r\n")[0]
        assert len(first_line.encode("utf-8")) <= 75


class TestNextDateForSeason:
    """Tests for season date calculation."""

    def test_future_season_same_year(self) -> None:
        """If season hasn't passed, use current year."""
        ref = date(2026, 1, 15)  # January — spring (April) is ahead
        result = _next_date_for_season(Season.SPRING, ref)
        assert result == date(2026, 4, 1)

    def test_past_season_rolls_to_next_year(self) -> None:
        """If season already passed, use next year."""
        ref = date(2026, 10, 15)  # October — spring (April) already passed
        result = _next_date_for_season(Season.SPRING, ref)
        assert result == date(2027, 4, 1)

    def test_all_seasons_have_start_months(self) -> None:
        """Every season should have a configured start month."""
        for season in Season:
            assert season in SEASON_START_MONTH
            month = SEASON_START_MONTH[season]
            assert 1 <= month <= 12

    def test_winter_start_month(self) -> None:
        assert SEASON_START_MONTH[Season.WINTER] == 11

    def test_summer_start_month(self) -> None:
        assert SEASON_START_MONTH[Season.SUMMER] == 6


# =============================================================================
# ICS GENERATION TESTS
# =============================================================================


def _make_item(
    task: str = "Test task",
    priority: str = "medium",
    device_type: str | None = "furnace",
    frequency: str | None = None,
    estimated_time: str | None = None,
    notes: str | None = None,
    source_doc: str | None = None,
) -> ChecklistItem:
    """Helper to create a ChecklistItem with defaults."""
    return ChecklistItem(
        task=task,
        priority=priority,
        device_type=device_type,
        frequency=frequency,
        estimated_time=estimated_time,
        notes=notes,
        source_doc=source_doc,
    )


class TestGenerateIcs:
    """Tests for the main generate_ics function."""

    def test_empty_checklist(self) -> None:
        """Empty checklist should produce a valid calendar with no events."""
        result = generate_ics([], Season.FALL, "Test House", ref_date=date(2026, 1, 1))
        assert "BEGIN:VCALENDAR" in result
        assert "END:VCALENDAR" in result
        assert "BEGIN:VEVENT" not in result

    def test_single_item(self) -> None:
        """Single item should produce one VEVENT."""
        items = [_make_item(task="Replace furnace filter")]
        result = generate_ics(items, Season.FALL, "Test House", ref_date=date(2026, 1, 1))
        assert result.count("BEGIN:VEVENT") == 1
        assert result.count("END:VEVENT") == 1
        assert "Replace furnace filter" in result

    def test_multiple_items(self) -> None:
        """Multiple items should produce multiple VEVENTs."""
        items = [
            _make_item(task="Task 1", priority="high"),
            _make_item(task="Task 2", priority="medium"),
            _make_item(task="Task 3", priority="low"),
        ]
        result = generate_ics(items, Season.WINTER, "My Home", ref_date=date(2026, 1, 1))
        assert result.count("BEGIN:VEVENT") == 3
        assert result.count("END:VEVENT") == 3

    def test_calendar_name_includes_season_and_house(self) -> None:
        result = generate_ics([_make_item()], Season.SPRING, "Main St", ref_date=date(2026, 1, 1))
        assert "Spring Maintenance - Main St" in result

    def test_crlf_line_endings(self) -> None:
        """ICS spec requires CRLF line endings."""
        result = generate_ics([_make_item()], Season.FALL, "House", ref_date=date(2026, 1, 1))
        # Every line should end with \r\n (not bare \n)
        assert "\r\n" in result

    def test_priority_staggering(self) -> None:
        """High, medium, and low priority items should have different dates."""
        items = [
            _make_item(task="High task", priority="high"),
            _make_item(task="Med task", priority="medium"),
            _make_item(task="Low task", priority="low"),
        ]
        ref = date(2026, 1, 1)
        result = generate_ics(items, Season.FALL, "House", ref_date=ref)

        # Fall starts in September 2026
        # High: Sept 1, Medium: Sept 8, Low: Sept 15
        assert "DTSTART;VALUE=DATE:20260901" in result  # high: offset 0
        assert "DTSTART;VALUE=DATE:20260908" in result  # medium: offset 7
        assert "DTSTART;VALUE=DATE:20260915" in result  # low: offset 14

    def test_all_day_events(self) -> None:
        """Events should be all-day (VALUE=DATE, not DATETIME)."""
        result = generate_ics([_make_item()], Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "DTSTART;VALUE=DATE:" in result
        assert "DTEND;VALUE=DATE:" in result

    def test_uid_uniqueness(self) -> None:
        """Each event should have a unique UID."""
        items = [_make_item(task=f"Task {i}") for i in range(5)]
        result = generate_ics(items, Season.SPRING, "House", ref_date=date(2026, 1, 1))
        uids = [line for line in result.split("\r\n") if line.startswith("UID:")]
        assert len(uids) == 5
        assert len(set(uids)) == 5  # All unique

    def test_description_includes_notes(self) -> None:
        items = [_make_item(notes="Use MERV 11 filter (16x25x1)")]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "MERV 11" in result

    def test_description_includes_frequency(self) -> None:
        items = [_make_item(frequency="monthly")]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "monthly" in result

    def test_description_includes_estimated_time(self) -> None:
        items = [_make_item(estimated_time="5 minutes")]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "5 minutes" in result

    def test_description_includes_source(self) -> None:
        items = [_make_item(source_doc="Furnace-OM9GFRC.pdf")]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "Furnace-OM9GFRC.pdf" in result

    def test_categories_from_device_type(self) -> None:
        items = [_make_item(device_type="hrv")]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "CATEGORIES:hrv" in result

    def test_no_categories_when_no_device_type(self) -> None:
        items = [_make_item(device_type=None)]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "CATEGORIES:" not in result

    def test_ical_priority_mapping(self) -> None:
        """iCalendar priority: 1=highest, 5=medium, 9=lowest."""
        items = [
            _make_item(task="H", priority="high"),
            _make_item(task="M", priority="medium"),
            _make_item(task="L", priority="low"),
        ]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        lines = result.split("\r\n")
        priorities = [line for line in lines if line.startswith("PRIORITY:")]
        assert "PRIORITY:1" in priorities
        assert "PRIORITY:5" in priorities
        assert "PRIORITY:9" in priorities

    def test_prodid_set(self) -> None:
        result = generate_ics([], Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "PRODID:-//Home Ops Copilot//EN" in result

    def test_version_2_0(self) -> None:
        result = generate_ics([], Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "VERSION:2.0" in result

    def test_special_chars_escaped_in_summary(self) -> None:
        items = [_make_item(task="Check filter; replace if dirty")]
        result = generate_ics(items, Season.FALL, "House", ref_date=date(2026, 1, 1))
        assert "SUMMARY:Check filter\\; replace if dirty" in result
