"""AI vision parser for schedule images."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from .config import Config
from .ocr_parser import ScheduleEntry, _parse_time, _resolve_year

logger = logging.getLogger(__name__)


class AIScheduleParser:
    """Parse schedule images directly with a vision-capable AI model."""

    def __init__(self, config: Config) -> None:
        self.api_key = config.openai_api_key
        self.base_url = config.openai_base_url
        self.model = config.openai_model
        self.timeout = config.ai_timeout
        self.enabled = config.ai_parser_enabled and bool(config.openai_api_key)

    async def parse_image(self, image_path: str | Path) -> list[ScheduleEntry]:
        """Parse a schedule image into calendar entries.

        Returns an empty list if parsing is disabled or the AI finds no shifts.
        Raises on transport/API failures so the caller can fall back to OCR.
        """
        if not self.enabled:
            return []

        payload = self._build_payload(image_path)
        async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        logger.info("AI parser response: %s", content)
        parsed = json.loads(content)
        return parse_ai_schedule_payload(parsed)

    def _build_payload(self, image_path: str | Path) -> dict[str, Any]:
        image_path = Path(image_path)
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        data_url = f"data:{mime_type};base64,{image_b64}"

        return {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract work schedules from mobile screenshots. "
                        "Return only valid JSON. Do not guess shifts for dates that show no time range. "
                        "If the image has dates without years, use null for year."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Read this schedule image and return JSON with this exact schema: "
                                "{\"entries\":[{\"month\":5,\"day\":4,\"year\":null,"
                                "\"start_time\":\"10:00 AM\",\"end_time\":\"6:00 PM\","
                                "\"label\":\"Shooters World\"}]}. "
                                "Only include rows with actual shift times. Ignore totals, navigation, tabs, "
                                "empty days, and unrelated UI text."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        }


def parse_ai_schedule_payload(payload: dict[str, Any]) -> list[ScheduleEntry]:
    """Normalize an AI JSON response into ScheduleEntry objects."""
    entries: list[ScheduleEntry] = []
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        return entries

    for raw in raw_entries:
        if not isinstance(raw, dict):
            continue

        try:
            month = int(raw["month"])
            day = int(raw["day"])
            start_time = _parse_time(str(raw["start_time"]))
            end_time = _parse_time(str(raw["end_time"]))
            if start_time is None or end_time is None:
                continue

            year = raw.get("year")
            if year:
                entry_date = _resolve_year(month, day)
                # Trust only future/no-year semantics for now. If the model returns a past year,
                # _resolve_year still prevents accidentally creating stale events.
                if int(year) >= entry_date.year:
                    entry_date = entry_date.replace(year=int(year))
            else:
                entry_date = _resolve_year(month, day)

            entries.append(
                ScheduleEntry(
                    date=entry_date,
                    start_time=start_time,
                    end_time=end_time,
                    label=str(raw.get("label") or "Schedule"),
                )
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping invalid AI schedule row: %r", raw)

    return entries
