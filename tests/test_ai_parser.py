"""Tests for AI parser payload normalization."""

from __future__ import annotations

from pathlib import Path

from app.ai_parser import AIScheduleParser, parse_ai_schedule_payload
from app.config import Config


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


def test_build_payload_no_temperature_and_data_url(tmp_path: Path) -> None:
    """Regression: _build_payload must omit temperature, produce correct multimodal URL."""
    config = Config(
        telegram_token="fake",
        ha_url="http://fake",
        ha_token="fake",
        ha_calendar_entity="fake",
        timezone="UTC",
        allowed_chat_ids=[1],
        openai_api_key="sk-fake",
        openai_base_url="https://api.openai.com/v1",
        openai_model="gpt-4o",
        ai_parser_enabled=True,
        ai_timeout=30,
    )
    parser = AIScheduleParser(config)
    bytes_content = b"\x00\x01\x02\x03"
    jpg_path = tmp_path / "schedule.jpg"
    jpg_path.write_bytes(bytes_content)
    payload = parser._build_payload(str(jpg_path))
    assert "temperature" not in payload
    assert payload["model"] == "gpt-4o"
    assert "messages" in payload
    user_msg = payload["messages"][1]
    assert user_msg["role"] == "user"
    assert len(user_msg["content"]) == 2
    text_part = user_msg["content"][0]
    assert text_part["type"] == "text"
    assert text_part["text"].startswith("Read this schedule image")
    image_part = user_msg["content"][1]
    assert image_part["type"] == "image_url"
    expected_url = "data:image/jpeg;base64,AAECAw=="
    assert image_part["image_url"]["url"] == expected_url
