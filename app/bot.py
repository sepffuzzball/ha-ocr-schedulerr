"""Telegram bot: receives images, runs OCR, creates HA calendar events."""

from __future__ import annotations

import logging
import os
import tempfile

from telegram import Message, Update
from telegram.constants import ChatType
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .ai_parser import AIScheduleParser
from .config import Config
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


def _is_group(chat_type: str) -> bool:
    return chat_type in (ChatType.GROUP, ChatType.SUPERGROUP)


def _bot_is_mentioned(message: Message, bot_username: str) -> bool:
    """Check whether the bot is @mentioned in the message text or caption."""
    text = message.caption or message.text or ""
    if f"@{bot_username}" in text:
        return True
    # Also check entity-level mentions (more reliable)
    for entity in (message.caption_entities or []) + (message.entities or []):
        if entity.type == "mention":
            mention_text = text[entity.offset : entity.offset + entity.length]
            if mention_text.lower() == f"@{bot_username.lower()}":
                return True
    return False


class ScheduleBot:
    """Telegram bot that processes schedule images.

    Activation rules:
      - Private chat (DM): photo sent directly → process
      - Group chat: /schedule command with photo, or /schedule replying to a photo,
        or photo with @bot mention in caption → process
      - Everything else in groups → ignored
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.ha_client = HomeAssistantClient(config)
        self.ai_parser = AIScheduleParser(config)
        self._bot_username: str = ""

    def _is_authorized(self, chat_id: int) -> bool:
        """Check if the chat is authorized to use the bot."""
        if not self.config.allowed_chat_ids:
            return True  # No restriction if not configured
        return chat_id in self.config.allowed_chat_ids

    # ------------------------------------------------------------------
    # /start
    # ------------------------------------------------------------------

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Respond to /start with a short help message."""
        if not update.message:
            return
        await update.message.reply_text(
            "👋 Send me a schedule screenshot and I'll add the shifts to your "
            "Home Assistant calendar.\n\n"
            "In group chats use /schedule (with a photo or replying to one) "
            "or @mention me on a photo."
        )

    # ------------------------------------------------------------------
    # /schedule command — works in groups and DMs
    # ------------------------------------------------------------------

    async def cmd_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /schedule command.

        Accepts:
          1. /schedule sent *with* an attached photo
          2. /schedule sent as a *reply* to a photo message
          3. /schedule in a DM (no photo) → asks for one
        """
        if not update.message:
            return

        chat_id = update.message.chat_id
        if not self._is_authorized(chat_id):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        # Case 1: photo attached to the /schedule message itself
        if update.message.photo:
            await self._process_photo(update.message.photo[-1], update.message)
            return

        # Case 2: /schedule is a reply to another message that has a photo
        replied = update.message.reply_to_message
        if replied and replied.photo:
            await self._process_photo(replied.photo[-1], update.message)
            return

        # Case 3: no photo found
        await update.message.reply_text(
            "📷 Send /schedule with an attached photo, or reply to a photo with /schedule."
        )

    # ------------------------------------------------------------------
    # Passive photo handler — DMs always, groups only when @mentioned
    # ------------------------------------------------------------------

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming photos.

        - In private chats: always process.
        - In group chats: only if the bot is @mentioned in the caption.
        """
        if not update.message or not update.message.photo:
            return

        chat_id = update.message.chat_id
        if not self._is_authorized(chat_id):
            return  # Silently ignore in groups

        chat_type = update.message.chat.type

        # DMs: always process
        if not _is_group(chat_type):
            await self._process_photo(update.message.photo[-1], update.message)
            return

        # Groups: only if mentioned
        if self._bot_username and _bot_is_mentioned(update.message, self._bot_username):
            await self._process_photo(update.message.photo[-1], update.message)

    # ------------------------------------------------------------------
    # Core processing pipeline
    # ------------------------------------------------------------------

    async def _process_photo(self, photo_file, reply_to: Message) -> None:
        """Download, parse, and create calendar events from a photo.

        `photo_file` is a telegram PhotoSize (the largest).
        `reply_to` is the Message used for sending replies.
        """
        tg_file = await photo_file.get_file()

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=DOWNLOAD_DIR, suffix=".jpg", delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            await tg_file.download_to_drive(tmp_path)
            logger.info("Downloaded photo to %s", tmp_path)

            await reply_to.reply_text("🔍 Processing image...")

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
                    await reply_to.reply_text(
                        "❌ Could not extract any text from the image. "
                        "Please make sure the image is clear and contains a schedule."
                    )
                    return

                entries = parse_schedule(raw_text)
                parse_method = "OCR"

            if not entries:
                await reply_to.reply_text(
                    "❌ Could not parse a schedule from the image.\n\n"
                    "OCR text found:\n```\n" + raw_text + "\n```\n\n"
                    "Expected format: dates with time ranges like 'May 04 10:00AM - 6:00PM'"
                )
                return

            # Preview what was parsed
            preview_lines = [f"📅 Found schedule entries ({parse_method}):"]
            for entry in entries:
                preview_lines.append(f"  • {entry}")
            await reply_to.reply_text("\n".join(preview_lines))

            # Create events in Home Assistant
            results = await self.ha_client.create_events(entries)

            # Report results
            await reply_to.reply_text(_format_results(results))

        except Exception:
            logger.exception("Error processing image")
            await reply_to.reply_text(
                "❌ An unexpected error occurred while processing the image."
            )
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def post_init(self, application: object) -> None:
        """Run after the application is initialized."""
        bot = getattr(application, "bot", None)
        if bot:
            me = await bot.get_me()
            self._bot_username = me.username or ""
            logger.info("Bot username: @%s", self._bot_username)

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

        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("schedule", self.cmd_schedule))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        logger.info("Starting bot...")
        app.run_polling()
