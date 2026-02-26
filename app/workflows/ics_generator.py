"""ICS calendar generation for maintenance reminders.

Converts maintenance checklist items into iCalendar (.ics) events so
homeowners can import seasonal reminders into Apple Calendar, Google
Calendar, Outlook, etc.

The generated calendar uses RFC 5545 (iCalendar) format without any
third-party library — the spec is simple enough for our use case.
"""

from datetime import date, timedelta

from app.workflows.models import ChecklistItem, Season

# ---------------------------------------------------------------------------
# Season → month mapping
# ---------------------------------------------------------------------------
# Each season maps to a start month when the tasks should begin.
# These are approximate — the homeowner can adjust after import.

SEASON_START_MONTH: dict[Season, int] = {
    Season.SPRING: 4,  # April
    Season.SUMMER: 6,  # June
    Season.FALL: 9,  # September
    Season.WINTER: 11,  # November
}


def _next_date_for_season(season: Season, ref: date | None = None) -> date:
    """Return the next upcoming date for the given season's start month.

    If the season's month has already passed this year, return next year.
    """
    today = ref or date.today()
    month = SEASON_START_MONTH[season]
    target = date(today.year, month, 1)
    if target < today:
        target = date(today.year + 1, month, 1)
    return target


def _escape_ics(text: str) -> str:
    """Escape special characters for iCalendar text fields (RFC 5545 §3.3.11)."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold_line(line: str) -> str:
    """Fold long lines per RFC 5545 §3.1 (max 75 octets per line)."""
    if len(line.encode("utf-8")) <= 75:
        return line
    # Split into 75-byte chunks; continuation lines start with a space
    result: list[str] = []
    encoded = line.encode("utf-8")
    first_chunk = encoded[:75].decode("utf-8", errors="ignore")
    result.append(first_chunk)
    pos = len(first_chunk.encode("utf-8"))
    while pos < len(encoded):
        chunk = encoded[pos : pos + 74].decode("utf-8", errors="ignore")
        result.append(" " + chunk)
        pos += len(chunk.encode("utf-8"))
    return "\r\n".join(result)


def generate_ics(
    checklist_items: list[ChecklistItem],
    season: Season,
    house_name: str,
    ref_date: date | None = None,
) -> str:
    """Generate an iCalendar (.ics) string from maintenance checklist items.

    Each checklist item becomes an all-day event. High-priority items are
    placed on the season start date; medium items one week later; low items
    two weeks later. This gives the homeowner a natural stagger.

    Args:
        checklist_items: Maintenance tasks to convert to calendar events.
        season: The season this plan is for (determines event dates).
        house_name: House identifier (used in calendar name).
        ref_date: Reference date for calculating event dates (defaults to today).

    Returns:
        A valid iCalendar string ready to write to a .ics file.
    """
    base_date = _next_date_for_season(season, ref_date)

    # Stagger by priority so the homeowner isn't overwhelmed on day 1
    priority_offsets: dict[str, int] = {
        "high": 0,
        "medium": 7,
        "low": 14,
    }

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Home Ops Copilot//EN",
        f"X-WR-CALNAME:{_escape_ics(f'{season.value.title()} Maintenance - {house_name}')}",
    ]

    for idx, item in enumerate(checklist_items):
        offset_days = priority_offsets.get(item.priority, 7)
        event_date = base_date + timedelta(days=offset_days)
        date_str = event_date.strftime("%Y%m%d")

        # Build description from available fields
        desc_parts: list[str] = []
        if item.notes:
            desc_parts.append(item.notes)
        if item.frequency:
            desc_parts.append(f"Frequency: {item.frequency}")
        if item.estimated_time:
            desc_parts.append(f"Estimated time: {item.estimated_time}")
        if item.source_doc:
            desc_parts.append(f"Source: {item.source_doc}")
        description = "\\n".join(desc_parts) if desc_parts else ""

        # UID must be globally unique per RFC 5545
        uid = f"homeops-{season.value}-{idx}-{date_str}@home-ops-copilot"

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTART;VALUE=DATE:{date_str}")
        lines.append(f"DTEND;VALUE=DATE:{(event_date + timedelta(days=1)).strftime('%Y%m%d')}")
        lines.append(f"SUMMARY:{_escape_ics(item.task)}")
        if description:
            lines.append(_fold_line(f"DESCRIPTION:{_escape_ics(description)}"))
        if item.device_type:
            lines.append(f"CATEGORIES:{_escape_ics(item.device_type)}")
        # Map priority to iCalendar priority (1=highest, 9=lowest)
        ical_priority = {"high": 1, "medium": 5, "low": 9}.get(item.priority, 5)
        lines.append(f"PRIORITY:{ical_priority}")
        lines.append("STATUS:NEEDS-ACTION")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    # iCalendar spec requires CRLF line endings
    return "\r\n".join(lines) + "\r\n"
