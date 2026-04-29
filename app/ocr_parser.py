"""OCR schedule parser: extracts date/time schedule entries from images."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytesseract
from PIL import Image
from dateutil import tz as dateutil_tz


@dataclass(frozen=True)
class ScheduleEntry:
    """A single parsed schedule entry."""
    date: date
    start_time: time
    end_time: time
    label: str = ""

    def start_datetime(self, timezone_str: str = "America/New_York") -> datetime:
        zone = dateutil_tz.gettz(timezone_str)
        return datetime.combine(self.date, self.start_time, tzinfo=zone)

    def end_datetime(self, timezone_str: str = "America/New_York") -> datetime:
        zone = dateutil_tz.gettz(timezone_str)
        return datetime.combine(self.date, self.end_time, tzinfo=zone)

    def __str__(self) -> str:
        return f"{self.date.strftime('%b %d')}: {self.start_time.strftime('%I:%M %p')} – {self.end_time.strftime('%I:%M %p')}"


def extract_text_from_image(image_path: str | Path) -> str:
    """Run Tesseract OCR on an image and return the raw text."""
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text


def _resolve_year(month: int, day: int, today: date | None = None) -> date:
    """Given a month and day (no year), return the next occurrence in the future."""
    if today is None:
        today = date.today()

    # Try this year first
    candidate = date(today.year, month, day)
    if candidate >= today:
        return candidate

    # Otherwise next year
    return date(today.year + 1, month, day)


def _parse_time(time_str: str) -> time | None:
    """Parse a time string like '10:00AM', '10:00 PM', '6:00PM', '10AM', '6:00p'."""
    time_str = time_str.strip().upper().replace(".", "").replace(" ", "")

    patterns = [
        (r"^(\d{1,2}):(\d{2})(AM|PM)$", "hms_ampm"),
        (r"^(\d{1,2})(AM|PM)$", "h_ampm"),
        (r"^(\d{1,2}):(\d{2})$", "hm"),
    ]

    for pattern, kind in patterns:
        m = re.match(pattern, time_str)
        if m:
            if kind == "hms_ampm":
                h, mi, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
            elif kind == "h_ampm":
                h, ampm = int(m.group(1)), m.group(2)
                mi = 0
            else:
                h, mi = int(m.group(1)), int(m.group(2))
                ampm = None

            if ampm == "PM" and h != 12:
                h += 12
            elif ampm == "AM" and h == 12:
                h = 0

            return time(h, mi)

    return None


def _parse_date(date_str: str) -> tuple[int, int] | None:
    """Parse a date string like 'May 04', 'May 4', '05/04', '5/4', '2025-05-04'.
    Returns (month, day) or None.
    """
    date_str = date_str.strip()

    # ISO format: 2025-05-04
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_str)
    if m:
        return int(m.group(2)), int(m.group(3))

    # "May 04", "May 4", "Jun 15"
    month_names = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
        "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
        "JUNE": 6, "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9,
        "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
    }
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2})$", date_str)
    if m:
        month_name = m.group(1).upper()
        if month_name in month_names:
            return month_names[month_name], int(m.group(2))

    # MM/DD or M/D
    m = re.match(r"^(\d{1,2})/(\d{1,2})$", date_str)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None


def parse_schedule(text: str) -> list[ScheduleEntry]:
    """Parse OCR text into a list of ScheduleEntry objects.

    Supports multiple common formats:
    - Tabular: "May 04  10:00AM  6:00PM"
    - Dashed:  "May 04  10:00AM - 6:00PM"
    - Labeled: "May 04 (Mon)  10:00AM - 6:00PM  Work"
    - Multi-line blocks with date on one line and times on the next
    """
    entries: list[ScheduleEntry] = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Pattern 1: Date + time range on same line
    # e.g., "May 04  10:00AM  6:00PM" or "May 04  10:00AM - 6:00PM"
    same_line_re = re.compile(
        r"(?P<date>[A-Za-z]+\s+\d{1,2}|\d{1,2}/\d{1,2}|\d{4}-\d{1,2}-\d{1,2})"
        r"(?:\s*\([^)]*\))?"  # optional day-of-week in parens
        r"\s+"
        r"(?P<start>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|[AaPp][Mm]))"
        r"\s*(?:[-–—to]+)\s*"
        r"(?P<end>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|[AaPp][Mm]))"
        r"(?:\s+(?P<label>.+))?",
        re.IGNORECASE,
    )

    # Pattern 2: Time range without explicit date (looks for date on previous line)
    time_only_re = re.compile(
        r"(?P<start>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|[AaPp][Mm]))"
        r"\s*(?:[-–—to]+)\s*"
        r"(?P<end>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|[AaPp][Mm]))",
        re.IGNORECASE,
    )

    # Pattern 3: Two separate times on the same line without separator
    # e.g., "10:00AM  6:00PM"
    two_times_re = re.compile(
        r"(?P<start>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|[AaPp][Mm]))"
        r"\s{2,}"
        r"(?P<end>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|[AaPp][Mm]))",
        re.IGNORECASE,
    )

    last_date_md: tuple[int, int] | None = None

    for line in lines:
        # Try same-line match first
        m = same_line_re.search(line)
        if m:
            md = _parse_date(m.group("date"))
            start_t = _parse_time(m.group("start"))
            end_t = _parse_time(m.group("end"))
            if md and start_t and end_t:
                month, day = md
                entry_date = _resolve_year(month, day)
                label = (m.group("label") or "").strip()
                entries.append(ScheduleEntry(
                    date=entry_date, start_time=start_t, end_time=end_t, label=label
                ))
                last_date_md = md
                continue

        # Try to detect a date-only line (for multi-line format)
        date_only_m = re.match(
            r"^([A-Za-z]+\s+\d{1,2}|\d{1,2}/\d{1,2}|\d{4}-\d{1,2}-\d{1,2})"
            r"(?:\s*\([^)]*\))?\s*$",
            line,
        )
        if date_only_m:
            md = _parse_date(date_only_m.group(1))
            if md:
                last_date_md = md
                continue

        # Try two times separated by spaces (no dash)
        m = two_times_re.search(line)
        if m:
            start_t = _parse_time(m.group("start"))
            end_t = _parse_time(m.group("end"))
            if start_t and end_t and last_date_md:
                month, day = last_date_md
                entry_date = _resolve_year(month, day)
                entries.append(ScheduleEntry(
                    date=entry_date, start_time=start_t, end_time=end_t
                ))
                continue

        # Try time range with separator
        m = time_only_re.search(line)
        if m:
            start_t = _parse_time(m.group("start"))
            end_t = _parse_time(m.group("end"))
            if start_t and end_t and last_date_md:
                month, day = last_date_md
                entry_date = _resolve_year(month, day)
                entries.append(ScheduleEntry(
                    date=entry_date, start_time=start_t, end_time=end_t
                ))
                continue

    return entries
