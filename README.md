# ha-ocr-scheduler

A Telegram bot that reads schedule images via OCR and creates calendar events in Home Assistant.

## What it does

1. You send a photo of a work schedule to the Telegram bot
2. The bot uses AI vision parsing if `OPENAI_API_KEY` is configured
3. If AI parsing is unavailable or fails, the bot falls back to Tesseract OCR
4. The parsed schedule (dates + time ranges) is sent to Home Assistant
5. Calendar events are created via the HA REST API
6. The bot replies with a success/failure summary

## Tech stack

- Python 3.12
- python-telegram-bot v20+ (async)
- Optional OpenAI-compatible vision model via HTTP API
- Tesseract OCR (pytesseract + Pillow)
- httpx (async HTTP for HA API)
- Docker

## Supported schedule formats

The parser handles several common formats:

```
May 04  10:00AM - 6:00PM
May 05  10:00AM – 6:00PM
May 06 (Mon)  9:00AM - 5:00PM
```

And multi-line:
```
May 04
10:00AM - 6:00PM
```

## Quick start

### 1. Create a Telegram bot

Message [@BotFather](https://t.me/BotFather) on Telegram, create a new bot, and copy the token.

### 2. Get your chat ID

Send a message to your bot, then visit:
```
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```
Look for `"chat":{"id": <NUMBER>}`.

### 3. Create a Home Assistant long-lived access token

In Home Assistant, go to your Profile → Security → Create Token. Copy it.

### 4. Configure

```bash
cp .env.example .env
# Edit .env with your values
```

Required environment variables:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `HA_URL` | Home Assistant URL (e.g., `http://homeassistant.local:8123`) |
| `HA_TOKEN` | Long-lived access token from HA |
| `HA_CALENDAR_ENTITY` | Calendar entity ID (e.g., `calendar.work_schedule`) |
| `ALLOWED_CHAT_IDS` | Comma-separated chat IDs (leave empty to allow all) |
| `TZ` | Timezone for events (default: `America/New_York`) |
| `AI_PARSER_ENABLED` | Use AI vision parsing before OCR fallback (`true`/`false`) |
| `OPENAI_API_KEY` | API key (any string for local servers like LM Studio) |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint (default: `https://api.openai.com/v1`) |
| `OPENAI_MODEL` | Vision-capable model name (see [docs/MODEL_RECOMMENDATIONS.md](docs/MODEL_RECOMMENDATIONS.md)) |

### Using LM Studio on a remote machine

```env
# Remote LM Studio server at 203.0.113.50:1234
OPENAI_BASE_URL=http://203.0.113.50:1234/v1
OPENAI_API_KEY=local-key
OPENAI_MODEL=Qwen/Qwen2.5-VL-7B-Instruct-GGUF
```

See [docs/MODEL_RECOMMENDATIONS.md](docs/MODEL_RECOMMENDATIONS.md) for model recommendations and setup tips.

## Example image parsing

For the schedule screenshot showing `May 04 - May 10`, the correct parsed entries are:

| Date | Start | End | Label |
|---|---:|---:|---|
| May 04 | 10:00 AM | 6:00 PM | Shooters World |
| May 05 | 10:00 AM | 6:00 PM | Shooters World |
| May 06 | 10:00 AM | 3:00 PM | Shooters World |
| May 07 | 10:00 AM | 6:00 PM | Shooters World |
| May 08 | 4:30 PM | 9:30 PM | Shooters World |

May 09 is ignored because it has no shift time. Since the screenshot has no year, each date is resolved to the next future occurrence of that month/day.

### 5. Run with Docker Compose

```bash
docker compose up -d
```

### 6. Send a schedule image

Open Telegram, send your bot a photo of a schedule. It will respond with parsed entries and creation results.

## Development

### Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/
```

### Lint

```bash
ruff check app/ tests/
```

## Architecture

```
app/
├── main.py         # Entry point
├── config.py       # Environment config
├── bot.py          # Telegram bot handler
├── ai_parser.py    # AI vision parsing (OpenAI-compatible API)
├── ocr_parser.py   # Tesseract OCR + schedule parsing
└── ha_client.py    # Home Assistant API client
```

Flow: Telegram photo → download → AI vision parse → OCR fallback → parse dates/times → create HA calendar events → reply

## Troubleshooting

| Issue | Fix |
|---|---|
| OCR returns no text | Ensure image is clear, well-lit, and has high contrast |
| Wrong dates parsed | Check OCR output in logs; may need image preprocessing |
| HA event creation fails | Verify `HA_URL`, `HA_TOKEN`, and `HA_CALENDAR_ENTITY` |
| Bot doesn't respond | Check `TELEGRAM_BOT_TOKEN` and container logs |
| "Unauthorized" | Add your chat ID to `ALLOWED_CHAT_IDS` |

## License

MIT
