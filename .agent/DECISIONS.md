# Agent Decision Log

## 2026-04-29: Tech stack selection

- Context: Building a Telegram bot that OCRs schedule images and creates HA calendar events
- Decision: Python with python-telegram-bot v20+, pytesseract, httpx
- Alternatives considered: Node.js (telegraf + tesseract.js), Go (less OCR library support)
- Consequences: Simple async model, good OCR support via Tesseract, lightweight Docker image
- Related files: pyproject.toml, Dockerfile

## 2026-04-29: HA API approach

- Context: Home Assistant calendar event creation
- Decision: Use REST API POST /api/services/calendar/create_event with start_date_time/end_date_time
- Alternatives considered: WebSocket API (more complex, overkill for simple event creation)
- Consequences: Simple HTTP calls, requires long-lived access token, timezone-aware datetimes required
- Related files: app/ha_client.py

## 2026-04-29: OCR parser design

- Context: Need to handle various schedule image formats from OCR output
- Decision: Regex-based parser supporting multiple formats (same-line, multi-line, with/without dashes, with labels)
- Alternatives considered: LLM-based parsing (adds latency and cost), strict single format
- Consequences: Handles common formats well, may need tuning for new formats
- Related files: app/ocr_parser.py

## 2026-04-29: AI vision parser before OCR fallback

- Context: The target schedule is a mobile screenshot where visual row grouping matters and OCR alone may lose structure.
- Decision: Add optional AI vision parsing first, controlled by `OPENAI_API_KEY` and `AI_PARSER_ENABLED`, with Tesseract OCR as fallback.
- Alternatives considered: OCR-only parsing, local multimodal model, sending OCR text to an LLM.
- Consequences: Better parsing for screenshots and empty days, but requires a paid external API key when enabled.
- Related files: app/ai_parser.py, app/bot.py, .env.example, README.md

## 2026-04-29: OpenAI-compatible endpoint support

- Context: Users may want to run vision models locally or on a remote machine (e.g., LM Studio) instead of paying for OpenAI.
- Decision: Add `OPENAI_BASE_URL` config variable, defaulting to official OpenAI but allowing any OpenAI-compatible endpoint.
- Alternatives considered: Separate "local mode" flag, hardcoded LM Studio URL.
- Consequences: Flexible deployment (cloud or self-hosted), requires users to specify base URL for non-OpenAI endpoints.
- Related files: app/config.py, app/ai_parser.py, .env.example, docs/MODEL_RECOMMENDATIONS.md
