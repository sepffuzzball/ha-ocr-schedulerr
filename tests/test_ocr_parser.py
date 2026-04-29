"""Tests for the OCR schedule parser."""

from __future__ import annotations

from datetime import date

import pytest

from app.ocr_parser import ScheduleEntry, _parse_date, _parse_time, _resolve_year, parse_schedule


class TestParseTime:
    def test_standard_am_pm(self):
        assert _parse_time("10:00AM") is not None
        assert _parse_time("10:00AM").hour == 10
        assert _parse_time("10:00AM").minute == 0

    def test_pm_conversion(self):
        assert _parse_time("6:00PM").hour == 18
        assert _parse_time("6:00PM").minute == 0

    def test_12pm(self):
        assert _parse_time("12:00PM").hour == 12

    def test_12am(self):
        assert _parse_time("12:00AM").hour == 0

    def test_no_minutes(self):
        assert _parse_time("10AM") is not None
        assert _parse_time("10AM").hour == 10
        assert _parse_time("10AM").minute == 0

    def test_lowercase(self):
        assert _parse_time("10:00am").hour == 10
        assert _parse_time("6:00pm").hour == 18

    def test_space_before_ampm(self):
        assert _parse_time("10:00 PM").hour == 22

    def test_invalid(self):
        assert _parse_time("abc") is None


class TestParseDate:
    def test_month_day(self):
        assert _parse_date("May 04") == (5, 4)

    def test_month_day_no_zero(self):
        assert _parse_date("May 4") == (5, 4)

    def test_month_abbrev(self):
        assert _parse_date("Jun 15") == (6, 15)

    def test_slash_format(self):
        assert _parse_date("05/04") == (5, 4)

    def test_iso_format(self):
        assert _parse_date("2025-05-04") == (5, 4)

    def test_invalid(self):
        assert _parse_date("Hello") is None


class TestResolveYear:
    def test_future_date_this_year(self):
        today = date(2026, 3, 1)
        result = _resolve_year(5, 4, today)
        assert result == date(2026, 5, 4)

    def test_past_date_rolls_to_next_year(self):
        today = date(2026, 6, 1)
        result = _resolve_year(5, 4, today)
        assert result == date(2027, 5, 4)

    def test_today(self):
        today = date(2026, 5, 4)
        result = _resolve_year(5, 4, today)
        assert result == date(2026, 5, 4)


class TestParseSchedule:
    def test_single_line_format(self):
        text = "May 04  10:00AM - 6:00PM"
        entries = parse_schedule(text)
        assert len(entries) == 1
        assert entries[0].date.month == 5
        assert entries[0].date.day == 4
        assert entries[0].start_time.hour == 10
        assert entries[0].end_time.hour == 18

    def test_multi_line_format(self):
        text = """May 04
10:00AM - 6:00PM
May 05
10:00AM - 6:00PM
May 06
9:00AM - 5:00PM"""
        entries = parse_schedule(text)
        assert len(entries) == 3
        assert entries[0].date.day == 4
        assert entries[1].date.day == 5
        assert entries[2].start_time.hour == 9
        assert entries[2].end_time.hour == 17

    def test_five_day_schedule(self):
        text = """May 04  10:00AM - 6:00PM
May 05  10:00AM - 6:00PM
May 06  10:00AM - 6:00PM
May 07  10:00AM - 6:00PM
May 08  10:00AM - 6:00PM"""
        entries = parse_schedule(text)
        assert len(entries) == 5
        for entry in entries:
            assert entry.start_time.hour == 10
            assert entry.end_time.hour == 18

    def test_with_day_of_week(self):
        text = "May 04 (Sun)  10:00AM - 6:00PM"
        entries = parse_schedule(text)
        assert len(entries) == 1
        assert entries[0].date.day == 4

    def test_with_label(self):
        text = "May 04  10:00AM - 6:00PM  Work"
        entries = parse_schedule(text)
        assert len(entries) == 1
        assert entries[0].label == "Work"

    def test_two_times_no_separator(self):
        text = "May 04\n10:00AM  6:00PM"
        entries = parse_schedule(text)
        assert len(entries) == 1
        assert entries[0].start_time.hour == 10
        assert entries[0].end_time.hour == 18

    def test_empty_input(self):
        assert parse_schedule("") == []

    def test_no_dates_found(self):
        assert parse_schedule("hello world\nfoo bar") == []

    def test_en_dash(self):
        text = "May 04  10:00AM – 6:00PM"
        entries = parse_schedule(text)
        assert len(entries) == 1

    def test_em_dash(self):
        text = "May 04  10:00AM — 6:00PM"
        entries = parse_schedule(text)
        assert len(entries) == 1


class TestScheduleEntry:
    def test_str_format(self):
        entry = ScheduleEntry(
            date=date(2026, 5, 4),
            start_time=date(2026, 1, 1, 10, 0).time(),
            end_time=date(2026, 1, 1, 18, 0).time(),
        )
        s = str(entry)
        assert "May 04" in s
        assert "10:00 AM" in s
        assert "06:00 PM" in s
