"""Telegram bot: receives images, runs OCR, creates HA calendar events."""

from __future__ import annotations

import logging
import os
import tempfile

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from .config import Config
from .ai_parser import AIScheduleParser
from .ha_client import HomeAssistantClient
from .ocr_parser import extract_text_from_image, parse_schedule

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "/tmp/ha-ocr-scheduler"


def _format_results(results: list[dict]) -> str:
    """Format the creation results into a Telegram-friendly message."""
    succeeded = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    total = len(results)

    lines = [f"📋 Schedule processed: {succeeded}/{total} events created"]
    if failed:
        lines.append(f"⚠️ {failed} failed")

    lines.append("")
    for r in results:
        entry = r["entry"]
        if r["success"]:
            lines.append(f"✅ {entry}")
        else:
            error = r.get("error", "unknown error")
            lines.append(f"❌ {entry} — {error}")

    return "\n".join(lines)


class ScheduleBot:
    """Telegram bot that processes schedule images."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.ha_client = HomeAssistantClient(config)
        self.ai_parser = AIScheduleParser(config)

    def _is_authorized(self, chat_id: int) -> bool:
        """Check if the chat is authorized to use the bot."""
        if not self.config.allowed_chat_ids:
            return True  # No restriction if not configured
        return chat_id in self.config.allowed_chat_ids

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle an incoming photo message."""
        if not update.message or not update.message.photo:
            return

        chat_id = update.message.chat_id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        await update.message.reply_text("🔍 Processing image...")

        # Download the highest resolution photo
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=DOWNLOAD_DIR, suffix=".jpg", delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            await tg_file.download_to_drive(tmp_path)
            logger.info("Downloaded photo to %s", tmp_path)

            entries = []
            parse_method = "OCR"

            if self.ai_parser.enabled:
                try:
                    entries = await self.ai_parser.parse_image(tmp_path)
                    parse_method = "AI vision"
                except Exception:
                    logger.exception("AI parser failed; falling back to OCR")

            raw_text = ""
            if not entries:
                # OCR fallback
                raw_text = extract_text_from_image(tmp_path)
                logger.info("OCR text:\n%s", raw_text)

                if not raw_text.strip():
                    await update.message.reply_text(
                        "❌ Could not extract any text from the image. "
                        "Please make sure the image is clear and contains a schedule."
                    )
                    return

                entries = parse_schedule(raw_text)
                parse_method = "OCR"

            if not entries:
                await update.message.reply_text(
                    "❌ Could not parse a schedule from the image.\n\n"
                    "OCR text found:\n```\n" + raw_text + "\n```\n\n"
                    "Expected format: dates with time ranges like 'May 04 10:00AM - 6:00PM'"
                )
                return

            # Preview what was parsed
            preview_lines = [f"📅 Found schedule entries ({parse_method}):"]
            for entry in entries:
                preview_lines.append(f"  • {entry}")
            await update.message.reply_text("\n".join(preview_lines))

            # Create events in Home Assistant
            results = await self.ha_client.create_events(entries)

            # Report results
            await update.message.reply_text(_format_results(results))

        except Exception:
            logger.exception("Error processing image")
            await update.message.reply_text(
                "❌ An unexpected error occurred while processing the image."
            )
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def post_init(self, application: object) -> None:
        """Run after the application is initialized."""
        healthy = await self.ha_client.health_check()
        if healthy:
            logger.info("Home Assistant connection verified")
        else:
            logger.warning("Home Assistant health check failed — bot will continue but HA calls may fail")

    def run(self) -> None:
        """Build and run the Telegram bot."""
        app = (
            ApplicationBuilder()
            .token(self.config.telegram_token)
            .post_init(self.post_init)
            .build()
        )

        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        logger.info("Starting bot...")
        app.run_polling()
