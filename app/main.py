"""Entry point for ha-ocr-scheduler."""

from __future__ import annotations

import logging
import sys

from .config import Config
from .bot import ScheduleBot


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main() -> None:
    setup_logging()

    try:
        config = Config.from_env()
    except ValueError as exc:
        logging.critical("Configuration error: %s", exc)
        sys.exit(1)

    bot = ScheduleBot(config)
    bot.run()


if __name__ == "__main__":
    main()
