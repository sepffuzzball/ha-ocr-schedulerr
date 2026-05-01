"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    telegram_token: str
    ha_url: str
    ha_token: str
    ha_calendar_entity: str
    timezone: str
    allowed_chat_ids: list[int]
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    ai_parser_enabled: bool
    ai_timeout: int

    @classmethod
    def from_env(cls) -> Config:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        ha_url = os.environ.get("HA_URL", "http://homeassistant.local:8123")
        ha_token = os.environ.get("HA_TOKEN", "")
        ha_calendar = os.environ.get("HA_CALENDAR_ENTITY", "calendar.schedule")
        tz = os.environ.get("TZ", "America/New_York")
        chat_ids_str = os.environ.get("ALLOWED_CHAT_IDS", "")
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        openai_base_url = os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        ai_parser_enabled = os.environ.get("AI_PARSER_ENABLED", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        ai_timeout = int(os.environ.get("AI_TIMEOUT", "60"))

        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not ha_token:
            raise ValueError("HA_TOKEN is required")

        chat_ids: list[int] = []
        if chat_ids_str:
            chat_ids = [int(cid.strip()) for cid in chat_ids_str.split(",") if cid.strip()]

        return cls(
            telegram_token=token,
            ha_url=ha_url.rstrip("/"),
            ha_token=ha_token,
            ha_calendar_entity=ha_calendar,
            timezone=tz,
            allowed_chat_ids=chat_ids,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url.rstrip("/"),
            openai_model=openai_model,
            ai_parser_enabled=ai_parser_enabled,
            ai_timeout=ai_timeout,
        )
