"""Tests for AI parser payload normalization."""

from __future__ import annotations

from app.ai_parser import parse_ai_schedule_payload


def test_parse_ai_payload_from_example_schedule():
    payload = {
        "entries": [
            {"month": 5, "day": 4, "year": None, "start_time": "10:00 AM", "end_time": "6:00 PM", "label": "Shooters World"},
            {"month": 5, "day": 5, "year": None, "start_time": "10:00 AM", "end_time": "6:00 PM", "label": "Shooters World"},
            {"month": 5, "day": 6, "year": None, "start_time": "10:00 AM", "end_time": "3:00 PM", "label": "Shooters World"},
            {"month": 5, "day": 7, "year": None, "start_time": "10:00 AM", "end_time": "6:00 PM", "label": "Shooters World"},
            {"month": 5, "day": 8, "year": None, "start_time": "4:30 PM", "end_time": "9:30 PM", "label": "Shooters World"},
        ]
    }

    entries = parse_ai_schedule_payload(payload)

    assert len(entries) == 5
    assert [entry.date.month for entry in entries] == [5, 5, 5, 5, 5]
    assert [entry.date.day for entry in entries] == [4, 5, 6, 7, 8]
    assert entries[0].start_time.hour == 10
    assert entries[0].end_time.hour == 18
    assert entries[2].end_time.hour == 15
    assert entries[4].start_time.hour == 16
    assert entries[4].start_time.minute == 30
    assert entries[4].end_time.hour == 21
    assert entries[4].end_time.minute == 30


def test_parse_ai_payload_ignores_empty_days_and_bad_rows():
    payload = {
        "entries": [
            {"month": 5, "day": 9, "year": None, "start_time": "", "end_time": "", "label": ""},
            {"month": 5, "day": 10, "year": None, "start_time": "bad", "end_time": "6:00 PM", "label": ""},
            {"month": 5, "day": 11, "year": None, "start_time": "10:00 AM", "end_time": "6:00 PM", "label": "Work"},
        ]
    }

    entries = parse_ai_schedule_payload(payload)

    assert len(entries) == 1
    assert entries[0].date.day == 11
