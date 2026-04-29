"""Home Assistant REST API client for calendar event creation."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from .config import Config
from .ocr_parser import ScheduleEntry

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Async client for Home Assistant calendar API."""

    def __init__(self, config: Config) -> None:
        self.base_url = config.ha_url
        self.token = config.ha_token
        self.calendar_entity = config.ha_calendar_entity
        self.timezone = config.timezone

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def create_event(self, entry: ScheduleEntry) -> dict:
        """Create a single calendar event from a ScheduleEntry.

        Returns the HA API response.
        Raises httpx.HTTPStatusError on failure.
        """
        start_dt = entry.start_datetime(self.timezone)
        end_dt = entry.end_datetime(self.timezone)

        summary = entry.label or "Schedule"
        payload = {
            "entity_id": self.calendar_entity,
            "summary": summary,
            "start_date_time": start_dt.isoformat(),
            "end_date_time": end_dt.isoformat(),
        }

        url = f"{self.base_url}/api/services/calendar/create_event"
        logger.info(
            "Creating event: %s on %s (%s → %s)",
            summary, entry.date, start_dt.isoformat(), end_dt.isoformat(),
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def create_events(self, entries: list[ScheduleEntry]) -> list[dict]:
        """Create calendar events for all entries. Returns list of results.

        Partial failures are recorded but don't stop processing remaining entries.
        """
        results: list[dict] = []
        for entry in entries:
            try:
                result = await self.create_event(entry)
                results.append({"entry": entry, "success": True, "response": result})
                logger.info("✓ Created event for %s", entry)
            except httpx.HTTPStatusError as exc:
                logger.error("✗ Failed to create event for %s: %s", entry, exc)
                results.append({
                    "entry": entry,
                    "success": False,
                    "error": str(exc),
                    "status_code": exc.response.status_code,
                })
            except Exception as exc:
                logger.error("✗ Unexpected error for %s: %s", entry, exc)
                results.append({"entry": entry, "success": False, "error": str(exc)})
        return results

    async def health_check(self) -> bool:
        """Verify HA is reachable and token is valid."""
        url = f"{self.base_url}/api/"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers())
                return resp.status_code == 200
        except Exception:
            return False
