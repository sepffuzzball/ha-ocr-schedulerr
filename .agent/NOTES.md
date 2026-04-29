# Agent Notes

## Useful commands

- Run bot: `python -m app.main`
- Run tests: `pytest tests/ -v`
- Lint: `ruff check app/ tests/`
- Docker build: `docker compose build`
- Docker up: `docker compose up -d`
- View logs: `docker compose logs -f`

## LM Studio setup (remote)

1. Install LM Studio on remote machine
2. Download a vision model (see docs/MODEL_RECOMMENDATIONS.md)
3. Start server: `lmstudio --server` (default port 1234)
4. Set in `.env`:
   ```env
   OPENAI_BASE_URL=http://<remote-host>:1234/v1
   OPENAI_API_KEY=local-key
   OPENAI_MODEL=<model-name>
   ```

## Known gotchas

- Tesseract must be installed in the container (apt package, not pip)
- HA requires timezone-aware datetimes for calendar events
- If no year in date, parser assumes next future occurrence
- `end_date` for all-day events must be exclusive (start + 1 day)
- python-telegram-bot v20+ is fully async — all handlers must be async def

## AI parser troubleshooting

If you see "AI parser failed; falling back to OCR":
1. Check endpoint reachability: `curl http://<host>:1234/v1/models`
2. Verify model name matches exactly what LM Studio loaded
3. Ensure the model supports vision (check docs/MODEL_RECOMMENDATIONS.md)

## Model recommendations

See [docs/MODEL_RECOMMENDATIONS.md](docs/MODEL_RECOMMENDATIONS.md) for:
- Qwen2.5-VL-7B-Instruct (best balance)
- Phi-3.5-vision-instruct (compact, 4GB VRAM)
- LLaVA-NeXT-7B (widely tested)
